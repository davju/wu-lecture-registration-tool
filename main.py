from playwright.sync_api import sync_playwright, Page, Locator
import os
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv, set_key
from prompt_toolkit import print_formatted_text, prompt, HTML
from prompt_toolkit.shortcuts import message_dialog, input_dialog, radiolist_dialog, checkboxlist_dialog
import sys
from typing import Mapping, List

import sqlite3


load_dotenv()

import time


class DB_Interface():
    def __init__(self):
        pass

    def init(self , db_file_name:str):
        self.db = sqlite3.connect(db_file_name)

        listOfTables = self.db.cursor().execute(
            """SELECT tbl_name FROM sqlite_master WHERE type='table'
            AND tbl_name='scheduled_registrations'; """).fetchall()
        
        if not listOfTables:
            self.db.execute("CREATE TABLE scheduled_registrations(lecture_name, lecture_index, lecturer_name, lecturer_index, first_possible_registration_timestamp, registration_done, registration_failed)")


    def insert_scheduled_registration(self, lecture_name, lecture_index, lecturer_name, lecturer_index, first_possible_registration_timestamp):
        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO scheduled_registrations VALUES
            (?, ?, ?, ?, ?, NULL, NULL)
        """, (lecture_name, lecture_index, lecturer_name, lecturer_index, first_possible_registration_timestamp))
        self.db.commit()  # Don't forget to commit!
        cur.close()

        

def check_login_sucess(content:str, matrikelnummer:str) -> bool:
    soup = BeautifulSoup(content, features="html.parser")

    elements = soup.find_all("b")
    for element in elements:
        print(str(element))
        if matrikelnummer.replace("h", "") in str(element):
            return True

    return False

def extract_lv_content(page: Page) -> Mapping[str, List[Locator]]:
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
        
        # Updated regex to handle the actual structure
        # The pattern should capture text between LVP/VUE/PI and "LV anmelden"
        match = re.search(r'\b(?:LVP|VUE|PI)\s+(.*?)\s+LV anmelden', row_string)
        if not match:
            continue
            
        lecture_name = match.group(1)
        
        # The registration links are <a> elements, not buttons
        # Use the link with title "Lehrveranstaltungsanmeldung"
        register_button = row.locator('a[title="Lehrveranstaltungsanmeldung"]')
        
        # Check if the locator actually found an element
        if register_button.count() > 0:
            lectures["lecture_names"].append(lecture_name)
            lectures["registration_buttons"].append(register_button)
    
    return lectures

def select_lecture(lv_content) -> int:
    result = radiolist_dialog(
    title="Lecture Dialog",
    text="Which Lecture would you like to register ?",
    default=lv_content["lecture_names"][0],
    values=[
        (index, lecture) for index, lecture in enumerate(lv_content["lecture_names"])
    ]
    ).run(in_thread=True)

    return result

def load_lecture(lv_content, lecture_index:int):
    lv_content["registration_buttons"][lecture_index].click()


def select_and_load_lecture(lv_content):

    result = radiolist_dialog(
    title="Lecture Dialog",
    text="Which Lecture would you like to register ?",
    default=lv_content["lecture_names"][0],
    values=[
        (index, lecture) for index, lecture in enumerate(lv_content["lecture_names"])
    ]
    ).run(in_thread=True)
    
    lv_content["registration_buttons"][result].click()

def select_and_register_lecturer(lecture_information, page:Page):
    
    info_list = lecture_information[0]

    lecture_list = [
        (index, f"Instructor: {info['instructor']} | Capacity: {info['capacity']} | Registration starting {info['registration_time']}") for index, info in enumerate(info_list) if int(info["capacity"].split("/")[0].strip()) > 0
    ]
    result = checkboxlist_dialog(
    title="Lecturer Selection Dialog ",
    text="Which Lecturer would you like to register for",
    default_values=lecture_list[0],
    values=lecture_list
    ).run(in_thread=True)

    lecture_table = page.get_by_role("table").nth(1)

    selected_table_row = lecture_table.locator("tr").nth(result[0])

    register_button = selected_table_row.locator('input[value="anmelden"]')

    print(register_button)
    
    
    return result

def register_lecturer(page:Page, lecturer_index:int):
    lecture_table = page.get_by_role("table").nth(1)

    selected_table_row = lecture_table.locator("tr").nth(lecturer_index)

    register_button = selected_table_row.locator('input[value="anmelden"]')


def select_lecturer(lecture_information):
    info_list = lecture_information[0]

    lecture_list = [
        (index, f"Instructor: {info['instructor']} | Capacity: {info['capacity']} | Registration starting {info['registration_time']}") for index, info in enumerate(info_list) if int(info["capacity"].split("/")[0].strip()) > 0
    ]
    result = radiolist_dialog(
    title="Lecturer Selection Dialog ",
    text="Which Lecturer would you like to register for",
    default=lecture_list[0],
    values=lecture_list
    ).run(in_thread=True)

    return result 

def check_environment(dot_env_path=".env"):
    if not load_dotenv() or not all([os.getenv("MATRIKELNUMMER"), os.getenv("PASSWORT")]):
        # Not .env variables set or not .env file present
        try:
            f = open(".env", "x")
        except FileExistsError:
            pass

        message_dialog(
        title='Credentials',
        text='"Credentials are not set"', ok_text="Set").run()

        
        
        matrikelnummer = ""
        password = ""

        i = 0
        while not all([matrikelnummer, password]):
            if i > 0:
                message_dialog(HTML('<ansired>One or more credentials where empty</ansired>')).run()
            matrikelnummer = input_dialog(
                title='Input your Matrikelnummer',
                text='Please type your matrikelnummer').run()
            #matrikelnummer = prompt("Enter your Matrikelnummer: ")
            password = input_dialog(
                title='Input your Password',
                text='Please type your password').run()

            i+=1


        set_key(dot_env_path,"MATRIKELNUMMER", matrikelnummer)
        set_key(dot_env_path ,"PASSWORT", password)

        print_formatted_text("Credentials where sucessfully set. Programm will restart")
        os.execv(sys.executable, [sys.executable] + sys.argv)

def extract_course_data_with_indexes(html_content):
    """
    Extracts course information from the HTML table including:
    - Instructor names from td.ver_title div elements
    - Capacity information from elements with title="freie LV-Plätze / LV-Kapazität"
    - Registration timestamps from div.timestamp span elements
    - Row indexes for mapping back to table elements
    
    Args:
        html_content (str): HTML content as a string
        
    Returns:
        tuple: (course_data_list, row_indexes_list)
            - course_data_list: List of dictionaries with extracted course information
            - row_indexes_list: List of integers representing the row index in the original table
    """
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all table rows that contain course information
    course_rows = soup.find_all('tr', class_=['td0', 'td1'])
    
    course_data = []
    row_indexes = []
    
    for index, row in enumerate(course_rows):
        course_info = {}
        
        # Extract course ID and semester from the first column
        ver_id_td = row.find('td', class_='ver_id')
        if ver_id_td:
            link = ver_id_td.find('a')
            course_info['course_id'] = link.get_text(strip=True) if link else None
            semester_span = ver_id_td.find('span')
            course_info['semester'] = semester_span.get_text(strip=True) if semester_span else None
        else:
            course_info['course_id'] = None
            course_info['semester'] = None
        
        # Extract instructor name from td.ver_title div
        ver_title_td = row.find('td', class_='ver_title')
        if ver_title_td:
            div_element = ver_title_td.find('div')
            course_info['instructor'] = div_element.get_text(strip=True) if div_element else None
            
            # Also extract the course title
            title_span = ver_title_td.find('span')
            course_info['course_title'] = title_span.get_text(strip=True) if title_span else None
        else:
            course_info['instructor'] = None
            course_info['course_title'] = None
        
        # Extract capacity information
        capacity_element = row.find(attrs={'title': 'freie LV-Plätze / LV-Kapazität'})
        course_info['capacity'] = capacity_element.get_text(strip=True) if capacity_element else None
        
        # Extract registration timestamp
        timestamp_div = row.find('div', class_='timestamp')
        if timestamp_div:
            span_element = timestamp_div.find('span')
            course_info['registration_time'] = span_element.get_text(strip=True) if span_element else None
        else:
            course_info['registration_time'] = None
        
        # Extract registration status
        registration_box = row.find('td', class_=['box', 'registration'])
        if registration_box:
            status_div = registration_box.find('div')
            course_info['registration_status'] = status_div.get_text(strip=True) if status_div else None
        else:
            course_info['registration_status'] = None
        
        # Extract button/form information
        form_element = row.find('form')
        if form_element:
            submit_button = form_element.find('input', {'type': 'submit'})
            course_info['button_enabled'] = not submit_button.has_attr('disabled') if submit_button else False
            course_info['button_value'] = submit_button.get('value', '') if submit_button else None
            course_info['form_name'] = form_element.get('name', '')
            course_info['form_id'] = form_element.get('id', '')
            course_info['form_action'] = form_element.get('action', '')
            course_info['form_method'] = form_element.get('method', 'post')
            
            # Extract all hidden form fields
            hidden_inputs = form_element.find_all('input', {'type': 'hidden'})
            course_info['hidden_fields'] = {}
            for hidden_input in hidden_inputs:
                name = hidden_input.get('name')
                value = hidden_input.get('value')
                if name:
                    course_info['hidden_fields'][name] = value or ''
        else:
            course_info['button_enabled'] = False
            course_info['button_value'] = None
            course_info['form_name'] = None
            course_info['form_id'] = None
            course_info['form_action'] = None
            course_info['form_method'] = None
            course_info['hidden_fields'] = {}
        
        # Only add to results if we found at least some course information
        if course_info['course_id'] or course_info['instructor']:
            course_data.append(course_info)
            row_indexes.append(index)
    
    return course_data, row_indexes


def main():

    check_environment()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://lpis.wu.ac.at/lpis/")
        page.wait_for_timeout(1000)
        textboxes = page.get_by_role("textbox")
        textboxes.nth(0).fill(os.getenv("MATRIKELNUMMER"))
        textboxes.nth(1).fill(os.getenv("PASSWORT"))

        submit_button = page.get_by_role("button", name="Login")

        submit_button.click()

        page.wait_for_timeout(1000)

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

        selected_lecture_index = select_lecture(lv_content)

        load_lecture(lv_content, selected_lecture_index)

        page.wait_for_timeout(500)
        course_information = extract_course_data_with_indexes(page.content())

        #select_and_register_lecturer(course_information, page)

        selected_lectuerer_index = select_lecturer(course_information)

        register_lecturer(page, selected_lectuerer_index)

        time.sleep(500)

        browser.close()

if __name__ == "__main__":
    #main()    

    db = DB_Interface() 

    db.init("my_db")

    db.insert_scheduled_registration("test", 1, "test2", 2, "14")