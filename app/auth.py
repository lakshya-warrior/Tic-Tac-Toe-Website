from fastapi import APIRouter, File, HTTPException, UploadFile
from app.database import get_all_faces, update_user_status

from utils.facial_recognition_module import build_encodings_cache, find_closest_match

router = APIRouter()

ENCODING_CACHE = None


@router.post("/login")
async def login(file: UploadFile = File(...)):
    global ENCODING_CACHE

    
    #Building the encoding cache, for the first time.
    if ENCODING_CACHE is None:
        print("Building encoding cache... (this will take time once)")
        ENCODING_CACHE = {}
        
        #Using the async function get_all_faces in database.py
        #we did not use sql_functions.py as the functions are synchronous
        faces_list = await get_all_faces()

        #If the faces_list is null, then there was some error in getting images from db
        if not faces_list:
            raise HTTPException(404, "No images exist in the database")

        db_images_dict = {user["uid"]: user["image_data"] for user in faces_list}
        ENCODING_CACHE = build_encodings_cache(db_images_dict)

    # STEP 2: Encode login image
    live_bytes = await file.read()
    matched_uid = find_closest_match(live_bytes, ENCODING_CACHE)

    if matched_uid is None:
        raise HTTPException(401, "No face detected")

    update_user_status(matched_uid, True)
    return {
        "status": "success",
        "uid": matched_uid
    }


@router.post("/logout/{uid}")
async def logout(uid: str):
    """
    TODO:
    1. Call update_user_status(uid, False).
    2. Return confirmation.
    """

    # When logging out, simply set the is_online to false
    update_user_status(uid, False)
    print("The user has logged out! Success!")
    return {"status": "success", "message": "User has Logged Out", "uid": uid}
    
