from app.core.database import get_collection
from app.models.attendance import AttendanceModel
from datetime import date, datetime
from typing import Union, Dict, List
from bson import ObjectId
import re

collection = get_collection("BSCS_8B")

class AttendanceCRUD:
    
    def mark_attendance(self, attendance: Union[AttendanceModel, Dict]):
        """Create/mark attendance record"""
        if isinstance(attendance, AttendanceModel):
            collection.insert_one(attendance.dict())
        else:
            collection.insert_one(attendance)
    
    def check_attendance(self, student_id: str, attendance_date):
        """Check if student already marked for the date"""
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

    def get_attendance_by_id(self, attendance_id: str) -> Dict:
        """Get a specific attendance record by ID or student_id"""
        try:
            # First try as MongoDB ObjectId
            try:
                result = collection.find_one({"_id": ObjectId(attendance_id)})
                if result:
                    return result
            except Exception:
                pass
            
            # If not a valid ObjectId, try searching by student_id (most recent)
            result = collection.find_one(
                {"student_id": attendance_id},
                sort=[("date", -1)]  # Get most recent record
            )
            if result:
                return result
            
            # Try numeric ID match
            records = list(collection.find({}))
            numeric_id = attendance_id.lstrip('0') if attendance_id.isdigit() else attendance_id
            
            for record in records:
                record_id = record.get("student_id", "")
                numeric_part = re.sub(r'.*-(\d+)$', r'\1', record_id)
                
                if numeric_part == numeric_id or record_id == attendance_id:
                    return record
            
            return None
        except Exception as e:
            print(f"Error in get_attendance_by_id: {str(e)}")
            return None

    def list_attendance(self, skip: int = 0, limit: int = 10, filters: Dict = None) -> List[Dict]:
        """List attendance records with optional filters"""
        query = filters or {}
        records = list(collection.find(query).skip(skip).limit(limit))
        
        # Convert ObjectIds to strings for JSON serialization
        for record in records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
        
        return records

    def update_attendance(self, attendance_id: str, update_data: Dict) -> bool:
        """Update an attendance record"""
        try:
            # First find the record
            record = self.get_attendance_by_id(attendance_id)
            if not record:
                return False
            
            # Update using the _id
            result = collection.update_one(
                {"_id": record["_id"]},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete_attendance(self, attendance_id: str) -> bool:
        """Delete an attendance record"""
        try:
            # First find the record
            record = self.get_attendance_by_id(attendance_id)
            if not record:
                return False
            
            # Delete using the _id
            result = collection.delete_one({"_id": record["_id"]})
            return result.deleted_count > 0
        except Exception:
            return False