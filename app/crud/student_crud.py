from app.core.database import get_collection
from app.models.student import StudentModel
import re
from typing import List, Dict, Optional

class StudentCRUD:
    def __init__(self, collection_name: str = "students"):
        """Initialize CRUD with a dynamically specified collection name"""
        self.collection = get_collection(collection_name)

    def create_student(self, student: StudentModel, class_name: Optional[str] = None):
        """Create a new student"""
        target_collection = self.collection
        if class_name:
            target_collection = get_collection(f"students-{class_name}")
        target_collection.insert_one(student.dict() if hasattr(student, 'dict') else student)
        
    def get_student_by_id(self, student_id: str, class_name: Optional[str] = None):
        """Get student by ID (supports both exact and numeric ID matching)"""
        target_collection = self.collection
        if class_name:
            target_collection = get_collection(f"students-{class_name}")
            
        # First try exact match
        student = target_collection.find_one({"student_id": student_id}, {"_id": 0})
        if student:
            return student
        
        # If not found and target collection is default, scan all students-* collections
        if not class_name and self.collection.name == "students":
            from app.core.database import db
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    col = db[col_name]
                    student = col.find_one({"student_id": student_id}, {"_id": 0})
                    if student:
                        return student
        
        # If not found, try numeric ID match
        numeric_id = student_id.lstrip('0') if student_id.isdigit() else student_id
        students = list(target_collection.find({}, {"_id": 0}))
        for doc in students:
            doc_id = doc.get("student_id", "")
            numeric_part = re.sub(r'.*-(\d+)$', r'\1', doc_id)
            if numeric_part == numeric_id or numeric_part == student_id:
                return doc
                
        # Also try numeric ID match in class-isolated collections if no class_name override is passed and we are default
        if not class_name and self.collection.name == "students":
            from app.core.database import db
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    col = db[col_name]
                    students = list(col.find({}, {"_id": 0}))
                    for doc in students:
                        doc_id = doc.get("student_id", "")
                        numeric_part = re.sub(r'.*-(\d+)$', r'\1', doc_id)
                        if numeric_part == numeric_id or numeric_part == student_id:
                            return doc
        
        return None
    
    def list_students(self, skip: int = 0, limit: int = 50, class_name: Optional[str] = None) -> List[Dict]:
        """List students with pagination"""
        target_collection = self.collection
        if class_name:
            target_collection = get_collection(f"students-{class_name}")
            return list(target_collection.find({}, {"_id": 0}).skip(skip).limit(limit))
            
        if self.collection.name == "students":
            from app.core.database import db
            all_students = list(self.collection.find({}, {"_id": 0}))
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    all_students.extend(list(db[col_name].find({}, {"_id": 0})))
            return all_students[skip:skip+limit]
            
        return list(self.collection.find({}, {"_id": 0}).skip(skip).limit(limit))
    
    def count_students(self, class_name: Optional[str] = None) -> int:
        """Get total student count"""
        if class_name:
            return get_collection(f"students-{class_name}").count_documents({})
            
        if self.collection.name == "students":
            from app.core.database import db
            total = self.collection.count_documents({})
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    total += db[col_name].count_documents({})
            return total
            
        return self.collection.count_documents({})
    
    def search_by_name(self, query: str, class_name: Optional[str] = None) -> List[Dict]:
        """Search students by name (case-insensitive)"""
        target_collection = self.collection
        if class_name:
            target_collection = get_collection(f"students-{class_name}")
            return list(target_collection.find(
                {"name": {"$regex": query, "$options": "i"}},
                {"_id": 0}
            ))
            
        if self.collection.name == "students":
            from app.core.database import db
            results = list(self.collection.find(
                {"name": {"$regex": query, "$options": "i"}},
                {"_id": 0}
            ))
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    results.extend(list(db[col_name].find(
                        {"name": {"$regex": query, "$options": "i"}},
                        {"_id": 0}
                    )))
            return results
            
        return list(self.collection.find(
            {"name": {"$regex": query, "$options": "i"}},
            {"_id": 0}
        ))
    
    def update_student(self, student_id: str, update_data: Dict, class_name: Optional[str] = None) -> Dict:
        """Update student data"""
        target_collection = self.collection
        if class_name:
            target_collection = get_collection(f"students-{class_name}")
            
        result = target_collection.find_one_and_update(
            {"student_id": student_id},
            {"$set": update_data},
            return_document=True,
            projection={"_id": 0}
        )
        if result:
            return result
            
        # If not found and target is default, try to find in dynamic collections
        if not class_name and self.collection.name == "students":
            from app.core.database import db
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    col = db[col_name]
                    result = col.find_one_and_update(
                        {"student_id": student_id},
                        {"$set": update_data},
                        return_document=True,
                        projection={"_id": 0}
                    )
                    if result:
                        return result
        return {}
    
    def delete_student(self, student_id: str, class_name: Optional[str] = None) -> int:
        """Delete a student"""
        target_collection = self.collection
        if class_name:
            target_collection = get_collection(f"students-{class_name}")
            result = target_collection.delete_one({"student_id": student_id})
            return result.deleted_count
            
        result = target_collection.delete_one({"student_id": student_id})
        if result.deleted_count > 0:
            return result.deleted_count
            
        # Fallback for dynamic collections if default
        deleted = 0
        if not class_name and self.collection.name == "students":
            from app.core.database import db
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    col = db[col_name]
                    result = col.delete_one({"student_id": student_id})
                    deleted += result.deleted_count
        return deleted
    
    def get_all_embeddings(self, class_name: Optional[str] = None) -> Dict[str, list]:
        """Get all student embeddings as dict {student_id: embedding}"""
        target_collection = self.collection
        if class_name:
            target_collection = get_collection(f"students-{class_name}")
            students = list(target_collection.find({}, {"_id": 0, "student_id": 1, "embedding": 1}))
            embeddings = {}
            for student in students:
                if student.get("embedding"):
                    embeddings[student["student_id"]] = student["embedding"]
            return embeddings
            
        if self.collection.name == "students":
            from app.core.database import db
            embeddings = {}
            for student in list(self.collection.find({}, {"_id": 0, "student_id": 1, "embedding": 1})):
                if student.get("embedding"):
                    embeddings[student["student_id"]] = student["embedding"]
            for col_name in db.list_collection_names():
                if col_name.startswith("students-"):
                    for student in list(db[col_name].find({}, {"_id": 0, "student_id": 1, "embedding": 1})):
                        if student.get("embedding"):
                            embeddings[student["student_id"]] = student["embedding"]
            return embeddings
            
        students = list(self.collection.find({}, {"_id": 0, "student_id": 1, "embedding": 1}))
        embeddings = {}
        for student in students:
            if student.get("embedding"):
                embeddings[student["student_id"]] = student["embedding"]
        return embeddings