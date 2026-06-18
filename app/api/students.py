from fastapi import APIRouter, HTTPException, Depends, Query, Form, File, UploadFile
from pydantic import BaseModel, Field
from app.models.student import StudentModel, StudentsListResponse
from app.crud.student_crud import StudentCRUD
from app.core.security import get_current_user
from app.services.face_embedder import get_embedding
from typing import List, Optional
import os
import cv2
import numpy as np
import subprocess
import sys
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
crud = StudentCRUD()


# ==================== CREATE ====================

@router.post("/register")
async def register_student(
    name: str = Form(...),
    reg_number: str = Form(...),
    class_name: str = Form(...),
    image1: UploadFile = File(...),
    image2: UploadFile = File(...),
    image3: UploadFile = File(...),
    image4: UploadFile = File(...),
    image5: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    """
    Register a new student:
    1. Receives 5 distinct UploadFiles.
    2. Saves images to datasets/[class_name]/[reg_number]/image1.jpg ... image5.jpg
    3. Saves metadata record into class-isolated collection students-[class_name].
    """
    class_name = class_name.strip()
    reg_number = reg_number.strip()
    name = name.strip()

    if not class_name or not reg_number or not name:
        raise HTTPException(
            status_code=400,
            detail="Name, registration number, and class name cannot be empty."
        )

    # 4. Physical Storage: datasets/[class_name]/[reg_number]/
    target_dir = os.path.join("datasets", class_name, reg_number)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create directory structure: {str(e)}"
        )

    images = [image1, image2, image3, image4, image5]
    image_paths = []
    saved_files = []
    embeddings_to_save = []

    try:
        for idx, file in enumerate(images):
            file_name = f"image{idx + 1}.jpg"
            file_path = os.path.join(target_dir, file_name)
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_path)
            # Use forward slashes for database consistency
            image_paths.append(f"datasets/{class_name}/{reg_number}/{file_name}")

            # Extract face embedding for this image
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                emb = get_embedding(img_rgb)
                if emb is not None:
                    if hasattr(emb, "tolist"):
                        emb = emb.tolist()
                    embeddings_to_save.append(emb)
    except Exception as e:
        # Cleanup partially written files on error
        for path in saved_files:
            try:
                os.remove(path)
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save student images: {str(e)}"
        )

    if not embeddings_to_save:
        # Clean up files since registration failed
        for path in saved_files:
            try:
                os.remove(path)
            except Exception:
                pass
        raise HTTPException(
            status_code=400,
            detail="No faces could be detected in any of the 5 uploaded images. Registration aborted."
        )

    # 5. Database Isolation: save metadata record in collection named 'students-[class_name]'
    collection_name = f"students-{class_name}"
    class_crud = StudentCRUD(collection_name)
    
    # Check if student already exists in this class
    if class_crud.get_student_by_id(reg_number):
        # Clean up files since registration failed
        for path in saved_files:
            try:
                os.remove(path)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail="Student already exists in this class")

    from datetime import datetime
    student_dict = {
        "student_id": reg_number,
        "name": name,
        "reg_number": reg_number,
        "image_paths": image_paths,
        "embedding": embeddings_to_save[0],
        "embeddings": embeddings_to_save,
        "created_at": datetime.utcnow()
    }
    
    try:
        class_crud.collection.insert_one(student_dict)
    except Exception as e:
        # Cleanup files on database insertion error
        for path in saved_files:
            try:
                os.remove(path)
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save student metadata to database: {str(e)}"
        )

    # Update student_embeddings.npy dynamically
    from app.core.config import EMBEDDINGS_DIR
    try:
        EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "student_embeddings.npy")
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        
        if os.path.exists(EMBEDDINGS_FILE):
            data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
            student_ids_list = list(data.get("student_ids", []))
            embeddings_list = list(data.get("embeddings", []))
            
            # Remove any existing entries for this student to prevent duplicates
            indices_to_keep = [i for i, s_id in enumerate(student_ids_list) if s_id != reg_number]
            student_ids_list = [student_ids_list[i] for i in indices_to_keep]
            embeddings_list = [embeddings_list[i] for i in indices_to_keep]
            
            # Append all new embeddings
            for emb in embeddings_to_save:
                student_ids_list.append(reg_number)
                embeddings_list.append(np.array(emb, dtype=np.float32))
            
            data["student_ids"] = np.array(student_ids_list)
            data["embeddings"] = np.array(embeddings_list, dtype=np.float32)
        else:
            student_ids_list = [reg_number] * len(embeddings_to_save)
            data = {
                "student_ids": np.array(student_ids_list),
                "embeddings": np.array(embeddings_to_save, dtype=np.float32)
            }
        np.save(EMBEDDINGS_FILE, data, allow_pickle=True)
    except Exception as e:
        logger.error(f"Failed to update student_embeddings.npy: {str(e)}")

    return {
        "message": "Student registered successfully",
        "student_id": reg_number,
        "name": name,
        "class_name": class_name,
        "collection_name": collection_name,
        "image_paths": image_paths
    }


# ==================== READ ====================

@router.get("/list", response_model=StudentsListResponse)
def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=200),
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Get all students with pagination"""
    class_crud = StudentCRUD(f"students-{class_name}") if class_name else crud
    students = class_crud.list_students(skip, limit)
    return {"students": students, "count": len(students)}


@router.get("/search/by-name")
def search_students_by_name(
    query: str = Query(..., min_length=1),
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Search students by name"""
    class_crud = StudentCRUD(f"students-{class_name}") if class_name else crud
    results = class_crud.search_by_name(query)
    if not results:
        raise HTTPException(status_code=404, detail="No students found")
    return {"results": results, "count": len(results)}


@router.get("/{student_id}")
def get_student(
    student_id: str,
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Get a specific student by ID"""
    class_crud = StudentCRUD(f"students-{class_name}") if class_name else crud
    student = class_crud.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


class StudentUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None)
    registration_number: Optional[str] = Field(default=None)

# ==================== UPDATE ====================

@router.patch("/{student_id}")
def update_student(
    student_id: str,
    payload: StudentUpdateRequest,
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Manually update student profile fields in MongoDB"""
    class_crud = StudentCRUD(f"students-{class_name}") if class_name else crud
    student = class_crud.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Clean the incoming payload by explicitly filtering out "string" and None values
    payload_dict = {k: v for k, v in payload.dict(exclude_unset=True).items() if v != "string" and v is not None}
    
    update_data = {}
    if "name" in payload_dict:
        update_data["name"] = payload_dict["name"]
    if "registration_number" in payload_dict:
        update_data["reg_number"] = payload_dict["registration_number"]
        update_data["student_id"] = payload_dict["registration_number"]
        
    if not update_data:
        return {"message": "No update fields provided", "student_id": student_id}
        
    # Resolve the correct collection where the student is located
    target_collection = class_crud.collection
    if not class_name and class_crud.collection.name == "students":
        from app.core.database import db
        for col_name in db.list_collection_names():
            if col_name.startswith("students-"):
                if db[col_name].find_one({"student_id": student_id}):
                    target_collection = db[col_name]
                    break
                    
    # Update MongoDB using {"$set": update_data} via update_one so unprovided fields remain completely untouched
    result = target_collection.update_one(
        {"student_id": student_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update student")
        
    return {"message": "Student updated successfully", "student_id": student_id, "updated_fields": update_data}


# ==================== DELETE ====================

@router.delete("/{student_id}")
def delete_student(
    student_id: str,
    class_name: Optional[str] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """Manually delete a student and completely remove their metadata and files from the system"""
    class_crud = StudentCRUD(f"students-{class_name}") if class_name else crud
    student = class_crud.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Clean up associated files/directories from disk
    import shutil
    image_paths = student.get("image_paths", [])
    deleted_dirs = set()
    for img_path in image_paths:
        dir_path = os.path.dirname(img_path)
        if dir_path and dir_path not in deleted_dirs:
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    deleted_dirs.add(dir_path)
                except Exception:
                    pass
                    
    # Clean up raw datasets directory if it exists
    raw_folder = os.path.join("datasets", "raw", student_id)
    if os.path.exists(raw_folder):
        try:
            shutil.rmtree(raw_folder)
        except Exception:
            pass
            
    # Delete metadata from MongoDB
    class_crud.delete_student(student_id)
    return {"message": "Student completely deleted from system", "student_id": student_id}


# ==================== ENROLL (AUTOMATED ONBOARDING) ====================

@router.post("/enroll")
async def enroll_student(
    name: str = Form(...),
    roll_number: str = Form(...),
    image1: UploadFile = File(...),
    image2: UploadFile = File(...),
    image3: UploadFile = File(...),
    image4: UploadFile = File(...),
    image5: UploadFile = File(...),
    class_name: Optional[str] = Form(None),
    current_user: str = Depends(get_current_user)
):
    """
    Onboard a new student:
    1. Saves 5 raw images to datasets/raw/{roll_number}
    2. Extract a face embedding from the uploaded images for the MongoDB student profile
    3. Programmatically runs ml.train_embeddings to update student_embeddings.npy
    4. Registers student metadata and embedding in MongoDB
    """
    images = [image1, image2, image3, image4, image5]
    
    class_crud = StudentCRUD(f"students-{class_name}") if class_name else crud
        
    # Check if student already exists in DB
    if class_crud.get_student_by_id(roll_number):
        raise HTTPException(status_code=400, detail=f"Student with roll number {roll_number} already exists")

    # Create destination directory
    raw_student_dir = os.path.join("datasets", "raw", roll_number)
    os.makedirs(raw_student_dir, exist_ok=True)

    embedding = None
    saved_files = []

    try:
        # 2. Process and save images, extracting embedding from first valid face
        for idx, file in enumerate(images):
            content = await file.read()
            
            # Save file
            file_extension = os.path.splitext(file.filename)[1] or ".jpg"
            file_name = f"image_{idx + 1}{file_extension}"
            file_path = os.path.join(raw_student_dir, file_name)
            
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_path)

            # Try to extract face embedding (if not already found)
            if embedding is None:
                nparr = np.frombuffer(content, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    emb = get_embedding(img_rgb)
                    if emb is not None:
                        embedding = emb

        # Reject onboarding if no face was found in any of the 5 images
        if embedding is None:
            raise HTTPException(
                status_code=400, 
                detail="No face could be detected in any of the 5 uploaded images. Enrollment aborted."
            )

        # 3. Programmatically trigger ml.train_embeddings
        try:
            # Using sys.executable guarantees it runs using the current virtual env's python interpreter
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            subprocess.run(
                [sys.executable, "-m", "ml.train_embeddings"],
                check=True,
                capture_output=True,
                text=True,
                env=env
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run train_embeddings: {e.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update embeddings cache file: {e.stderr}"
            )

        # 4. Save student record to MongoDB
        student_model = StudentModel(
            student_id=roll_number,
            name=name,
            embedding=embedding
        )
        class_crud.create_student(student_model)

        return {
            "message": "Student enrolled and trained successfully",
            "student_id": roll_number,
            "name": name,
            "images_saved": len(saved_files)
        }

    except Exception as e:
        # Cleanup files on general failure to prevent orphaned partial folders
        if os.path.exists(raw_student_dir):
            for file in os.listdir(raw_student_dir):
                try:
                    os.remove(os.path.join(raw_student_dir, file))
                except Exception:
                    pass
            try:
                os.rmdir(raw_student_dir)
            except Exception:
                pass
        raise e
