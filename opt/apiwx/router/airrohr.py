from fastapi import APIRouter, HTTPException
import json

router = APIRouter()

@router.get("/")
async def get_airrohr():
    try:
        with open('/home/weewx/public_html/data/json/current_airrohr.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Internal Server Error. Data not found.")
