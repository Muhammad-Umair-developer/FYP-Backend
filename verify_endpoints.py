#!/usr/bin/env python
"""
Quick verification script to test all endpoints
Run: python verify_endpoints.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = None

def test_health():
    """Test health endpoint"""
    print("\n✓ Testing: GET /health")
    r = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    return r.status_code == 200

def test_root():
    """Test root endpoint"""
    print("\n✓ Testing: GET /")
    r = requests.get(f"{BASE_URL}/")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    return r.status_code == 200

def test_login():
    """Test login"""
    print("\n✓ Testing: POST /api/v1/auth/login")
    payload = {"email": "admin@fyp.com", "password": "admin123"}
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json=payload)
    print(f"  Status: {r.status_code}")
    resp = r.json()
    print(f"  Response: {resp}")
    
    global TOKEN
    if r.status_code == 200 and "access_token" in resp:
        TOKEN = resp["access_token"]
        print(f"  ✓ Token acquired: {TOKEN[:50]}...")
    
    return r.status_code == 200

def test_student_list():
    """Test list students"""
    if not TOKEN:
        print("\n✗ Skipping: GET /api/v1/students (no token)")
        return False
    
    print("\n✓ Testing: GET /api/v1/students")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.get(f"{BASE_URL}/api/v1/students", headers=headers)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    return r.status_code == 200

def test_student_count():
    """Test student count"""
    if not TOKEN:
        print("\n✗ Skipping: GET /api/v1/students/stats/count (no token)")
        return False
    
    print("\n✓ Testing: GET /api/v1/students/stats/count")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.get(f"{BASE_URL}/api/v1/students/stats/count", headers=headers)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    return r.status_code == 200

def test_api_info():
    """Test API info"""
    print("\n✓ Testing: GET /api/info")
    r = requests.get(f"{BASE_URL}/api/info")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    return r.status_code == 200

def main():
    print("=" * 60)
    print("API ENDPOINT VERIFICATION")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Health Check", test_health()))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(("Health Check", False))
    
    try:
        results.append(("Root Endpoint", test_root()))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(("Root Endpoint", False))
    
    try:
        results.append(("API Info", test_api_info()))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(("API Info", False))
    
    try:
        results.append(("Login", test_login()))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(("Login", False))
    
    try:
        results.append(("List Students", test_student_list()))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(("List Students", False))
    
    try:
        results.append(("Student Count", test_student_count()))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(("Student Count", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✓ All endpoints working!")
    else:
        print("\n✗ Some endpoints failed. Check logs above.")

if __name__ == "__main__":
    main()
