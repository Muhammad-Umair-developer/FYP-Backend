from app.core.database import get_collection
from app.models.attendance import AttendanceModel
from datetime import date, datetime
from typing import Union, Dict
import re

collection=get_collection("BSCS_8B")

class AttendanceCRUD:
    def mark_attendance(self, attendance:Union[AttendanceModel, Dict]):
        if isinstance(attendance, AttendanceModel):
            collection.insert_one(attendance.dict())
        else:
            collection.insert_one(attendance)
        
    def check_attendance(self, student_id:str, attendance_date):
        # Handle both date and datetime objects
        if isinstance(attendance_date, datetime):
            # Search by date only (ignore time)
            start_date = attendance_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = attendance_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = {
                "$or": [
                    {"student_id": student_id, "date": {"$gte": start_date, "$lte": end_date}},
                ]
            }
        else:
            query = {"student_id": student_id, "date": attendance_date}
        
        result = collection.find_one(query)
        
        # If not found with exact ID, try numeric ID match
        if not result:
            records = list(collection.find({}))
            numeric_id = student_id.lstrip('0') if student_id.isdigit() else student_id
            
            for record in records:
                record_id = record.get("student_id", "")
                numeric_part = re.sub(r'.*-(\d+)$', r'\1', record_id)
                
                if isinstance(attendance_date, datetime):
                    start_date = attendance_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = attendance_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    record_date = record.get("date")
                    date_match = start_date <= record_date <= end_date if record_date else False
                else:
                    date_match = record.get("date") == attendance_date
                
                if (numeric_part == numeric_id or record_id == student_id) and date_match:
                    return record
        
        return result