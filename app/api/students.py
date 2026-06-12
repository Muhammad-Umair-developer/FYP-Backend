from fastapi import APIRouter, HTTPException, Depends, Query
from app.models.student import StudentModel
from app.crud.student_crud import StudentCRUD
from app.core.security import get_current_user
from typing import List

router = APIRouter()
crud = StudentCRUD()


# ==================== CREATE ====================

@router.post("/register")
def register_student(
    student: StudentModel
):
    """Register a new student"""
    if crud.get_student_by_id(student.student_id):
        raise HTTPException(status_code=400, detail="Student already exists")

    crud.create_student(student)
    return {"message": "Student registered successfully", "student_id": student.student_id}


# ==================== READ ====================

@router.get("/list")
def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Get all students with pagination"""
    students = crud.list_students(skip, limit)
    return {"students": students, "count": len(students)}


@router.get("/search/by-name")
def search_students_by_name(
    query: str = Query(..., min_length=1)
):
    """Search students by name"""
    results = crud.search_by_name(query)
    if not results:
        raise HTTPException(status_code=404, detail="No students found")
    return {"results": results, "count": len(results)}


@router.get("/{student_id}")
def get_student(
    student_id: str
):
    """Get a specific student by ID"""
    student = crud.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# ==================== UPDATE ====================

@router.put("/{student_id}")
def update_student(
    student_id: str,
    update_data: dict
):
    """Update student information"""
    student = crud.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    updated = crud.update_student(student_id, update_data)
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update student")
    
    return {"message": "Student updated successfully", "student_id": student_id}


# ==================== DELETE ====================

@router.delete("/{student_id}")
def delete_student(
    student_id: str
):
    """Delete a student"""
    student = crud.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    crud.delete_student(student_id)
    return {"message": "Student deleted successfully", "student_id": student_id}
