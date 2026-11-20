(function() {
let client_id;
// let gameSocket;
let ws;
let isInMatch = false;

// Trigger this function AFTER facial recognition returns the UID
function start_lobby(id) {
    
    client_id = Number(id);

    // const self_label = document.getElementById("self_label");
    // self_label.innerHTML = `Player #${client_id} (You)`;
    // // document.getElementById("self-avatar").textContent = client_id;
    // document.querySelector("#myid").textContent = client_id;
    
    // Connect to WebSocket with the recognized UID
    const host = window.location.host; 
    ws = new WebSocket(`ws://${host}/ws/${client_id}`);

    ws.onopen = () => {
        // console.log("Connected to lobby");
        ws.send(JSON.stringify({
            type: "validate_player",
            message: client_id,
        }));
    };

    ws.onmessage = (event) => {
        const messagein = JSON.parse(event.data);

    console.log("Message received:", messagein);
    if (messagein.type == "redirect") {
        window.location.href = messagein.url;
        return;
    }

    if (messagein.type == "player_name") {
        const self_label = document.getElementById("self_label");
        const self_avatar = document.getElementById("self-avatar");
        const self_elo_row = document.getElementById("self-elo-row");
        
        const name = messagein.content;
        const uid = messagein.uid;
        
        if (self_label) {
            self_label.innerHTML = `${name} <small style="font-size: 0.75em; opacity: 0.7;">(#${uid})</small>`;
        }

        if (self_avatar) {
            self_avatar.innerHTML = generateAvatarHtml(messagein.uid, "online");
        }
        if (self_elo_row) {
            self_elo_row.textContent = `${messagein.elo} ELO`;
        }
        
        const myIdEl = document.querySelector("#myid");
        if (myIdEl) myIdEl.textContent = uid;
    }

    if (messagein.type == "already_logged"){
        const messages = document.getElementById('messages');
        const li = document.createElement('li');
        const challengeText = document.getElementById("challengeText");
        li.classList.add('challenge-msg');
        li.textContent = messagein.content;
        messages.appendChild(li);

        const confirmbutton = document.getElementById("customConfirm");
        challengeText.innerHTML = `
            <strong>Session Conflict</strong><br>
            You are already logged in on another device or tab.<br><br>
            <a href="/" style="color: #3b82f6; text-decoration: underline; font-weight: bold;">
                Return to Face Auth
            </a>
        `;
        confirmbutton.style.display = "block";

        document.getElementById("noBtn").style.display = "none";
        document.getElementById("yesBtn").style.display = "none";
    }

    if (messagein.type == "listplayers") {
        let playersList = document.getElementById('players');
        playersList.innerHTML = '';

        // messagein.playing_players is now an array of objects: [{id: 1, name: "Alice"}, ...]
        messagein.playing_players.forEach(player => {
            const row = createPlayerRow(player.id, player.name, "busy", player.elo);
            playersList.appendChild(row);
        });

        messagein.content.forEach(player => {
            if (player.id != client_id) {
                const row = createPlayerRow(player.id, player.name, "online", player.elo);
                playersList.appendChild(row);
            }
        });
    }

    else if (messagein.type == "chat") {
        const messages = document.getElementById('messages');
        const li = document.createElement('li');
        li.textContent = messagein.content;
        messages.appendChild(li);
        messages.scrollTop = messages.scrollHeight;
    }

    else if (messagein.type == "challenge") {
        const messages = document.getElementById('messages');
        const li = document.createElement('li');
        const challengeText = document.getElementById("challengeText");
        li.classList.add('challenge-msg');
        li.textContent = messagein.content;
        messages.appendChild(li);

        const confirmbutton = document.getElementById("customConfirm");
        challengeText.innerHTML = `
            You've been challenged by <br>
            <strong>${messagein.sender_name}</strong> 
            <small style="opacity: 0.6;">(#${messagein.sender})</small>. <br>
            Accept?
        `;
        confirmbutton.style.display = "block";

        document.getElementById("yesBtn").onclick = () => {
            ws.send(JSON.stringify({
                type: "accept_challenge",
                message: messagein.reciver,
                challenger_id: messagein.sender,
                accepter_id: messagein.reciver
            }));
            confirmbutton.style.display = "none";
        };

        document.getElementById("noBtn").onclick = () => {
            ws.send(JSON.stringify({
                type: "decline_challenge",
                message: messagein.reciver,
                challenger_id: messagein.sender
            }));
            confirmbutton.style.display = "none";
        };
    }
    else if (messagein.type == "match_start") {
        // Match accepted! Transition to the game room.
        const roomId = messagein.room_id;
        joinGameRoom(roomId);

        const turnIndicator = document.getElementById("turn-indicator");
        turnIndicator.innerText = "Connecting to board...";
    }

    else if (messagein.type == "leaderboard_update") {
        const leaderboard_list = document.getElementById("Leaderboard");
        leaderboard_list.innerHTML = "";
        
        messagein.content.forEach((player, index) => {
            const li = document.createElement("li");
            li.innerHTML = `<strong>#${index + 1} ${player.name}</strong><span>${player.elo_rating}</span>`;
            leaderboard_list.appendChild(li);
        });

        // Update self ELO in topbar + sidebar if present
        // const me = messagein.content.find(p => p.id === client_id);
        // if (me) {
        //     document.getElementById("self-elo-row").textContent = `${me.elo_rating} ELO`;
        //     const badge = document.getElementById("my-elo-badge");
        //     badge.textContent = `${me.elo_rating} ELO`;
        //     badge.style.display = "inline";
        // }
    }
    };
}

function sendMessage(event) {
    event.preventDefault(); // Prevents the page from refreshing on form submit
    const input = document.getElementById("messageText");
    if (!input.value.trim()) return; // to stop empty messages
    const messageData = {
        "type": "chat",
        "message": input.value
    };
    ws.send(JSON.stringify(messageData));
    input.value = '';
}

function joinGameRoom(roomId) {
    // Switch UI views
    isInMatch = true;
    document.getElementById("lobby").style.display = "none";
    document.getElementById("lobbybtn").style.display = "none";
    document.getElementById("game-view").style.display = "flex";
    document.getElementById("forfitbtn").style.display = "block";
    document.getElementById("room_id").innerText = roomId;

    document.querySelectorAll('.challenge-btn').forEach(btn => {
        btn.disabled = true;
        btn.classList.add('busy');
    });

    const host = window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    gameSocket = new WebSocket(`${protocol}//${host}/ws/game/${roomId}/${client_id}`);
    // gameSocket = new WebSocket(`ws://localhost:8000/ws/game/${roomId}/${client_id}`);

    gameSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.state && data.state.board) {
            const board = data.state.board;
            const players = data.state.players; // [challenger_id, accepter_id]
            const names = data.state.names;
            const myMark = (client_id === players[0]) ? "X" : "O";
            const cells = document.querySelectorAll('.cell');
            
            const avatarChallenger = document.getElementById("avatar-challenger");
            const avatarAccepter = document.getElementById("avatar-accepter");

            if (avatarChallenger) {
                avatarChallenger.innerHTML = generateAvatarHtml(players[0], "busy");
            }
            if (avatarAccepter) {
                // We add the 'red' class here for the second player
                avatarAccepter.innerHTML = generateAvatarHtml(players[1], "busy");
                avatarAccepter.firstElementChild.classList.add("red");
            }

            // Populate player strips
            const cId = players[0], aId = players[1];
            const name0 = names[0] || `Player #${players[0]}`;
            const name1 = names[1] || `Player #${players[1]}`;
            document.getElementById("name-challenger").innerHTML =
                `${name0} <small style="font-size: 0.75em; opacity: 0.7;">(#${cId})</small>${cId === client_id ? ' (You)' : ''}`;
            document.getElementById("name-accepter").innerHTML =
                `${name1} <small style="font-size: 0.75em; opacity: 0.7;">(#${aId})</small>${aId === client_id ? ' (You)' : ''}`;

            board.forEach((cellValue, index) => {
                const el = cells[index];
                const prev = el.textContent;
                const next = cellValue || "";
                el.classList.remove("self", "opponent");
                if (cellValue) {
                    el.classList.add(cellValue === myMark ? "self" : "opponent");
                    if (prev !== next) {
                        el.style.animation = "none";
                        el.offsetHeight;
                        el.style.animation = "";
                    }
                }
                el.textContent = next;
            });

            // Active strip highlight
            const currentTurn = data.state.current_turn;
            document.getElementById("card-challenger").classList.toggle("active", currentTurn === cId);
            document.getElementById("card-accepter").classList.toggle("active", currentTurn === aId);
        }

        if (data.type == "game_state") {
            const currentTurn = data.state.current_turn;
            document.getElementById("turn-indicator").textContent =
                currentTurn == client_id ? "Your turn" : `Player #${currentTurn}'s turn`;
        }

        else if (data.type == "game_win" || data.type == "game_draw" || data.type == "game_forfit") {
            const eloUpdates = data.state.elo_updates;
            const myUpdate = eloUpdates ? eloUpdates[client_id] : null;
            const go_to_lobby_button = document.getElementById("lobbybtn");
            const turnIndicator = document.getElementById("turn-indicator");
            
            let resultText = "Game Over";
            document.getElementById("forfitbtn").style.display = "none";
            if (data.type == "game_win") {
                resultText = data.state.current_turn == client_id ? "YOU WON!" : "YOU LOST!";
            } 

            else if (data.type == "game_draw") {
                resultText = "DRAW!";
            } 

            else if (data.type == "game_forfit"){
                // If current_turn is me, the other person forfeited. If not, I forfeited.
                resultText = (data.state.current_turn == client_id) ? "OPPONENT LEFT - YOU WIN!" : "YOU FORFEITED - YOU LOSE!";
            }

            turnIndicator.innerHTML = `${resultText} ${formatEloChange(myUpdate)}`;
            go_to_lobby_button.style.display = "block";
        }
    };
}

function move(cellIndex) { // This is called when the cell is pressed whcih send to backend to verify and place
    if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
        const payload = {
            "type": "make_move",
            "cell_index": cellIndex
        };
        gameSocket.send(JSON.stringify(payload));
        console.log("Pressed cell number", cellIndex)
    }
}

function lobby(){
    if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
        gameSocket.close(); // Triggers disconnect on the server
    }
    isInMatch = false;

    // go back to the lobby
    document.getElementById("lobby").style.display = "flex";
    document.getElementById("game-view").style.display = "none";
    document.getElementById("lobbybtn").style.display = "none";
    document.querySelectorAll('.cell').forEach(c => {
        c.textContent = "";
        c.classList.remove("self", "opponent");
    });
    document.getElementById("turn-indicator").textContent = "";
    document.getElementById("card-challenger").classList.remove("active");
    document.getElementById("card-accepter").classList.remove("active");

    document.querySelectorAll('.challenge-btn').forEach(btn => {
        // Only re-enable if the player isn't actually busy in another game
        if (!btn.textContent.includes('Playing')) {
            btn.disabled = false;
            btn.classList.remove('busy');
        }
    });
}

function leaderboard() {
    document.getElementById("player_zone").style.display = "none";
    document.getElementById("Leaderboard").style.display = "flex";
    document.getElementById("tab-players").classList.remove("active");
    document.getElementById("tab-lb").classList.add("active");
}

function player_zone() {
    document.getElementById("player_zone").style.display = "block";
    document.getElementById("Leaderboard").style.display = "none";
    document.getElementById("tab-players").classList.add("active");
    document.getElementById("tab-lb").classList.remove("active");
}

function createPlayerRow(id, name, status, elo=1200){
    const li = document.createElement('li');
    li.className = 'player-item';

    const isBusy = status === "busy";
    const isButtonDisabled = isBusy || isInMatch; 

   li.innerHTML = `
        ${generateAvatarHtml(id, status)}
        <div class="pname-group" style="display:flex; flex-direction:column; margin-left:10px; flex:1;">
            <span class="pname">${name}</span>
            <span class="p-elo" style="font-size:11px; color:#888780;">(${elo})</span>
        </div>
        <button class="challenge-btn ${isButtonDisabled ? 'busy' : ''}" ${isButtonDisabled ? 'disabled' : ''}>
            ${isBusy ? 'Playing' : 'Challenge'}
        </button>`;

    li.querySelector('.challenge-btn').onclick = () => {
        if (isInMatch || status === "busy") return; 

        ws.send(JSON.stringify({
            "type": "challenge",
            "message": id,
        }));
    };

    return li;
}

function forfit() {
    if (confirm("Are you sure you want to forfeit the match?")) {
        if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
            gameSocket.send(JSON.stringify({ "type": "forfeit" }));
        }
    }
}

function formatEloChange(update) {
    if (!update) return "";
    const color = update.diff >= 0 ? "#81b64c" : "#c55a4a";
    const arrow = update.diff >= 0 ? "▲" : "▼";
    const sign = update.diff >= 0 ? "+" : "";
    return `<span style="color: ${color}; margin-left: 8px;">
                ${update.new} ${arrow} (${sign}${update.diff})
            </span>`;
}

function generateAvatarHtml(uid, status) {
    const isBusy = status === "busy";
    // Deterministic "randomness" based on UID
    const marks = ['X', 'O', '', 'X', 'O', 'X']; 
    const boardPattern = [
        marks[uid % 6], 
        marks[(uid + 1) % 6], 
        marks[(uid + 2) % 6], 
        marks[(uid + 3) % 6]
    ];

    let boardHtml = boardPattern.map(m => `<div class="a-cell">${m}</div>`).join('');

    return `
        <div class="chess-avatar-container">
            <div class="avatar-board-2x2">${boardHtml}</div>
            <div class="status-indicator ${isBusy ? 'busy' : 'online'}"></div>
        </div>`;
}

    window.onload = () => {
        console.log("Current URL Search:", window.location.search);
        const urlParams = new URLSearchParams(window.location.search);
        const uid = urlParams.get('uid');

        if (uid) {
            console.log("Credentials detected. Initializing lobby...");
            start_lobby(uid);
        } 
        else {
            document.body.innerHTML = "<h1>Error: Please login via Facial Recognition first.</h1>";
        }
    };

    window.leaderboard = leaderboard;
    window.player_zone = player_zone;
    window.sendMessage = sendMessage;
    window.lobby = lobby;
    window.move = move;
    window.forfit = forfit;
})();