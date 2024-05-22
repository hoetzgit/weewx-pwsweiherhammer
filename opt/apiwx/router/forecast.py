from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import json
import os.path

PATH = '/home/weewx/public_html/data/json/'
PROVIDERS = [
    'aeris',
    'brightsky',
    'dwd-mosmix',
    'om-best-match',
    'om-icon-combined',
    'om-icon-d2',
    'om-icon-eu',
    'om-icon-seamless'
]

router = APIRouter()

@router.get("/")
async def get_forecast(provider: str = Query(None), interval: str = Query(None), column: str = Query(None), total: str = Query(None)):
    if provider is None or provider.lower() == 'all':
        if total is None:
            data_all = dict()
            for prov in PROVIDERS:
                data_all[prov] = dict()
                fn = os.path.join(PATH, 'forecastwx_%s.json' % prov)
                if os.path.exists(fn):
                    with open(fn) as file:
                        data = json.load(file)
                    data_all[prov] = data
            return JSONResponse(content=data_all)
        else:
            fn = os.path.join(PATH, 'forecastwx_total.json')
            data = dict()
            if os.path.exists(fn):
                with open(fn) as file:
                    data = json.load(file)
            return JSONResponse(content=data)
    elif provider.lower() in PROVIDERS:
        data = dict()
        data[provider] = dict()
        if total is None:
            fn = os.path.join(PATH, 'forecastwx_%s.json' % provider.lower())
        else:
            fn = os.path.join(PATH, 'forecastwx_total.json')
        if os.path.exists(fn):
            with open(fn) as file:
                data = json.load(file)
        else:
            raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s)" % provider)
        if total is not None and provider.lower() not in data:
            raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s)" % provider)
        if total is None:
            if interval is None:
                return JSONResponse(content=data)
            elif interval.lower() in data:
                if column is None:
                    return JSONResponse(content=data[interval])
                elif column in data[interval]:
                    return JSONResponse(content=data[provider][interval][column])
                else:
                    raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s, interval=%s, column=%s)" % (provider, interval, column))
            else:
                raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s, interval=%s, column=%s)" % (provider, interval, column))
        else:
            if interval is None:
                return JSONResponse(content=data[provider])
            elif interval.lower() in data[provider]:
                if column is None:
                    return JSONResponse(content=data[provider][interval])
                elif column in data[provider][interval]:
                    return JSONResponse(content=data[provider][interval][column])
                else:
                    raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s, interval=%s, column=%s)" % (provider, interval, column))
            else:
                raise HTTPException(status_code=404, detail="Valid request. No results available based on your query parameters. (provider=%s, interval=%s, column=%s)" % (provider, interval, column))
    else:
        raise HTTPException(status_code=400, detail="Invalid request. Provider %s is not a valid provider!" % provider)
