import os
import csv
import requests
import pymysql
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv() #load env variables from .env file to memory

#fetch mysql credentials
sqlhost = os.getenv("MYSQL_HOST")
sqlport = int(os.getenv("MYSQL_PORT"))
sqluser = os.getenv("MYSQL_USER")
sqlpassword = os.getenv("MYSQL_PASSWORD")
mongo = os.getenv("MONGO_URI")

#establishing connection to mysql container
try:
    conn = pymysql.connect(
        host = sqlhost, port = sqlport, user = sqluser, password = sqlpassword,
        database = "arena_db", cursorclass=pymysql.cursors.DictCursor
    )
    print("Connected to MySQL")

except Exception as e:
    print(f"Connection to MYSQL failed: {e}")
    exit(1)

#connection to mongodb container
try:
    mongo_uri = mongo
    mongo_client = MongoClient(mongo_uri)
    mongo_db = mongo_client['arena_db']
    images = mongo_db['profile_images']
    print("Connected to MongoDB")
except Exception as e:
    print(f"Connection to MongoDB failed : {e}")
    exit(1)

def harvest_data():
    # CHECK IF DATA EXISTS
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    result = cursor.fetchone()
    
    if result and result['count'] > 0:
        print(f"Database already contains {result['count']} users. Skipping harvest.")
        return # This stops the function right here

    # PROCEED WITH HARVEST IF EMPTY
    print("Databases are empty. Starting data harvest...")

    #open csv file, read it as dictionary
    with open("batch_data.csv", mode='r') as f:
        data = csv.DictReader(f)
        success_count = 0
        fail_count = 0

        for lines in data:
            id = lines['uid'].strip()
            name = lines['name'].strip()
            url = lines['website_url'].strip().rstrip('/')

            if not url.startswith('http'):
                url = "http://" + url
            image_url = f"{url}/images/pfp.jpg"

            try:
                response = requests.get(image_url, timeout=5)
                response.raise_for_status() # checks status code and raises error if request failed

                image_binary = response.content
                #if uid already exists, update the name
                cursor.execute("""INSERT INTO users (uid, name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE name=%s
                """, (id, name, name))

                images.update_one(
                    {'uid' : id},
                    {'$set': {'image_data': image_binary}},
                    upsert=True
                )

                print(f"Success: {name} ({id})")
                success_count+=1
            except Exception as e:
                #catch timeouts or 404 error
                print(f"Failed to fetch image of {name} {id} : {e}")
                fail_count += 1
                continue

    conn.commit()
    print(f"\nHarvest Complete! Added {success_count} users. Failed {fail_count} users.")

if __name__ == "__main__":
    harvest_data()
    # close connections
    conn.close()
    mongo_client.close()