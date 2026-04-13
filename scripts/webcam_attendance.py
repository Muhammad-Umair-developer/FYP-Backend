import cv2
import numpy as np
import os
from datetime import datetime, date
from app.services.face_embedder import get_all_embeddings
from app.services.face_matcher import cosine_similarity
from app.crud.attendance_crud import AttendanceCRUD
from app.crud.student_crud import StudentCRUD
from app.core.config import EMBEDDINGS_DIR

# Load embeddings
EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "student_embeddings.npy")
if not os.path.exists(EMBEDDINGS_FILE):
    print(f"Error: Embeddings file not found at {EMBEDDINGS_FILE}")
    exit(1)

data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
attendance_crud = AttendanceCRUD()
student_crud = StudentCRUD()

THRESHOLD = 0.6
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam")
    exit(1)

print("Live Webcam Attendance Started. Press 'q' to quit.")

# Keep track of already marked students today (to avoid duplicates)
marked_students_today = set()
today_datetime = datetime.combine(date.today(), datetime.min.time())

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_results = get_all_embeddings(frame_rgb)
    
    face_count = len(face_results)
    display_frame = frame.copy()
    
    for idx, (emb, bbox) in enumerate(face_results, 1):
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        
        best_score = 0
        best_student_id = None
        
        # Match face with embeddings
        for s_id, s_emb in zip(data["student_ids"], data["embeddings"]):
            score = cosine_similarity(emb, s_emb)
            if score > best_score:
                best_score = score
                best_student_id = s_id
        
        # Fetch student name
        student_name = None
        if best_student_id:
            student = student_crud.get_student_by_id(best_student_id)
            student_name = student["name"] if student else best_student_id
        
        if best_score >= THRESHOLD:
            # Check if already marked today (set or DB)
            already_marked = best_student_id in marked_students_today or \
                             attendance_crud.check_attendance(best_student_id, today_datetime)
            
            if not already_marked:
                # Mark attendance with proper datetime
                attendance_crud.mark_attendance({
                    "student_id": best_student_id,
                    "name": student_name,
                    "date": today_datetime,
                    "status": "Present"
                })
                marked_students_today.add(best_student_id)
                print(f"✓ Attendance marked for {student_name or best_student_id}")
                color = (0, 255, 0)  # Green = newly marked
                label = f"{student_name or best_student_id} - Marked"
            else:
                color = (0, 165, 255)  # Orange = already marked
                label = f"{student_name or best_student_id} - Already marked"
                print(f"! Student {student_name or best_student_id} already marked today")
            
            # Draw rectangle + label
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display_frame, label, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        else:
            # Unknown face → red box
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(display_frame, "Unknown", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
    
    # Show total face count
    cv2.putText(display_frame, f"Detected Faces: {face_count}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    
    cv2.imshow("Live Attendance", display_frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Live webcam closed.")
