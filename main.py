import os
import secrets
from fastapi import Depends, FastAPI, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials


from typing import Annotated

import csv
import dotenv
import httpx

dotenv.load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

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


def color_by_rating(rating: int):
    match rating:
        case 1:
            return "#9c27b0"
        case 2:
            return "#0288d1"
        case 3:
            return "#afb42b"
        case _:
            return "#bebebe"


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, _=Depends(get_admin_auth)):
    return templates.TemplateResponse("admin.jinja.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    places = []

    with open("data/result.csv", newline="") as csvfile:
        spamreader = csv.reader(csvfile)
        next(spamreader)
        for row in spamreader:
            [lon, lat, name, description, address, city, rating] = row
            places.append(
                {
                    "coordinates": [float(lat), float(lon)],
                    "color": color_by_rating(int(rating)),
                    "name": name,
                    "description": description,
                    "address": address,
                }
            )

    return templates.TemplateResponse(
        "index.jinja.html",
        {"request": request, "places": places},
    )


result_header = ["lat", "lon", "name", "description", "address", "city", "rating"]


@app.post("/addPlace", response_class=RedirectResponse)
async def addPlace(
    request: Request,
    name: Annotated[str, Form()],
    lat: Annotated[str, Form()],
    lon: Annotated[str, Form()],
    description: Annotated[str, Form()],
    rating: Annotated[int, Form()],
):
    with open("places/result.csv", "a", newline="\n") as result_file:
        writer = csv.writer(result_file)

        res = httpx.get(
            f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json?access_token=pk.eyJ1Ijoicm9zZW5iZXJnbSIsImEiOiJjamtzYjlnYnkzcjF3M3Fwanc4Nmdmd3IxIn0.j29iER1BDiwOCUCwk4aA9A"
        ).json()

        address = res["features"][0]["place_name"]
        city = next(
            filter(
                lambda x: x["id"].startswith("place"),
                res["features"][0]["context"],
            ),
            {"text": "Prague"},
        )["text"]

        writer.writerow([lat, lon, name, description, address, city, rating])

    return RedirectResponse("/admin", status_code=302)
