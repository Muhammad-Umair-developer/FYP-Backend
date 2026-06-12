"""
Embeddings management endpoints
Retrain, update, and manage student embeddings
"""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Query
from typing import List, Dict
from app.crud.student_crud import StudentCRUD
from app.core.security import get_current_user
from app.core.config import EMBEDDINGS_DIR
from app.services.face_embedder import get_embedding
import cv2
import numpy as np
import os
from datetime import datetime
import shutil

router = APIRouter(prefix="/api/v1/embeddings", tags=["Embeddings"])
student_crud = StudentCRUD()

EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "student_embeddings.npy")


@router.post("/retrain", response_model=dict)
def retrain_embeddings(
    current_user: str = Depends(get_current_user)
):
    """
    Retrain all student embeddings from MongoDB
    Loads embeddings from student collection and saves to .npy file
    """
    try:
        students = student_crud.list_students(limit=10000)
        
        if not students:
            raise HTTPException(status_code=400, detail="No students found in database")
        
        student_ids = []
        embeddings_list = []
        failed = []
        
        for student in students:
            if student.get("embedding"):
                student_ids.append(student["student_id"])
                embeddings_list.append(student["embedding"])
            else:
                failed.append({"student_id": student["student_id"], "reason": "No embedding"})
        
        if not embeddings_list:
            raise HTTPException(status_code=400, detail="No embeddings found in any student")
        
        # Convert to numpy arrays
        embeddings_array = np.array(embeddings_list, dtype=np.float32)
        
        # Save to file with backup
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        
        if os.path.exists(EMBEDDINGS_FILE):
            backup_file = f"{EMBEDDINGS_FILE}.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(EMBEDDINGS_FILE, backup_file)
        
        # Save embeddings
        np.save(EMBEDDINGS_FILE, {
            "student_ids": np.array(student_ids),
            "embeddings": embeddings_array,
            "trained_at": datetime.utcnow().isoformat(),
            "total_students": len(student_ids)
        }, allow_pickle=True)
        
        return {
            "message": "Embeddings retrained successfully",
            "total_trained": len(student_ids),
            "failed": len(failed),
            "failed_details": failed[:10] if failed else []
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}")


@router.post("/update/{student_id}", response_model=dict)
async def update_student_embedding_file(
    student_id: str,
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    """
    Update embedding for a student from new image
    Updates both MongoDB and .npy file
    """
    try:
        # Get student from DB
        student = student_crud.get_student_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Process image
        contents = await file.read()
        img = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        embedding = get_embedding(img_rgb)
        
        if embedding is None:
            raise HTTPException(status_code=400, detail="No face detected in image")
        
        # Update in MongoDB
        student_crud.update_student(student_id, {
            "embedding": embedding.tolist(),
            "embedding_updated_at": datetime.utcnow()
        })
        
        # Update embeddings file
        if os.path.exists(EMBEDDINGS_FILE):
            data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
            
            if student_id in data["student_ids"]:
                idx = list(data["student_ids"]).index(student_id)
                data["embeddings"][idx] = embedding
            else:
                data["student_ids"] = np.append(data["student_ids"], student_id)
                data["embeddings"] = np.vstack([data["embeddings"], embedding])
            
            np.save(EMBEDDINGS_FILE, data, allow_pickle=True)
        
        return {
            "message": "Student embedding updated successfully",
            "student_id": student_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.get("/info", response_model=dict)
def get_embeddings_info(
    current_user: str = Depends(get_current_user)
):
    """Get current embeddings file information"""
    if not os.path.exists(EMBEDDINGS_FILE):
        return {
            "status": "not_created",
            "message": "Embeddings file not found. Run retrain to create.",
            "file_path": EMBEDDINGS_FILE
        }
    
    try:
        data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
        
        file_size = os.path.getsize(EMBEDDINGS_FILE)
        file_size_mb = file_size / (1024 * 1024)
        
        return {
            "status": "ready",
            "file_path": EMBEDDINGS_FILE,
            "file_size_mb": round(file_size_mb, 2),
            "total_students": len(data["student_ids"]),
            "embedding_dimension": len(data["embeddings"][0]) if len(data["embeddings"]) > 0 else 0,
            "trained_at": data.get("trained_at", "unknown"),
            "sample_student_ids": list(data["student_ids"][:5])
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/validate", response_model=dict)
def validate_embeddings(
    current_user: str = Depends(get_current_user)
):
    """Validate embeddings file integrity"""
    try:
        if not os.path.exists(EMBEDDINGS_FILE):
            raise HTTPException(status_code=404, detail="Embeddings file not found")
        
        data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
        
        # Validate structure
        required_keys = ["student_ids", "embeddings"]
        for key in required_keys:
            if key not in data:
                raise HTTPException(status_code=400, detail=f"Missing key: {key}")
        
        # Validate dimensions
        num_students = len(data["student_ids"])
        num_embeddings = len(data["embeddings"])
        
        if num_students != num_embeddings:
            raise HTTPException(
                status_code=400,
                detail=f"Mismatch: {num_students} students vs {num_embeddings} embeddings"
            )
        
        # Check embedding dimension
        if len(data["embeddings"]) > 0:
            embedding_dim = len(data["embeddings"][0])
            if embedding_dim != 512:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid embedding dimension: {embedding_dim} (expected 512)"
                )
        
        return {
            "status": "valid",
            "total_students": num_students,
            "embedding_dimension": 512,
            "message": "Embeddings file is valid"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup", response_model=dict)
def backup_embeddings(
    current_user: str = Depends(get_current_user)
):
    """Create backup of embeddings file"""
    try:
        if not os.path.exists(EMBEDDINGS_FILE):
            raise HTTPException(status_code=404, detail="Embeddings file not found")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{EMBEDDINGS_FILE}.backup_{timestamp}"
        
        shutil.copy2(EMBEDDINGS_FILE, backup_file)
        
        return {
            "message": "Backup created successfully",
            "backup_file": backup_file,
            "timestamp": timestamp
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-backups", response_model=dict)
def list_embeddings_backups(
    current_user: str = Depends(get_current_user)
):
    """List available embeddings backups"""
    try:
        backup_files = []
        
        if os.path.exists(EMBEDDINGS_DIR):
            for file in os.listdir(EMBEDDINGS_DIR):
                if "backup" in file:
                    file_path = os.path.join(EMBEDDINGS_DIR, file)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)
                    modification_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    backup_files.append({
                        "filename": file,
                        "size_mb": round(file_size, 2),
                        "modified": modification_time.isoformat()
                    })
        
        return {
            "total_backups": len(backup_files),
            "backups": sorted(backup_files, key=lambda x: x["modified"], reverse=True)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
