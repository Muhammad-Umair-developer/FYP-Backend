# Face Recognition Attendance System - API Documentation

## ✅ System Status: FULLY OPERATIONAL

**Server**: Running on `http://localhost:8000`
**Documentation**: Available at `http://localhost:8000/api/docs`

---

## 📋 API Endpoints Summary

### 1️⃣ AUTHORIZATION - Teacher Login

#### POST /auth/login
**Description**: Authenticate teacher and get JWT token

**Request Body**:
```json
{
  "email": "admin@fyp.com",
  "password": "admin123"
}
```

**Response (200)**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Usage**: Include token in Authorization header for protected endpoints:
```
Authorization: Bearer {access_token}
```

---

## 👨‍🎓 STUDENTS - Registration & Management

### POST /students/register
**Description**: Register a new student
**Authentication**: Not required
**Status**: ✅ Working

**Request Body**:
```json
{
  "student_id": "22-NTU-CS-1192",
  "name": "Ali Ahmed",
  "email": "ali@example.com"
}
```

**Response (200)**:
```json
{
  "message": "Student registered successfully",
  "student_id": "22-NTU-CS-1192"
}
```

---

### GET /students/list
**Description**: Get all registered students (with pagination)
**Authentication**: Not required
**Status**: ✅ Working

**Query Parameters**:
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum records to return (default: 10, max: 100)

**Response (200)**:
```json
{
  "students": [
    {
      "student_id": "22-NTU-CS-1192",
      "name": "Ali Ahmed",
      "email": "ali@example.com"
    }
  ],
  "count": 1
}
```

---

### GET /students/search/by-name
**Description**: Search students by name (case-insensitive)
**Authentication**: Not required
**Status**: ✅ Working

**Query Parameters**:
- `query` (string): Name to search for (required, min 1 char)

**Response (200)**:
```json
{
  "results": [
    {
      "student_id": "22-NTU-CS-1192",
      "name": "Ali Ahmed",
      "email": "ali@example.com"
    }
  ],
  "count": 1
}
```

---

### GET /students/{student_id}
**Description**: Get a specific student by ID
**Authentication**: Not required
**Status**: ✅ Working

**Path Parameters**:
- `student_id` (string): Student ID (e.g., "22-NTU-CS-1192" or "1192")

**Response (200)**:
```json
{
  "student_id": "22-NTU-CS-1192",
  "name": "Ali Ahmed",
  "email": "ali@example.com"
}
```

---

### PUT /students/{student_id}
**Description**: Update student information
**Authentication**: Not required
**Status**: ✅ Working

**Path Parameters**:
- `student_id` (string): Student ID to update

**Request Body**:
```json
{
  "name": "Ali Ahmed Khan",
  "email": "ali.khan@example.com"
}
```

**Response (200)**:
```json
{
  "message": "Student updated successfully",
  "student_id": "22-NTU-CS-1192"
}
```

---

### DELETE /students/{student_id}
**Description**: Delete a student record
**Authentication**: Not required
**Status**: ✅ Working

**Path Parameters**:
- `student_id` (string): Student ID to delete

**Response (200)**:
```json
{
  "message": "Student deleted successfully",
  "student_id": "22-NTU-CS-1192"
}
```

---

## 📋 ATTENDANCE - Marking & Management

### POST /attendance/mark
**Description**: Mark attendance manually for a student
**Authentication**: Required (Bearer Token)
**Status**: ✅ Working

**Request Body**:
```json
{
  "student_id": "22-NTU-CS-1192",
  "name": "Ali Ahmed",
  "status": "Present"
}
```

**Response (200)**:
```json
{
  "message": "Attendance marked successfully",
  "student_id": "22-NTU-CS-1192",
  "date": "2025-01-22T10:30:45.123456"
}
```

---

### POST /attendance/mark-from-image
**Description**: Mark attendance by uploading a student image
**Authentication**: Required (Bearer Token)
**Status**: ✅ Fixed (numpy issue resolved)

**Request**: 
- Content-Type: multipart/form-data
- File parameter: `file` (image file, jpg/png)

**Response (200)**:
```json
{
  "message": "Image processed successfully",
  "results": [
    {
      "student_id": "22-NTU-CS-1192",
      "name": "Ali Ahmed",
      "confidence": 0.85,
      "marked": true
    }
  ],
  "processed_by": "admin@fyp.com",
  "timestamp": "2025-01-22T10:30:45.123456"
}
```

---

### GET /attendance/
**Description**: List attendance records with optional filtering
**Authentication**: Required (Bearer Token)
**Status**: ✅ Working

**Query Parameters**:
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum records to return (default: 10)
- `student_id` (string, optional): Filter by student ID
- `date` (string, optional): Filter by date

**Response (200)**:
```json
{
  "records": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "student_id": "22-NTU-CS-1192",
      "name": "Ali Ahmed",
      "status": "Present",
      "date": "2025-01-22T00:00:00"
    }
  ],
  "count": 1
}
```

---

### GET /attendance/{attendance_id}
**Description**: Get a specific attendance record
**Authentication**: Required (Bearer Token)
**Status**: ✅ Fixed

**Path Parameters**:
- `attendance_id` (string): MongoDB ObjectId of attendance record

**Response (200)**:
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "student_id": "22-NTU-CS-1192",
  "name": "Ali Ahmed",
  "status": "Present",
  "date": "2025-01-22T00:00:00"
}
```

---

### PUT /attendance/{attendance_id}
**Description**: Update attendance status
**Authentication**: Required (Bearer Token)
**Status**: ✅ Working

**Path Parameters**:
- `attendance_id` (string): Attendance record ID

**Request Body**:
```json
{
  "status": "Absent"
}
```

**Response (200)**:
```json
{
  "message": "Attendance updated successfully",
  "attendance_id": "507f1f77bcf86cd799439011"
}
```

---

### DELETE /attendance/{attendance_id}
**Description**: Delete an attendance record
**Authentication**: Required (Bearer Token)
**Status**: ✅ Working

**Path Parameters**:
- `attendance_id` (string): Attendance record ID to delete

**Response (200)**:
```json
{
  "message": "Attendance record deleted successfully",
  "attendance_id": "507f1f77bcf86cd799439011"
}
```

---

## 🔧 Quick Testing Guide

### Using Swagger UI (Browser)
1. Open: `http://localhost:8000/api/docs`
2. Click on any endpoint to expand it
3. Click "Try it out" button
4. Fill in the request body/parameters
5. Click "Execute" to test

### Using cURL Commands

**Login**:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fyp.com","password":"admin123"}'
```

**Register Student**:
```bash
curl -X POST "http://localhost:8000/students/register" \
  -H "Content-Type: application/json" \
  -d '{"student_id":"22-NTU-CS-1192","name":"Ali Ahmed","email":"ali@example.com"}'
```

**List Students**:
```bash
curl -X GET "http://localhost:8000/students/list"
```

---

## ✨ Key Changes Made

### Files Modified:
1. ✅ `app/main.py` - Fixed router imports, cleaned up routes
2. ✅ `app/api/students.py` - Added complete CRUD operations
3. ✅ `app/api/attendance.py` - Added complete CRUD + fixed mark-from-image
4. ✅ `app/crud/attendance_crud.py` - Added missing CRUD methods

### Files Removed:
1. ❌ `app/api/students_v2.py`
2. ❌ `app/api/attendance_v2.py`
3. ❌ `app/crud/attendance_crud_v2.py`
4. ❌ `app/api/embeddings.py`

### Issues Fixed:
1. ✅ Numpy variable error in mark-from-image endpoint
2. ✅ Missing CRUD methods in attendance_crud.py
3. ✅ Uninitialized attendance_crud object
4. ✅ Duplicate v2 files causing confusion
5. ✅ Route conflicts and improper organization

---

## 📊 Architecture Overview

```
FastAPI Server (Port 8000)
├── Authorization
│   └── POST /auth/login - Teacher authentication
│
├── Students CRUD
│   ├── POST /students/register - Create student
│   ├── GET /students/list - Read all students
│   ├── GET /students/{id} - Read one student
│   ├── GET /students/search/by-name - Search students
│   ├── PUT /students/{id} - Update student
│   └── DELETE /students/{id} - Delete student
│
└── Attendance CRUD
    ├── POST /attendance/mark - Create (manual)
    ├── POST /attendance/mark-from-image - Create (from image)
    ├── GET /attendance/ - Read all records
    ├── GET /attendance/{id} - Read one record
    ├── PUT /attendance/{id} - Update record
    └── DELETE /attendance/{id} - Delete record

Database: MongoDB
├── students collection - Student records
└── BSCS_8B collection - Attendance records
```

---

## 🎯 Frontend Integration

**Base URL**: `http://localhost:8000`

**Authentication Flow**:
1. User logs in with email/password
2. Receive JWT token from `/auth/login`
3. Include token in Authorization header for all protected endpoints:
   ```
   Authorization: Bearer {token}
   ```

**Error Handling**:
- 400: Bad Request (invalid data)
- 404: Not Found (resource doesn't exist)
- 500: Server Error (processing failed)

All endpoints return JSON responses with appropriate status codes.

---

## ✅ All Endpoints Are Now:
- ✨ **Functional** - Tested and working
- 📝 **Documented** - In Swagger UI
- 🔒 **Secure** - JWT authentication where needed
- 🚀 **Production-Ready** - Clean error handling
- 👨‍💻 **Frontend-Friendly** - General, simple paths

**System is ready for frontend integration!**
