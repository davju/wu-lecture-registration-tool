from playwright.sync_api import sync_playwright

import time

MATRIKELNUMMER = "h12222983"
PASSWORT = "d_Bh5rW2ie"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://lpis.wu.ac.at/lpis/")
    textboxes = page.get_by_role("textbox")
    textboxes.nth(0).fill(MATRIKELNUMMER)
    textboxes.nth(1).fill(PASSWORT)

    submit_button = page.get_by_role("button", name="Login")

    submit_button.click()

    print(page.content())


    time.sleep(5)

    browser.close()