from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AttendanceModel(BaseModel):
    student_id:str
    name:Optional[str]=None
    date:datetime
    status:str="Present"
    