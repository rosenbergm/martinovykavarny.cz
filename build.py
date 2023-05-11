import csv
import json
import pathlib
import re
import requests
from time import sleep

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

places = []
scanned = pathlib.Path("data/scanned.txt").read_text().split("\n")
with open("data/opening_hours.json") as file:
    place_opening_hours = json.load(file)

with open("data/result.csv", newline="") as csvfile:
    csv_reader = csv.reader(csvfile)
    next(csv_reader)
    for row in csv_reader:
        # 7 is the index for a map link
        places.append(row[7])

browser = Firefox()
browser.maximize_window()
browser.get("https://maps.google.com")

# Zoom out three times
for _ in range(3):
    # Send keys
    browser.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.COMMAND + "-")

place_images = {}

for place in places:
    place_id = place.split("/")[-1]

    if place_id in scanned:
        continue

    print(place_id)

    # Open the coffee place's page
    browser.get(place)
    sleep(5)

    # Deal with cookies
    if "consent.google.c" in browser.current_url:
        no_consent = browser.find_element(
            By.CSS_SELECTOR, 'button[aria-label="Odmítnout vše"]'
        )
        no_consent.click()

    ### Images

    # Click on the images icon
    browser.find_element(
        By.CSS_SELECTOR, 'button[aria-label^="Fotka: "]'
    ).click()

    sleep(3)

    # Find all the images
    images = browser.find_elements(
        By.CSS_SELECTOR, 'div.loaded[style*="googleusercontent.com"]'
    )
    # Extract the image links
    place_images[place_id] = [
        re.search(
            r'url\("(?P<image_link>.*)"\)', i.get_attribute("style")
        ).group("image_link")
        for i in images
    ][:3]

    # Save the images
    for i, link in enumerate(place_images[place_id]):
        with open(f"data/images/{place_id}_{i}.jpeg", "wb") as f:
            f.write(requests.get(link).content)

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

        place_opening_hours[place_id] = dict(
            enumerate(map(lambda d: d.text, opening_hours_rows))
        )
    except:
        place_opening_hours[place_id] = None

    # Append the opening hours to the JSON file with opening hourse
    with open("data/opening_hours.json", "w") as f:
        json.dump(place_opening_hours, f)

    # Mark this place as scanned
    scanned.append(place_id)
    pathlib.Path("data/scanned.txt").write_text("\n".join(scanned))

browser.quit()
