import os
from dotenv import load_dotenv
import mysql.connector
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

mongo_client = None
nosql_db = None
mysql_pool = None

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "arena_db"
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3307)) 
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "arena_root")

def init_db():
    global mongo_client, nosql_db, mysql_pool
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    nosql_db = mongo_client[DB_NAME]
    mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=DB_NAME,
    )

def close_db():
    global mongo_client, nosql_db, mysql_pool
    if(mongo_client is not None):
        mongo_client.close()


# --- TODO: IMPLEMENT THESE ---


async def get_student_image(uid: str):
    """
    Use 'await nosql_db.images.find_one()'
    to get the image_data for the given uid.
    """
    # The find_one method return the first occurrence in the selection.
    # It's primarily used for fetching data from collections
    # MongoDB Collection = MySQL tables
    # You can also have queries inside find_one
    # nosql_db.images points to the images collection can also be done using, images_collection = nosql_db["images"]
    images_query = {"uid": uid}

    

    result = await nosql_db.profile_images.find_one(images_query)
    

    # get() Function :
    if result is not None:
        return result.get("image_data") if "image_data" in result else None
    else:
        return None




def update_user_status(uid: str, is_online: bool):
    """
    Use 'mysql_pool.get_connection()' to execute
    an UPDATE query on the 'users' table.
    """
    if(uid is None):
        return
    # MySQL table = MongoDB collection
    # Define the database here using mysql_pool.get_connection()
    database = mysql_pool.get_connection()

    # Setting the update_cursor, the cursor is a pointer from python to MySQL
    # It points to those particular rows and fetches those rows.
    # Use cursor.execute() to execute the query, and we define a cursor for a database.
    update_cursor = database.cursor()

    # Updating the is_online status, via the query using %s as placeholders
    # Use %s as place holders, and while passing the query to the cursor, pass the vars as well.
    update_query = "UPDATE users SET is_online = %s WHERE uid = %s"
    update_cursor.execute(update_query, (is_online, uid))

    # Database doesn't update without commiting.
    database.commit()
    update_cursor.close()
    database.close()

 


def get_user_metadata(uid: str):
    """
    Use a 'dictionary=True' cursor to SELECT
    name and elo_rating from the 'users' table.
    """

    database = mysql_pool.get_connection()

    #dictionary = True simply changes how the data is accessed, now we can use the values by the key
    metadata_cursor = database.cursor(dictionary=True)

    metadata_query = "SELECT name, elo_rating FROM users WHERE uid = %s"

    #executing the metadata query
    metadata_cursor.execute(metadata_query, (uid,))

    #fetchone is very similar to find_one, as it returns the very first row from the matching query
    #and keeps going to the next row
    result = metadata_cursor.fetchone()
    metadata_cursor.close()

    #Closing the database and then returning the result
    database.close()

    return result

async def get_all_faces():
    """

    Fetching all faces from MongoDB
    """

    #Note that find() returns an asynchronous cursor, and not directly the data,
    #which is why while writing a for loop, we must have the async keyword before it.
    get_all_face_query = {}
    result = nosql_db.profile_images.find(get_all_face_query)
    
   
    to_return = []
    #Simply iterating over all the docs in the cursor and returning a list.
    async for doc in result:
        if "uid" in doc:
            if "image_data" in doc:
                to_return.append({"uid" : doc["uid"],
                                   "image_data" : doc["image_data"]})
    
    return to_return




