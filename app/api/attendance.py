from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from app.models.attendance import AttendanceModel
from app.crud.attendance_crud import AttendanceCRUD
from datetime import datetime
import cv2
import numpy as np
import os

from app.core.security import get_current_user
from app.services.face_matcher import cosine_similarity
from app.core.config import EMBEDDINGS_DIR

router = APIRouter()
crud = AttendanceCRUD()


@router.post("/mark")
def mark_attendance(
    attendance: AttendanceModel,
    current_user: str = Depends(get_current_user)
):
    today = datetime.utcnow()

    if crud.check_attendance(attendance.student_id, today):
        raise HTTPException(status_code=400, detail="Attendance already marked")

    attendance.date = today
    crud.mark_attendance(attendance)

    return {"message": "Attendance marked successfully"}


@router.post("/mark-from-image")
async def mark_attendance_from_image(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "student_embeddings.npy")

    if not os.path.exists(EMBEDDINGS_FILE):
        raise HTTPException(status_code=500, detail="Embeddings not found")

    contents = await file.read()
    img = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
    from app.services.attendance_logic import process_multiple_faces

    results = process_multiple_faces(img_rgb, dict(zip(data["student_ids"], data["embeddings"])))

    return {
        "marked_by": current_user,
        "results": results
    }
