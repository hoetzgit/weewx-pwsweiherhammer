from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from router import current, forecast, warnings, airquality, weewx, airrohr, mosmix

app = FastAPI()

@app.get("/favicon.ico")
async def favicon():
    return PlainTextResponse("")

app.include_router(current.router, prefix="/v1/current")
app.include_router(forecast.router, prefix="/v1/forecast")
app.include_router(warnings.router, prefix="/v1/warnings")
app.include_router(airquality.router, prefix="/v1/airquality")

app.include_router(weewx.router, prefix="/v1/weewx")
app.include_router(airrohr.router, prefix="/v1/airrohr")
app.include_router(mosmix.router, prefix="/v1/mosmix")
