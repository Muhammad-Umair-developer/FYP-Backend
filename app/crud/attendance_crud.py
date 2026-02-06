from app.core.database import get_collection
from app.models.attendance import AttendanceModel
from datetime import date
from typing import Union, Dict

collection=get_collection("BSCS_8B")

class AttendanceCRUD:
    def mark_attendance(self, attendance:Union[AttendanceModel, Dict]):
        if isinstance(attendance, AttendanceModel):
            collection.insert_one(attendance.dict())
        else:
            collection.insert_one(attendance)
        
    def check_attendance(self, student_id:str, attendance_date:date):
        return collection.find_one({"student_id":student_id, "date":attendance_date})