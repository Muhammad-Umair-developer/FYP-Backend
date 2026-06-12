from app.core.database import get_collection
from app.models.student import StudentModel
import re
from typing import List, Dict, Optional

collection=get_collection("students")

class StudentCRUD:
    def create_student(self, student:StudentModel):
        """Create a new student"""
        collection.insert_one(student.dict())
        
    def get_student_by_id(self, student_id:str):
        """Get student by ID (supports both exact and numeric ID matching)"""
        # First try exact match
        student = collection.find_one({"student_id":student_id},{"_id":0})
        if student:
            return student
        
        # If not found, try numeric ID match
        numeric_id = student_id.lstrip('0') if student_id.isdigit() else student_id
        students = list(collection.find({}, {"_id": 0}))
        for doc in students:
            doc_id = doc.get("student_id", "")
            numeric_part = re.sub(r'.*-(\d+)$', r'\1', doc_id)
            if numeric_part == numeric_id or numeric_part == student_id:
                return doc
        
        return None
    
    def list_students(self, skip: int = 0, limit: int = 50) -> List[Dict]:
        """List students with pagination"""
        return list(collection.find({}, {"_id": 0}).skip(skip).limit(limit))
    
    def count_students(self) -> int:
        """Get total student count"""
        return collection.count_documents({})
    
    def search_by_name(self, query: str) -> List[Dict]:
        """Search students by name (case-insensitive)"""
        return list(collection.find(
            {"name": {"$regex": query, "$options": "i"}},
            {"_id": 0}
        ))
    
    def update_student(self, student_id: str, update_data: Dict) -> Dict:
        """Update student data"""
        result = collection.find_one_and_update(
            {"student_id": student_id},
            {"$set": update_data},
            return_document=True,
            projection={"_id": 0}
        )
        return result or {}
    
    def delete_student(self, student_id: str) -> int:
        """Delete a student"""
        result = collection.delete_one({"student_id": student_id})
        return result.deleted_count
    
    def get_all_embeddings(self) -> Dict[str, list]:
        """Get all student embeddings as dict {student_id: embedding}"""
        students = list(collection.find({}, {"_id": 0, "student_id": 1, "embedding": 1}))
        embeddings = {}
        for student in students:
            if student.get("embedding"):
                embeddings[student["student_id"]] = student["embedding"]
        return embeddings