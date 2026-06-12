# Face Recognition Attendance System - Production Backend v2.0

## 📋 Quick Setup Guide

### Prerequisites
- Python 3.8+
- MongoDB running locally or remote
- Virtual environment (venv313 - 3.13)

### Installation

1. **Activate Virtual Environment**
```bash
& f:\FYP-120\myvenv313\Scripts\Activate.ps1
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment Variables**
Create `.env` file in project root:
```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=attendance_db
EMBEDDINGS_DIR=datasets/embeddings
RECOGNITION_THRESHOLD=0.6
ATTENDANCE_COLLECTION=BSCS_8B
STUDENT_COLLECTION=students
SECRET_KEY=your-secret-key-here-change-in-production
```

4. **Start MongoDB**
```bash
mongod
```

5. **Train/Retrain Embeddings (One-time or periodic)**
```bash
python ml/train_embeddings.py
```

6. **Start Server**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. **Access API**
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- API Root: http://localhost:8000/

---

## 🎯 API v2.0 Endpoints Overview

### Base URL
```
/api/v1
```

### Authentication
```
POST /api/v1/auth/login
  Body: {"email": "admin@fyp.com", "password": "admin123"}
  Returns: {"access_token": "..."}
```

Use token in header: `Authorization: Bearer <token>`

---

## 👥 Students Management

### Create Student (with embedding)
```bash
POST /api/v1/students/with-image
  Query: student_id, name
  File: image (face photo)
```

### Get All Students (with pagination)
```bash
GET /api/v1/students?skip=0&limit=50
```

### Get Student Details
```bash
GET /api/v1/students/{student_id}
```

### Search Students by Name
```bash
GET /api/v1/students/search/by-name?query=bilal
```

### Update Student
```bash
PUT /api/v1/students/{student_id}
  Body: {"name": "New Name"}
```

### Update Student Embedding
```bash
POST /api/v1/students/{student_id}/update-embedding
  File: new_face_image
```

### Delete Student
```bash
DELETE /api/v1/students/{student_id}
```

### Batch Operations
```bash
POST /api/v1/students/batch/create
  Body: [{"student_id": "1", "name": "Student1"}, ...]

POST /api/v1/students/batch/update
  Body: [{"student_id": "1", "name": "Updated"}, ...]

POST /api/v1/students/batch/delete
  Body: ["student_id1", "student_id2", ...]
```

---

## 📝 Attendance Management

### Mark Attendance (Manually)
```bash
POST /api/v1/attendance/mark
  Body: {
    "student_id": "22-NTU-CS-1192",
    "name": "bilal rafique",
    "date": "2026-04-13T00:00:00",
    "status": "Present"
  }
```

### Mark Attendance from Image
```bash
POST /api/v1/attendance/mark-from-image?class_name=BSCS_8B
  File: image_with_students
```

### Get Live Camera Session (WebSocket)
```bash
POST /api/v1/attendance/mark-from-camera?class_name=BSCS_8B
Returns:
{
  "session_id": "xxx-yyy-zzz",
  "websocket_url": "/ws/camera/xxx-yyy-zzz"
}

Connect to WebSocket and send:
{
  "type": "frame",
  "data": "base64_encoded_image"
}

Server responds:
{
  "type": "match_result",
  "faces_detected": 2,
  "newly_marked": 1,
  "matches": [...]
}
```

### Get Student Attendance History
```bash
GET /api/v1/attendance/student/{student_id}?limit=100
```

### Daily Attendance Report
```bash
GET /api/v1/attendance/report/daily?date=2026-04-13&class_name=BSCS_8B
```

### Attendance Date Range Report
```bash
GET /api/v1/attendance/report/range?start_date=2026-04-01&end_date=2026-04-30
```

### Student Summary (Overall attendance)
```bash
GET /api/v1/attendance/report/student-summary?start_date=2026-04-01&end_date=2026-04-30
```

### Update Attendance Status
```bash
PUT /api/v1/attendance/{attendance_id}?status=Present
```

### Delete Attendance Record
```bash
DELETE /api/v1/attendance/{attendance_id}
```

### Delete All Student Attendance
```bash
DELETE /api/v1/attendance/student/{student_id}/all
```

### Batch Mark Attendance
```bash
POST /api/v1/attendance/batch/mark
  Body: [
    {"student_id": "1", "name": "Name1", "status": "Present"},
    {"student_id": "2", "name": "Name2", "status": "Absent"}
  ]
```

### Batch Delete Attendance
```bash
POST /api/v1/attendance/batch/delete
  Body: ["attendance_id1", "attendance_id2", ...]
```

### Statistics
```bash
GET /api/v1/attendance/stats/today
GET /api/v1/attendance/stats/period?start_date=2026-04-01&end_date=2026-04-30
```

---

## 📊 Embeddings Management

### Retrain Embeddings (from MongoDB to .npy)
```bash
POST /api/v1/embeddings/retrain
```

### Get Embeddings Info
```bash
GET /api/v1/embeddings/info
```

### Validate Embeddings File
```bash
POST /api/v1/embeddings/validate
```

### Backup Embeddings
```bash
POST /api/v1/embeddings/backup
```

### List Backups
```bash
GET /api/v1/embeddings/list-backups
```

---

## 🗄️ Database Schema

### Students Collection
```json
{
  "_id": ObjectId,
  "student_id": "22-NTU-CS-1192",
  "name": "bilal rafique",
  "embedding": [0.123, 0.456, ...],  // 512-dimensional float array
  "created_at": ISODate,
  "embedding_updated_at": ISODate
}
```

### Attendance Collection (BSCS_8B)
```json
{
  "_id": ObjectId,
  "student_id": "22-NTU-CS-1192",
  "name": "bilal rafique",
  "date": ISODate,
  "status": "Present",  // Present, Absent, Leave, Late
  "confidence": 0.95,  // Face match confidence
  "class": "BSCS_8B",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

---

## 🔧 Standalone Scripts

### Training Embeddings
```bash
python ml/train_embeddings.py
```
- Reads images from `datasets/raw/{student_id}/*.jpg`
- Generates embeddings
- Saves to `datasets/embeddings/student_embeddings.npy`
- Also stores in MongoDB

### Evaluating Model
```bash
python ml/evaluate_model.py
```
- Validates embedding quality
- Calculates recognition accuracy

### Mark Attendance from Image (Batch)
```bash
python scripts/mark_attendance.py path/to/image.jpg
```

### Real-time Webcam Attendance
```bash
python scripts/webcam_attendance.py
```
- Live camera feed
- Real-time face detection
- Prevents duplicate marking
- Green box = newly marked
- Orange box = already marked
- Red box = unknown face

---

## 🚀 Frontend Integration Examples

### JavaScript - Fetch API

#### Login
```javascript
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'admin@fyp.com', password: 'admin123'})
});
const {access_token} = await response.json();
```

#### Get All Students
```javascript
const response = await fetch('http://localhost:8000/api/v1/students?limit=50', {
  headers: {Authorization: `Bearer ${token}`}
});
const {students} = await response.json();
```

#### Mark Attendance from Image
```javascript
const formData = new FormData();
formData.append('file', imageFile);
formData.append('class_name', 'BSCS_8B');

const response = await fetch('http://localhost:8000/api/v1/attendance/mark-from-image', {
  method: 'POST',
  headers: {Authorization: `Bearer ${token}`},
  body: formData
});
const result = await response.json();
console.log(`Marked: ${result.marked}, Unknown: ${result.unknown_faces}`);
```

#### Live Camera (WebSocket)
```javascript
const sessionResponse = await fetch('http://localhost:8000/api/v1/attendance/mark-from-camera', {
  method: 'POST',
  headers: {Authorization: `Bearer ${token}`}
});
const {session_id, websocket_url} = await sessionResponse.json();

const ws = new WebSocket(`ws://localhost:8000${websocket_url}`);

ws.onopen = () => {
  // Capture camera frame and send as base64
  const canvas = document.querySelector('canvas');
  const imageData = canvas.toDataURL('image/jpeg').split(',')[1];
  
  ws.send(JSON.stringify({
    type: 'frame',
    data: imageData
  }));
};

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  console.log(`Matches: ${result.matches.length}, Marked: ${result.newly_marked}`);
};

ws.send(JSON.stringify({type: 'end'})); // Close when done
```

---

## ⚙️ Production Checklist

- [ ] Change `SECRET_KEY` in config
- [ ] Restrict CORS origins in main.py
- [ ] Enable authentication (uncomment `@Depends(get_current_user)`)
- [ ] Set up MongoDB authentication
- [ ] Configure logging for production
- [ ] Set `allow_origins` to actual domain
- [ ] Use proper password hashing for admin credentials
- [ ] Enable rate limiting
- [ ] Set up HTTPS/SSL
- [ ] Database backups scheduled
- [ ] Monitor embeddings file size
- [ ] Log all attendance changes

---

## 🐛 Troubleshooting

**Issue: `Embeddings not found`**
- Run: `python ml/train_embeddings.py`

**Issue: `Student not found`**
- Check MongoDB connection
- Verify student registered with correct ID

**Issue: `Face not detected`**
- Ensure image quality is good
- Face should be clearly visible

**Issue: WebSocket connection fails**
- Check WebSocket URL is correct
- Ensure firewall allows WebSocket connections

---

## 📚 API Documentation

Full interactive documentation available at:
- Swagger: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

---

## 📞 Support

For issues or questions, check:
1. MongoDB connection
2. Embeddings file existence
3. Student registration status
4. API authentication token validity

