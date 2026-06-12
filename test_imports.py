#!/usr/bin/env python
"""Test script to check if all imports work correctly"""
import sys
import traceback

print("=" * 60)
print("IMPORT TEST FOR FACE RECOGNITION SYSTEM")
print("=" * 60)

tests = []

def test_import(module_name):
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
        tests.append((module_name, True))
        return True
    except Exception as e:
        print(f"✗ {module_name}: {str(e)[:100]}")
        tests.append((module_name, False))
        traceback.print_exc()
        return False

print("\nCore modules:")
test_import("fastapi")
test_import("uvicorn")
test_import("pymongo")

print("\nApp imports:")
test_import("app.core.config")
test_import("app.core.database")
test_import("app.core.security")
test_import("app.models.user")
test_import("app.models.student")
test_import("app.models.attendance")
test_import("app.crud.student_crud")
test_import("app.crud.attendance_crud_v2")
test_import("app.services.matching_service")
test_import("app.services.face_detector")
test_import("app.api.auth")
test_import("app.main")

print("\n" + "=" * 60)
passed = sum(1 for _, result in tests if result)
total = len(tests)
print(f"RESULT: {passed}/{total} imports successful")
print("=" * 60)
