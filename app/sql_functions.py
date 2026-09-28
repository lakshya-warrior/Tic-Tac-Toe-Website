import math
import os

import pymysql
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv() # Load environment variables

def connect_to_sql():
    #establish and return connection to mysql db
    try:
        sqlhost = os.getenv("MYSQL_HOST")
        sqlport = int(os.getenv("MYSQL_PORT"))
        sqluser = os.getenv("MYSQL_USER")
        sqlpassword = os.getenv("MYSQL_PASSWORD")
        conn = pymysql.connect(
            host = sqlhost, port = sqlport, user = sqluser, password = sqlpassword,
            database = "arena_db", cursorclass=pymysql.cursors.DictCursor 
        ) #fetch all values as dict
        return conn
    except Exception as e:
        print(f"Connection to MYSQL failed: {e}")
        return None

def update_online_status(uid: str, online: bool = False):
    sql_conn = connect_to_sql()
    if sql_conn is None:
        return
    else:
        try:
            with sql_conn.cursor() as cursor:        
                cursor.execute("""UPDATE users SET is_online = %s WHERE uid = %s""", (online, uid))
            sql_conn.commit()
            print("Status updated succesfully..")
            # sql_conn.close()
        except:
            print("Error executing SQL")
        finally:
            sql_conn.close()


def update_elo(winnerid: str, loserid: str, draw: bool):
    sql_conn = connect_to_sql()
    if sql_conn is None:
        return
    else:
        try:
            with sql_conn.cursor() as cursor:        
                cursor.execute("""SELECT elo_rating FROM users WHERE uid = %s""", (winnerid,))
                winner_elo = cursor.fetchone()['elo_rating']
                cursor.execute("""SELECT elo_rating FROM users WHERE uid = %s""", (loserid,))
                loser_elo = cursor.fetchone()['elo_rating']

                ewinner = 1 / (1+math.pow(10 , (loser_elo-winner_elo)/400))
                eloser = 1 / (1+math.pow(10 , (winner_elo-loser_elo)/400))
                
                k = 32
                sw = 0.5 if draw else 1
                sl = 0.5 if draw else 0
                winner_new_elo = round(winner_elo + k * (sw - ewinner))
                loser_new_elo = round(loser_elo + k * (sl - eloser))

                cursor.execute("""UPDATE users SET elo_rating = %s WHERE uid = %s""", (winner_new_elo, winnerid))
                cursor.execute("""UPDATE users SET elo_rating = %s WHERE uid = %s""", (loser_new_elo, loserid))
            sql_conn.commit()
            print(f"Ratings updated: {winnerid} is now {winner_new_elo}, {loserid} is now {loser_new_elo}")
            return {
                winnerid: {"new": winner_new_elo, "diff": winner_new_elo - winner_elo},
                loserid: {"new": loser_new_elo, "diff": loser_new_elo - loser_elo}
            }
        except:
            print("Error executing SQL")
        finally:
            sql_conn.close()

def connect_to_mongo():
    try:
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017/')
        client = MongoClient(mongo_uri)
        
        client.admin.command('ping') 
        return client
    except Exception as e:
        print(f"Connection to MongoDB failed: {e}")
        return None

def get_all_faces_from_mongo():
    #return list of dictionaries with uid and image data as keys
    mongo_client = connect_to_mongo()
    
    if mongo_client is None:
        return []
    
    try:
        db = mongo_client['arena_db']
        images_collection = db['profile_images']

        cursor = images_collection.find({}, {'_id': 0, 'uid': 1, 'image_data': 1})
        faces_list = list(cursor)
        return faces_list
    except Exception as e:
        print(f"Error fetching faces from MongoDB: {e}")
        return []
        
    finally:
        mongo_client.close()


def get_leaderboard():
    #return list of dictionaries with name, elo_rating as keys
    sql_conn = connect_to_sql()
    if sql_conn is None:
        return []
    else:
        try:
            with sql_conn.cursor() as cursor:        
                cursor.execute("SELECT name, elo_rating FROM users ORDER BY elo_rating DESC")
                leaderboard = cursor.fetchall()
                return leaderboard
            sql_conn.close()
        except Exception as e:
            print(f"Error fetching leaderboard: {e}")
            return []
        finally:
            sql_conn.close()

def get_player(uid: str):
    sql_conn = connect_to_sql()
    if sql_conn is None:
        return None
    try:
        with sql_conn.cursor() as cursor:        
            # Using DictCursor means 'result' is a dictionary
            cursor.execute("SELECT name, is_online, elo_rating FROM users WHERE uid = %s LIMIT 1", (uid,))
            result = cursor.fetchone()
            
            if result:
                return (result['name'], result['is_online'], result['elo_rating'])
            return None
    except Exception as e:
        print(f"SQL Error in get_player: {e}")
        return None
    finally:
        sql_conn.close()

if __name__ == "__main__":
    users = get_leaderboard()
    for i in users:
        print(i)