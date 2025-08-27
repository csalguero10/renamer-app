import os, uuid, time

def new_session_state(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "created": time.time(),
        "items": [],  # list of dicts per image
    }

def new_item(image_id: str, path: str, original_filename: str) -> dict:
    return {
        "id": image_id,
        "path": path,
        "original_filename": original_filename,
        "type": None,
        "validated": False,
        "page_number": None,  # int | False
        "number_scheme": "arabic",
        "extra": "",
        "ghost_number": False,
        "graphic": False,
        "new_filename": None,
    }
