from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import os

router = APIRouter()

@router.post("/register")
async def register_student_images(
    name: str = Form(..., description="Name of the student"),
    reg_number: str = Form(..., description="Registration number of the student"),
    class_name: str = Form(..., description="Class name of the student"),
    images: List[UploadFile] = File(..., description="Exactly 5 student face images")
):
    """
    Register a new student and save exactly 5 uploaded images on disk.
    Directory structure: datasets/[class_name]/[reg_number]/image1.jpg ... image5.jpg
    """
    # Validate that exactly 5 images are uploaded
    if len(images) != 5:
        raise HTTPException(
            status_code=400,
            detail=f"Exactly 5 images must be uploaded. Received {len(images)}."
        )
        
    class_name = class_name.strip()
    reg_number = reg_number.strip()
    
    if not class_name or not reg_number:
        raise HTTPException(
            status_code=400,
            detail="Class name and registration number cannot be empty."
        )
        
    # Build target directory path: datasets/[class_name]/[reg_number]/
    target_dir = os.path.join("datasets", class_name, reg_number)
    
    # Create directory dynamically at runtime if it doesn't exist
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create target directory: {str(e)}"
        )
        
    saved_files = []
    
    # Save the 5 images as image1.jpg, image2.jpg, ... image5.jpg
    try:
        for idx, file in enumerate(images):
            file_name = f"image{idx + 1}.jpg"
            file_path = os.path.join(target_dir, file_name)
            
            # Read file content and write to disk
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_name)
            
    except Exception as e:
        # Cleanup any partially written files in case of error
        for file_name in saved_files:
            try:
                os.remove(os.path.join(target_dir, file_name))
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded files: {str(e)}"
        )
        
    return {
        "message": "Student images registered and saved successfully",
        "name": name,
        "reg_number": reg_number,
        "class_name": class_name,
        "saved_directory": target_dir,
        "files_saved": saved_files
    }
