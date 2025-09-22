from typing import List, Optional, TypedDict, Dict
from playwright.sync_api import Locator


class LectureContent(TypedDict):
    lecture_names: List[str]
    registration_buttons: List[Optional[Locator]]

class CourseData(TypedDict):
    course_id: Optional[str]
    semester: Optional[str]
    instructor: Optional[str]
    course_title: Optional[str]
    capacity: Optional[str]
    registration_time: Optional[str]
    registration_status: Optional[str]
    button_enabled: bool
    button_value: Optional[str]
    form_name: Optional[str]
    form_id: Optional[str]
    form_action: Optional[str]
    form_method: Optional[str]
    hidden_fields: Dict[str, str]