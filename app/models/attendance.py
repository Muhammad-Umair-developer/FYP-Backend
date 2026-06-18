from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AttendanceModel(BaseModel):
    student_id: str
    name: Optional[str] = None
    date: Optional[datetime] = None
    status: str = "Present"
    course_name: Optional[str] = None
    course_code: Optional[str] = None