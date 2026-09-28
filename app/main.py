import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import close_db, init_db

# Internal module imports
from . import auth
from .sql_functions import get_leaderboard, get_player, update_elo, update_online_status


class ConnectionManager:
    def __init__(self):
        # dictionary of WebSockets with userids
        self.active_connections: dict[int, WebSocket] = {}
        # dictionary of game rooms maping to userids with WebSockets 
        self.game_rooms: dict[str, dict[int, WebSocket]] = {}
        # stores tha data of the room
        self.game_states: dict[str, dict] = {}
        self.user_names: dict[int, str] = {}

    async def connect(self, client_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket # adding to the list

    def disconnect(self, client_id: int):
        if client_id in self.active_connections:
            del self.active_connections[client_id] # removing from the list

    async def send_personal_message(self, message: str, websocket: WebSocket):
        payload = {
            "type": "chat",
            "content": message
        }
        await websocket.send_json(payload)

    async def send_challange(self, reciver_id: int, senderid: int):
        sender_name = self.user_names.get(senderid, f"Player #{senderid}")
        payload = {
            "type": "challenge",
            "content": f"{sender_name} has challenged you!",
            "sender": senderid,
            "sender_name": sender_name, # Send the name explicitly
            "reciver": reciver_id
        }
        if reciver_id in self.active_connections:
            await self.active_connections[reciver_id].send_json(payload)

    async def broadcast(self, message: str, message_type: str):
        # We send a dictionary instead of a raw string
        payload = {
            "type": message_type,
            "content": message
        }

        for client_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_json(payload)
            except Exception:
                pass

    async def list_players(self):
        playing_players_ids = set()
        for room_id, room_members in self.game_rooms.items():
            state = self.game_states.get(room_id)
            # Only mark as "busy" if the game is still in progress
            if state and state.get("status") == "playing":
                playing_players_ids.update(room_members.keys())
        
        # Helper to build a player object
        def get_player_info(pid):
            data = get_player(str(pid))
            elo = data[2] if data else 1200
            return {
                "id": pid,
                "name": self.user_names.get(pid, f"Player #{pid}"),
                "elo": elo
            }

        players_online = [get_player_info(pid) for pid in self.active_connections.keys() if pid not in playing_players_ids]
        playing_players = [get_player_info(pid) for pid in playing_players_ids]

        payload = {
            "type": "listplayers",
            "content": players_online, # List of objects
            "playing_players": playing_players # List of objects
        }
        for connection in self.active_connections.values():
            await connection.send_json(payload)
    
    async def create_game_room(self, player1: int, player2: int):
        room_id = f"room_{player1}_{player2}"
        # Initialize an empty room and the starting Tic-Tac-Toe state
        name1 = self.user_names.get(player1) or get_player(str(player1))[0]
        name2 = self.user_names.get(player2) or get_player(str(player2))[0]

        self.game_rooms[room_id] = {}
        self.game_states[room_id] = {
            "board": [None] * 9, # 9 empty cells
            "current_turn": player1,
            "status": "playing", # or "win", "draw"
            "players": [player1, player2],
            "names": [name1, name2]
        }

        payload = {
            "type": "match_start",
            "room_id": room_id
        }
        
        if player1 in self.active_connections:
            await self.active_connections[player1].send_json(payload)
        if player2 in self.active_connections:
            await self.active_connections[player2].send_json(payload)

    async def connect_game(self, websocket: WebSocket, room_id: str, user_id: int):
        await websocket.accept()
        if room_id not in self.game_rooms:
            self.game_rooms[room_id] = {}
        self.game_rooms[room_id][user_id] = websocket
        
        await self.broadcast_in_room(room_id, "game_state")

    async def broadcast_in_room(self, room_id: str, message: str):
        room = self.game_rooms.get(room_id)
        state = self.game_states.get(room_id)

        if room is None or state is None:
            print(f"Room {room_id} does not exists.")
            return
        
        payload = {
            "type": message,
            "state": self.game_states[room_id]
        }
        # TODO: Send a message ONLY to the websockets inside self.game_rooms[room_id]
        for pid, connection in list(room.items()):
            try:
                await connection.send_json(payload)
            except Exception:
                pass

    # --- GAME SYNCHRONIZATION ---
    def validate_and_apply_move(self, room_id: str, client_id: int, cell_index: int):
        state = self.game_states.get(room_id)
        if not state:
            return False
            
        if state.get("current_turn") != client_id:
            return False
            
        if state["board"][cell_index] is not None:
            return False
        
        if state.get("status") != "playing":
            return False

        # Apply the move
        players = state["players"]
        # Assign 'X' to the challenger (Player 1), 'O' to the accepter (Player 2)
        if players[0] == client_id:
            mark = "X"
        else:
            mark = "O" 

        state["board"][cell_index] = mark
        return True

    def switch_turn(self, room_id):
        state = self.game_states.get(room_id)
        players = state["players"]
        if (state["current_turn"] == players[1]):
            state["current_turn"] = players[0]
        else:
            state["current_turn"] = players[1]

    def winlogic(self, room_id):
        state = self.game_states.get(room_id)

        board = state.get("board")

        status = "playing"
        if (board[0] == board[1] == board[2] and board[0] is not None):
            status = "win"
        elif (board[3] == board[4] == board[5] and board[3] is not None):
            status = "win"
        elif (board[6] == board[7] == board[8] and board[6] is not None):
            status = "win"
        elif (board[0] == board[3] == board[6] and board[0] is not None):
            status = "win"
        elif (board[1] == board[4] == board[7] and board[1] is not None):
            status = "win"
        elif (board[2] == board[5] == board[8] and board[2] is not None):
            status = "win"
        elif (board[0] == board[4] == board[8] and board[0] is not None):
            status = "win"
        elif (board[2] == board[4] == board[6] and board[2] is not None):
            status = "win"


        state["status"] = status
        
        if (state["status"] == "win"):
            return True
        return False
    
    def gamefull(self, room_id):
        state = self.game_states.get(room_id)
        board = state.get("board")

        if None not in board:
            state["status"] = "draw"
            return True
        return False

    async def broadcast_leaderboard(self):
        leaderboard_data = get_leaderboard()
        # print(leaderboard_data)
        
        payload = {
            "type": "leaderboard_update",
            "content": leaderboard_data,
        }
        for client_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_json(payload)
            except Exception:
                pass

    async def validate_player(self, client_id):
        name = get_player(str(client_id))
        if (name):
            if (name[1]):
                # already online
                print("online")
            
            if (not name[1]):
                # already not online
                print("offline")
            
            display_name = name[0]
            elo = name[2]
            self.user_names[client_id] = display_name
        
            payload = {
                "type": "player_name",
                "content": display_name,
                "uid": client_id,
                "elo": elo
            }
        
            if client_id in self.active_connections:
                await self.active_connections[client_id].send_json(payload)
        
        await self.list_players()

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    TODO: Orchestrate the global startup sequence by initializing the 
    MySQL and MongoDB connection pools via the database module.
    """
    init_db()
    yield
    close_db()
    """
    TODO: Implement a graceful teardown of all persistent connections 
    to prevent resource leaks on the host machine during server shutdown.
    """

app = FastAPI(
    title="Identity-Verified Multiplayer Arena",
    lifespan=lifespan
)

# TODO: Configure Cross-Origin Resource Sharing (CORS) to permit 
# asynchronous requests from the frontend development server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Mount the authentication sub-module to the main application 
# tree using a dedicated URL namespace.
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

@app.get("/")
async def get_index():
    return FileResponse("frontend/index.html")
    # return {"status": "online"}


@app.get("/lobby")
async def get_lobby():
    return FileResponse("websocketpage.html")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    
    player_data = get_player(str(client_id))

    if not player_data or not player_data[1]:
        await websocket.accept()
        await websocket.send_json({
            "type": "redirect",
            "url": "/"
        })
        print("OFFLINE")
        await asyncio.sleep(0.1)
        await websocket.close()
        return
    
    if client_id in manager.active_connections:
        await websocket.accept()
        await websocket.send_json({
            "type": "already_logged",
            "content": "You are already logged in on another device/tab."
        })
        print("ONLINE")
        await websocket.close(code=4001)
        return
    
    await manager.connect(client_id, websocket)
    # await asyncio.to_thread(update_online_status, str(client_id), True)
    await manager.list_players()
    await manager.broadcast_leaderboard()
    try:
        while True:
            data = await websocket.receive_json()
            if (data.get("type") == "challenge"):
                await manager.send_challange(data.get('message'), client_id)

            elif (data.get("type") == "accept_challenge"):
                await manager.send_personal_message(f"{manager.user_names[data.get('message')]} Accepted!", manager.active_connections[data.get("challenger_id")])
                await manager.create_game_room(data.get("challenger_id"), data.get("accepter_id"))
                
            elif (data.get("type") == "decline_challenge"):
                await manager.send_personal_message(f"{manager.user_names[data.get('message')]} Declined!", manager.active_connections[data.get("challenger_id")])
            elif (data.get("type") == "validate_player"):
                await manager.validate_player(data.get('message'))
            else:
                await manager.broadcast(f"{manager.user_names[client_id]} says: {data.get('message')}", message_type="chat")
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await asyncio.to_thread(update_online_status, str(client_id), False)
        await manager.broadcast(f"{manager.user_names[client_id]} left the game", message_type="chat")
        await manager.list_players()



@app.websocket("/ws/game/{room_id}/{client_id}")
async def game_websocket_endpoint(websocket: WebSocket, room_id: str, client_id: int):
    # Connect the user to the specific game room
    await manager.connect_game(websocket, room_id, client_id)
    await manager.list_players()
    
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "forfeit":
                state = manager.game_states.get(room_id)
                if state and state.get("status") == "playing":
                    players = state.get("players")
                    # The person who sent the message is the loser
                    winner_id = players[1] 
                    if client_id == players[1]:
                        winner_id = players[0] 
                    loser_id = client_id
                    
                    # Update Elo
                    elo_results = update_elo(str(winner_id), str(loser_id), False)
                    manager.game_states[room_id]["elo_updates"] = elo_results
                    manager.game_states[room_id]["current_turn"] = winner_id
                    manager.game_states[room_id]["status"] = "forfeit"
                    
                    await manager.broadcast_in_room(room_id, "game_forfit")
                    await manager.broadcast_leaderboard()
                    await manager.list_players()
                    
            if (data.get("type") == "make_move"):
                if (data.get("type") == "make_move"):
                    valid_move = manager.validate_and_apply_move(room_id, client_id, data.get("cell_index"))

                    if valid_move:
                        win = manager.winlogic(room_id)
                        gamefull = manager.gamefull(room_id)
                        if (win):
                            winner = manager.game_states.get(room_id).get('current_turn')
                            print(f"PLayer {winner} WON!")
                            players = manager.game_states.get(room_id).get("players")
                            loser = players[0]
                            if players[0] == winner:
                                loser = players[1]
                            
                            elo_results = update_elo(str(winner), str(loser), False)
                            manager.game_states[room_id]["elo_updates"] = elo_results
                            await manager.broadcast_in_room(room_id, "game_win")
                            del manager.game_rooms[room_id]
                            await manager.broadcast_leaderboard()
                            await manager.list_players()
                        elif (gamefull):
                            print("DRAW")
                            players = manager.game_states.get(room_id).get("players")

                            elo_results = update_elo(str(players[0]), str(players[1]), True)
                            manager.game_states[room_id]["elo_updates"] = elo_results
                            await manager.broadcast_in_room(room_id, "game_draw")
                            del manager.game_rooms[room_id]
                            await manager.broadcast_leaderboard()
                            await manager.list_players()
                        else:
                            manager.switch_turn(room_id)
                            await manager.broadcast_in_room(room_id, "game_state")
                
    except WebSocketDisconnect:
        # Detects If a player discconects from game
        if room_id in manager.game_rooms and client_id in manager.game_rooms[room_id]:
            del manager.game_rooms[room_id][client_id]
        
        state = manager.game_states.get(room_id)
        if state and state.get("status") == "playing":
            players = state.get("players")
            print(f"Player {client_id} left the room")

            if players[0] == client_id:
                print(f"PLayer {players[1]} WON!")            
                elo_results= update_elo(str(players[1]), str(players[0]),False)
                manager.game_states[room_id]["elo_updates"] = elo_results
                manager.game_states[room_id]["current_turn"] = players[1]
            elif players[1] == client_id:
                print(f"PLayer {players[0]} WON!")
                elo_results = update_elo(str(players[0]), str(players[1]),False)
                manager.game_states[room_id]["elo_updates"] = elo_results
                manager.game_states[room_id]["current_turn"] = players[0]
                
            
            await manager.broadcast_in_room(room_id, "game_forfit")
            await manager.broadcast_leaderboard()

        if room_id in manager.game_rooms and not manager.game_rooms[room_id]:
            del manager.game_rooms[room_id]
            if room_id in manager.game_states:
                del manager.game_states[room_id]

        await manager.list_players()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host = "0.0.0.0", port = 8000, reload = True)