from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, Query
from app.models.attendance import AttendanceModel
from app.crud.attendance_crud import AttendanceCRUD
from datetime import datetime
import cv2
import numpy as np
import os

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
    current_user: str = Depends(get_current_user)
):
    """Mark attendance for a student manually"""
    today = datetime.utcnow()

    if crud.check_attendance(attendance.student_id, today):
        raise HTTPException(status_code=400, detail="Attendance already marked today")

    attendance.date = today
    attendance.status = attendance.status or "Present"
    crud.mark_attendance(attendance)

    return {"message": "Attendance marked successfully", "student_id": attendance.student_id, "date": str(today)}


@router.post("/mark-from-image")
async def mark_attendance_from_image(
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

        # Load embeddings
        embeddings_data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
        student_embeddings = dict(zip(embeddings_data["student_ids"], embeddings_data["embeddings"]))

        # Process faces and mark attendance
        results = process_multiple_faces(img_rgb, student_embeddings)

        return {
            "message": "Image processed successfully",
            "results": results,
            "processed_by": current_user,
            "timestamp": str(datetime.utcnow())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


# ==================== READ ====================

@router.get("/")
def list_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    student_id: str = Query(None),
    date: str = Query(None)
):
    """Get attendance records with optional filtering"""
    try:
        # Build filter
        filter_dict = {}
        if student_id:
            filter_dict["student_id"] = student_id
        if date:
            filter_dict["date"] = date

        records = crud.list_attendance(skip, limit, filter_dict)
        return {"records": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")


@router.get("/{attendance_id}")
def get_attendance(
    attendance_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get a specific attendance record by ID or student ID"""
    try:
        record = crud.get_attendance_by_id(attendance_id)
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
    current_user: str = Depends(get_current_user)
):
    """Update attendance status or details"""
    try:
        record = crud.get_attendance_by_id(attendance_id)
        if not record:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        updated = crud.update_attendance(attendance_id, update_data)
        if not updated:
            raise HTTPException(status_code=400, detail="Failed to update attendance")

        return {"message": "Attendance updated successfully", "attendance_id": attendance_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating record: {str(e)}")


# ==================== DELETE ====================

@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete an attendance record"""
    try:
        record = crud.get_attendance_by_id(attendance_id)
        if not record:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        crud.delete_attendance(attendance_id)
        return {"message": "Attendance record deleted successfully", "attendance_id": attendance_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting record: {str(e)}")
