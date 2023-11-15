import json
import os
import secrets
import requests

import dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
    BackgroundTasks,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

dotenv.load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

admin_auth = HTTPBasic()
templates = Jinja2Templates(directory="templates")


def get_admin_auth(credentials: HTTPBasicCredentials = Depends(admin_auth)):
    correct_username = secrets.compare_digest(
        os.getenv("MK_USERNAME"), credentials.username
    )
    correct_password = secrets.compare_digest(
        os.getenv("MK_PASSWORD"), credentials.password
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Co tady sakra zkoušíš?",
        )


def color_by_rating(rating: str):
    match rating:
        case "excellent":
            return "#9c27b0"
        case "recommend":
            return "#0288d1"
        case "meh":
            return "#afb42b"
        case _:
            return "#bebebe"


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, _=Depends(get_admin_auth)):
    return templates.TemplateResponse("admin.jinja.html", {"request": request})


@app.post("/sweep", response_class=HTMLResponse)
async def sweep(
    request: Request, background_tasks: BackgroundTasks, _=Depends(get_admin_auth)
):
    background_tasks.add_task(lambda: os.system("python build.py"))  # help

    return RedirectResponse("/admin", status_code=302)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    places = []

    data = requests.get(
        "https://db.martinovykavarny.cz/api/collections/places/records?perPage=1000",
        headers={"Accept": "application/json"},
    ).json()

    for place in data["items"]:
        places.append(
            {
                "coordinates": [float(place["latitude"]), float(place["longitude"])],
                "color": color_by_rating(place["rating"]),
                "name": place["name"],
                "description": place["description"],
                "address": place["address"],
                "link": place["maps_link"],
                "id": place["id"],
                "hours": place["opening_hours"],
                "images": place["images"],
            }
        )

    return templates.TemplateResponse(
        "index.jinja.html",
        {"request": request, "places": places},
    )


@app.get("/offline", response_class=HTMLResponse)
async def offline(request: Request):
    places = []

    return templates.TemplateResponse(
        "offline.jinja.html", {"request": request, "places": places}
    )


@app.get("/manifest.json", response_class=JSONResponse)
async def manifest(_: Request):
    with open("static/manifest.json") as file:
        return JSONResponse(content=json.load(file))


@app.get("/worker.js", response_class=FileResponse)
async def worker(_: Request):
    return FileResponse("static/worker.js")
