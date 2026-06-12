import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("TESTING FACE RECOGNITION ATTENDANCE API")
print("=" * 60)

# Test 1: Login
print("\n1. Testing POST /auth/login")
print("-" * 60)
login_data = {
    "email": "admin@fyp.com",
    "password": "admin123"
}
response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
token = None
if response.status_code == 200:
    token = response.json().get("access_token")
    print(f"Token: {token[:50]}..." if token else "No token")

# Test 2: Register Student
print("\n2. Testing POST /students/register")
print("-" * 60)
student_data = {
    "student_id": "22-NTU-CS-1192",
    "name": "Test Student",
    "email": "student@test.com"
}
response = requests.post(f"{BASE_URL}/students/register", json=student_data)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 3: List Students
print("\n3. Testing GET /students/list")
print("-" * 60)
response = requests.get(f"{BASE_URL}/students/list")
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 4: Get Single Student
print("\n4. Testing GET /students/{{student_id}}")
print("-" * 60)
response = requests.get(f"{BASE_URL}/students/22-NTU-CS-1192")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2)}")
else:
    print(f"Response: {response.text}")

# Test 5: List Attendance (without token for testing)
print("\n5. Testing GET /attendance/ (List Attendance)")
print("-" * 60)
headers = {"Authorization": f"Bearer {token}"} if token else {}
response = requests.get(f"{BASE_URL}/attendance/", headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 6: Mark Attendance
print("\n6. Testing POST /attendance/mark")
print("-" * 60)
attendance_data = {
    "student_id": "22-NTU-CS-1192",
    "name": "Test Student",
    "status": "Present"
}
headers = {"Authorization": f"Bearer {token}"} if token else {}
response = requests.post(f"{BASE_URL}/attendance/mark", json=attendance_data, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

print("\n" + "=" * 60)
print("API TESTING COMPLETE")
print("=" * 60)
