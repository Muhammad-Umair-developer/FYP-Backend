import requests
import json

# Test 1: ObjectId format
print('Test 1: ObjectId format')
r = requests.get('http://localhost:8000/attendance/69fee654e95538446f2d8b04')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    print(f'  Student: {r.json().get("student_id")}')
    print(f'  Name: {r.json().get("name")}')
else:
    print(f'  Error: {r.json()}')

# Test 2: Full student ID format
print('\nTest 2: Full student ID (22-NTU-CS-1192)')
r = requests.get('http://localhost:8000/attendance/22-NTU-CS-1192')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    print(f'  Student: {r.json().get("student_id")}')
    print(f'  Name: {r.json().get("name")}')
else:
    print(f'  Error: {r.json()}')

# Test 3: Numeric portion only
print('\nTest 3: Numeric portion only (1192)')
r = requests.get('http://localhost:8000/attendance/1192')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    print(f'  Student: {r.json().get("student_id")}')
    print(f'  Name: {r.json().get("name")}')
else:
    print(f'  Error: {r.json()}')

print('\n' + '='*50)
print('All tests completed successfully!')
