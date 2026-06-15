from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, Query, Form
from app.models.attendance import AttendanceModel
from app.crud.attendance_crud import AttendanceCRUD
from app.crud.student_crud import StudentCRUD
from datetime import datetime
import cv2
import numpy as np
import os
from typing import Optional

from app.core.security import get_current_user
from app.services.face_matcher import cosine_similarity
from app.core.config import EMBEDDINGS_DIR
from app.services.attendance_logic import process_multiple_faces

router = APIRouter()
crud = AttendanceCRUD()


# ==================== CREATE ====================

@router.post("/mark")
def mark_attendance(
    attendance: AttendanceModel,
    class_name: str = Query(..., description="Target class name"),
    current_user: str = Depends(get_current_user)
):
    """Mark attendance for a student manually"""
    today = datetime.utcnow()

    # Verify student belongs to this class's collection
    student_crud = StudentCRUD()
    student = student_crud.get_student_by_id(attendance.student_id, class_name=class_name)
    if not student:
        raise HTTPException(
            status_code=400,
            detail=f"Student '{attendance.student_id}' does not exist in class '{class_name}'"
        )

    local_crud = AttendanceCRUD(class_name)
    if local_crud.check_attendance(attendance.student_id, today):
        raise HTTPException(status_code=400, detail="Attendance already marked today")

    attendance.date = today
    attendance.status = attendance.status or "Present"
    local_crud.mark_attendance(attendance)

    return {"message": "Attendance marked successfully", "student_id": attendance.student_id, "date": str(today)}


@router.post("/mark-from-image")
async def mark_attendance_from_image(
    class_name: str = Form(..., description="Target class name"),
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    """Mark attendance by uploading student image"""
    try:
        EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "student_embeddings.npy")

        if not os.path.exists(EMBEDDINGS_FILE):
            raise HTTPException(status_code=500, detail="Embeddings file not found")

        # Read and decode image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Fetch student IDs in the targeted class students-[class_name] collection
        student_crud = StudentCRUD()
        class_students = student_crud.list_students(limit=10000, class_name=class_name)
        class_student_ids = {s.get("student_id") for s in class_students if s.get("student_id")}

        # Load global embeddings
        embeddings_data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
        student_ids = embeddings_data["student_ids"]
        embeddings = embeddings_data["embeddings"]

        # Rebuild or slice the candidate embedding matrix dynamically at runtime
        sliced_indices = [idx for idx, s_id in enumerate(student_ids) if s_id in class_student_ids]
        
        # Build sliced list of IDs and list of vectors, keeping indices aligned
        sliced_student_ids = [student_ids[idx] for idx in sliced_indices]
        sliced_embeddings = [embeddings[idx] for idx in sliced_indices]
        
        # Zip them to preserve mapping alignment
        student_embeddings = list(zip(sliced_student_ids, sliced_embeddings))

        # Process faces and mark attendance, dynamically restricting lookup
        results = process_multiple_faces(img_rgb, student_embeddings, class_name=class_name)

        return {
            "message": "Image processed successfully",
            "results": results,
            "processed_by": current_user,
            "timestamp": str(datetime.utcnow())
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


# ==================== READ ====================

@router.get("/")
def list_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    student_id: str = Query(None),
    date: str = Query(None),
    class_name: Optional[str] = Query(None)
):
    """Get attendance records with optional filtering"""
    try:
        # Build filter
        filter_dict = {}
        if student_id:
            filter_dict["student_id"] = student_id
        if date:
            filter_dict["date"] = date

        local_crud = AttendanceCRUD(class_name) if class_name else crud
        records = local_crud.list_attendance(skip, limit, filter_dict)
        return {"records": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")


@router.get("/{attendance_id}")
def get_attendance(
    attendance_id: str,
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Get a specific attendance record by ID or student ID"""
    try:
        local_crud = AttendanceCRUD(class_name) if class_name else crud
        record = local_crud.get_attendance_by_id(attendance_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Attendance record not found for {attendance_id}")
        
        # Convert ObjectId to string for JSON serialization
        if "_id" in record:
            record["_id"] = str(record["_id"])
        
        return record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching record: {str(e)}")


# ==================== UPDATE ====================

@router.put("/{attendance_id}")
def update_attendance(
    attendance_id: str,
    update_data: dict,
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Update attendance status or details"""
    try:
        local_crud = AttendanceCRUD(class_name) if class_name else crud
        record = local_crud.get_attendance_by_id(attendance_id)
        if not record:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        updated = local_crud.update_attendance(attendance_id, update_data)
        if not updated:
            raise HTTPException(status_code=400, detail="Failed to update attendance")

        return {"message": "Attendance updated successfully", "attendance_id": attendance_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating record: {str(e)}")


# ==================== DELETE ====================

@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: str,
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Delete an attendance record"""
    try:
        local_crud = AttendanceCRUD(class_name) if class_name else crud
        record = local_crud.get_attendance_by_id(attendance_id)
        if not record:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        local_crud.delete_attendance(attendance_id)
        return {"message": "Attendance record deleted successfully", "attendance_id": attendance_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting record: {str(e)}")
