from playwright.sync_api import sync_playwright, Page, Locator
import os
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from typing import Mapping, List
load_dotenv()

import time

def check_login_sucess(content:str, matrikelnummer:str) -> bool:
    soup = BeautifulSoup(content, features="html.parser")

    elements = soup.find_all("b")
    for element in elements:
        print(str(element))
        if matrikelnummer.replace("h", "") in str(element):
            return True

    return False

def extract_lv_content(page:Page) -> Mapping[str, List[Locator]]:
    lecture_table = page.get_by_role("table").nth(1)

    rows = lecture_table.locator("tr").all()

    lectures = {
            "lecture_names": [], 
            "registration_buttons": []
        }
    for row in rows:
        row_string = " ".join(row.text_content().strip().split())

        if not "LV anmelden" in row_string:
            continue
        lecture_name = re.search(r'\b(?:LVP|VUE|PI)\s(.*?)\sLV anmelden', row_string).group(1)
        register_button = row.get_by_role("button").get_by_title("Lehrveranstaltungsanmeldung")
        
        #lectures["is_selectable"].append(not register_button.is_disabled())
        lectures["lecture_names"].append(lecture_name)
        lectures["registration_buttons"].append(register_button)

    return lectures

    
def main():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://lpis.wu.ac.at/lpis/")
        textboxes = page.get_by_role("textbox")
        textboxes.nth(0).fill(os.getenv("MATRIKELNUMMER"))
        textboxes.nth(1).fill(os.getenv("PASSWORT"))

        submit_button = page.get_by_role("button", name="Login")

        submit_button.click()

        content = page.content()

        if not check_login_sucess(content, os.getenv("MATRIKELNUMMER")):
            raise Exception("Login did not finish sucessfully")
        
        lecture_registration_links = page.get_by_title("Lehrveranstaltungsanmeldung").all()

        lecture_registration_names = page.get_by_text("LVP").all()

        '''
        lecture_table = page.get_by_role("table").nth(1)

        rows = lecture_table.locator("tr").all()

        lectures = {
            "lecture_names": [],
            "registration_buttons": []
        }
        for row in rows:
            row_string = " ".join(row.text_content().strip().split())

            if not "LV anmelden" in row_string:
                continue
            lecture_name = re.search(r'\b(?:LVP|VUE|PI)\s(.*?)\sLV anmelden', row_string).group(1)
            register_button = row.get_by_role("button").get_by_title("Lehrveranstaltungsanmeldung")

            lectures["lecture_names"].append(lecture_name)
            lectures["registration_buttons"].append(register_button)
        '''

        lv_content = extract_lv_content(page)

        for name, button in zip(lv_content["lecture_names"], lv_content["registration_buttons"]):
            print(name, button)
        time.sleep(5)

        browser.close()


if __name__ == "__main__":
    main()