from fastapi import APIRouter, HTTPException, Query
import json

router = APIRouter()

@router.get("/")
async def get_currentaq(station: str = Query(None), type: str = Query(None)):
    try:
        if station is None:
            station = 'weiden'
        if type is None or type.lower() not in ('s', 'l'):
            type = 's'
        with open('/home/weewx/public_html/data/json/%s_mosmix_%s.json' % (station.lower(), type.lower()), 'r') as file:
            return json.load(file)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail="Internal Server Error. Data not found.")
