from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import json
import os.path

PATH = '/home/weewx/public_html/data/json/'
PROVIDERS = [
    'aeris',
    'brightsky'
]

router = APIRouter()

@router.get("/")
async def get_warnings(provider: str = Query(None), total: str = Query(None)):
    if provider is None or provider.lower() == 'all':
        if total is None:
            data_all = dict()
            for prov in PROVIDERS:
                data_all[prov] = dict()
                fn = os.path.join(PATH, 'warnwx_%s.json' % prov)
                if os.path.exists(fn):
                    with open(fn) as file:
                        data = json.load(file)
                    data_all[prov] = data
            return JSONResponse(content=data_all)
        else:
            fn = os.path.join(PATH, 'warnwx_total.json')
            data = dict()
            if os.path.exists(fn):
                with open(fn) as file:
                    data = json.load(file)
            return JSONResponse(content=data)
    elif provider.lower() in PROVIDERS:
        data[provider] = dict()
        if total is None:
            fn = os.path.join(PATH, 'warnwx_%s.json' % provider.lower())
        else:
            fn = os.path.join(PATH, 'warnwx_total.json')
        if os.path.exists(fn):
            with open(fn) as file:
                data = json.load(file)
        else:
            raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s)" % provider)
        if total is not None and provider.lower() not in data:
            raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s)" % provider)
        if total is None:
            return JSONResponse(content=data)
        else:
            return JSONResponse(content=data[provider])
    else:
        raise HTTPException(status_code=400, detail="Invalid request. Provider %s is not a valid provider!" % provider)
