from app.core.database import get_collection
from app.models.student import StudentModel
import re

collection=get_collection("students")

class StudentCRUD:
    def create_student(self, student:StudentModel):
        collection.insert_one(student.dict())
        
    def get_student_by_id(self, student_id:str):
        # First try exact match
        student = collection.find_one({"student_id":student_id},{"_id":0})
        if student:
            return student
        
        # If not found, try to find by numeric ID (last part after hyphen)
        # For example: if looking for "1192", also try to find "22-NTU-CS-1192"
        numeric_id = student_id.lstrip('0') if student_id.isdigit() else student_id
        
        # Search for any student_id ending with the numeric ID
        students = list(collection.find({}, {"_id": 0}))
        for doc in students:
            doc_id = doc.get("student_id", "")
            # Extract numeric part from full student ID
            numeric_part = re.sub(r'.*-(\d+)$', r'\1', doc_id)
            if numeric_part == numeric_id or numeric_part == student_id:
                return doc
        
        return None
    
    
    