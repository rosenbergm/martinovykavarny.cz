import json
import os
import secrets
import requests

from typing import Annotated

import dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
    BackgroundTasks,
    Form,
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

auth = None


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


@app.on_event("startup")
async def on_startup():
    global auth

    admin = requests.post(
        "https://db.martinovykavarny.cz/api/admins/auth-with-password",
        json={"identity": os.getenv("PB_EMAIL"), "password": os.getenv("PB_PASSWORD")},
    ).json()

    auth = admin


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, _=Depends(get_admin_auth)):
    places = (
        requests.get(
            "https://db.martinovykavarny.cz/api/collections/places/records?perPage=1000&filter=(images:length=0 || longitude=0 || latitude=0 || address=null)",
            headers={"Accept": "application/json"},
        )
        .json()
        .get("items")
    )

    return templates.TemplateResponse(
        "admin.jinja.html", {"request": request, "unpopulated_places": len(places)}
    )


@app.post("/add_place", response_class=HTMLResponse)
async def add_place(
    request: Request,
    name: Annotated[str, Form()],
    maps_link: Annotated[str, Form()],
    rating: Annotated[str, Form()],
    description: Annotated[str, Form()],
    _=Depends(get_admin_auth),
):
    requests.post(
        "https://db.martinovykavarny.cz/api/collections/places/records",
        headers={
            "Authorization": auth["token"],
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "name": name,
                "maps_link": maps_link,
                "rating": rating,
                "description": description,
            }
        ),
    )

    return RedirectResponse("/admin", status_code=302)


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
                "rating": place["rating"],
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
