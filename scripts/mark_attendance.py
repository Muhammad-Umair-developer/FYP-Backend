import os
import numpy as np
import cv2
from datetime import datetime
from app.services.face_embedder import get_all_embeddings
from app.services.face_matcher import cosine_similarity
from app.crud.attendance_crud import AttendanceCRUD
from app.crud.student_crud import StudentCRUD
from app.core.config import EMBEDDINGS_DIR

EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "student_embeddings.npy")
data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()

attendance_crud = AttendanceCRUD()
student_crud = StudentCRUD()
THRESHOLD = 0.6

def mark_attendance(image_path):
    """Mark attendance for all faces detected in an image"""
    # Read and convert image to RGB
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image from {image_path}")
        return
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Get all face embeddings
    face_results = get_all_embeddings(img_rgb)
    
    if len(face_results) == 0:
        print("No faces detected in the image")
        return
    
    print(f"\nDetected {len(face_results)} face(s) in the image")
    print("=" * 50)
    
    today_datetime = datetime.combine(datetime.today(), datetime.min.time())
    
    for idx, (emb, bbox) in enumerate(face_results, 1):
        best_score = 0
        best_student_id = None
        
        # Match with database
        for s_id, s_emb in zip(data["student_ids"], data["embeddings"]):
            score = cosine_similarity(emb, s_emb)
            if score > best_score:
                best_score = score
                best_student_id = str(s_id)  # ⚡ ensure string type
        
        print(f"\nFace {idx}:")
        print(f"  Best match: {best_student_id} (confidence: {best_score:.2f})")
        
        if best_score > THRESHOLD:
            # Fetch student_name from students collection
            student_name = None
            if best_student_id:
                student = student_crud.get_student_by_id(best_student_id)
                student_name = student["name"] if student else best_student_id
            
            # Check if already marked today
            already_marked = attendance_crud.check_attendance(best_student_id, today_datetime)
            
            if not already_marked:
                attendance_crud.mark_attendance({
                    "student_id": best_student_id,
                    "name": student_name,
                    "date": today_datetime,
                    "status": "Present"
                })
                print(f"  ✓ Marked attendance for {student_name or best_student_id}")
            else:
                print(f"  ! {student_name or best_student_id} already marked today")
        else:
            print(f"  ✗ Unknown face (confidence too low)")
    
    print("=" * 50)
            
mark_attendance("datasets/raw/classroom_image.jpg")
