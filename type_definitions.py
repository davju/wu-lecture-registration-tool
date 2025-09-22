from typing import List, Optional, TypedDict
from playwright.sync_api import Locator


class LectureContent(TypedDict):
    lecture_names: List[str]
    registration_buttons: List[Optional[Locator]]