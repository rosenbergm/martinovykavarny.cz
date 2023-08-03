import csv
import json
import pathlib
import re
import requests
import io
import dotenv
from time import sleep

import os
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

opts = Options()
opts.headless = True

dotenv.load_dotenv()

admin = requests.post(
    "https://db.martinovykavarny.cz/api/admins/auth-with-password",
    json={"identity": os.getenv("PB_EMAIL"), "password": os.getenv("PB_PASSWORD")},
).json()


with Firefox(options=opts) as browser:
    browser.maximize_window()
    browser.get("https://maps.google.com")

    # Zoom out three times
    for _ in range(3):
        # Send keys
        browser.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.COMMAND + "-")

    place_images = {}

    places = (
        requests.get(
            "https://db.martinovykavarny.cz/api/collections/places/records?perPage=1000&filter=(images:length=0)",
            headers={"Accept": "application/json"},
        )
        .json()
        .get("items")
    )

    for place in places:
        # Open the coffee place's page
        browser.get(place["maps_link"])
        sleep(5)

        # Deal with cookies
        if "consent.google.c" in browser.current_url:
            no_consent = browser.find_element(
                By.CSS_SELECTOR, 'button[aria-label="Odmítnout vše"]'
            )
            no_consent.click()

        ### Images

        # Click on the images icon
        browser.find_element(By.CSS_SELECTOR, 'button[aria-label^="Fotka: "]').click()

        sleep(3)

        # Find all the images
        images = browser.find_elements(
            By.CSS_SELECTOR, 'div.loaded[style*="googleusercontent.com"]'
        )

        # Extract the image links
        place_images[place["id"]] = [
            re.search(r'url\("(?P<image_link>.*)"\)', i.get_attribute("style")).group(
                "image_link"
            )
            for i in images
        ][:3]

        images_to_send = []

        # Save the images
        for i, link in enumerate(place_images[place["id"]]):
            images_to_send.append(
                (
                    "images",
                    (f"{place['id']}_{i}", io.BytesIO(requests.get(link).content)),
                )
            )

        r = requests.patch(
            "https://db.martinovykavarny.cz/api/collections/places/records/"
            + place["id"],
            headers={"Authorization": admin["token"]},
            files=tuple(images_to_send),
        )

        # Go back to the business overview
        browser.execute_script("window.history.go(-1)")
        sleep(3)

        ### Opening hours

        # Click on the opening hours
        try:
            hours_icon = browser.find_element(
                By.CSS_SELECTOR,
                'img[src$="schedule_gm_blue_24dp.png"]',
            )
            hours_icon.find_element(By.XPATH, "..").click()

            sleep(0.5)

            # Select the opening hours table (first table in the document)
            opening_hours_table = browser.find_element(By.CSS_SELECTOR, "tbody")

            # Parse the opening hours for each day
            opening_hours_rows = opening_hours_table.find_elements(
                By.CSS_SELECTOR, "tr > td:nth-child(2) > ul"
            )

            r = requests.patch(
                "https://db.martinovykavarny.cz/api/collections/places/records/"
                + place["id"],
                headers={
                    "Authorization": admin["token"],
                    "Content-Type": "application/json",
                },
                data=json.dumps(
                    {
                        "opening_hours": dict(
                            enumerate(map(lambda d: d.text, opening_hours_rows))
                        )
                    }
                ),
            )
        except:
            pass
