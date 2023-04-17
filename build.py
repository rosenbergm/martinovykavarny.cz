import csv
import json
import re
import requests
from time import sleep

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By

places = []

with open("data/result.csv", newline="") as csvfile:
    csv_reader = csv.reader(csvfile)
    next(csv_reader)
    for row in csv_reader:
        # 7 is the index for a map link
        places.append(row[7])

browser = Firefox()
browser.maximize_window()
browser.get("https://maps.google.com")

# Deal with cookies
if "consent.google.com" in browser.current_url:
    no_consent = browser.find_element(
        By.CSS_SELECTOR, 'button[aria-label="Odmítnout vše"]'
    )
    no_consent.click()

place_images = {}
place_opening_hours = {}

for place in places:
    place_id = place.split("/")[-1]
    print(place_id)

    # Open the coffee place's page
    browser.get(place)
    sleep(5)

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
    ]

    # Go back to the business overview
    browser.execute_script("window.history.go(-1)")
    sleep(2)

    ### Opening hours

    # Click on the opening hours
    hours_icon = browser.find_element(
        By.CSS_SELECTOR,
        'img[src$="schedule_gm_blue_24dp.png"]',
    )
    hours_icon.find_element(By.XPATH, "..").click()

    sleep(0.1)

    # Select the opening hours table (first table in the document)
    opening_hours_table = browser.find_element(By.CSS_SELECTOR, "tbody")

    # Parse the opening hours for each day
    opening_hours_rows = opening_hours_table.find_elements(
        By.CSS_SELECTOR, "tr > td:nth-child(2) > ul"
    )

    place_opening_hours[place_id] = dict(
        enumerate(map(lambda d: d.text, opening_hours_rows))
    )

# Save the opening hours
with open("data/opening_hours.json", "w") as f:
    json.dump(place_opening_hours, f)

# Save the images
for place, links in place_images.items():
    for i, link in enumerate(links):
        with open(f"data/images/{place}_{i}.jpeg", "wb") as f:
            f.write(requests.get(link).content)
