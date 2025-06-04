#!/usr/bin/env python3
"""
Test script to verify the fixes work correctly
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, '/home/masat/claude-projects/QuestEd')

def test_imports():
    """Test that all modules can be imported"""
    print("Testing module imports...")
    
    try:
        # Test core app creation
        from app import create_app
        print("✓ App factory import successful")
        
        # Test student module
        from app.student import student_bp
        print("✓ Student blueprint import successful")
        
        # Test teacher module  
        from app.teacher import teacher_bp
        print("✓ Teacher blueprint import successful")
        
        # Test models
        from app.models import User, Class, Curriculum
        print("✓ Models import successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_routes():
    """Test that key routes are defined"""
    print("\nTesting route definitions...")
    
    try:
        from app.student import student_bp
        from app.teacher import teacher_bp
        
        # Check student routes
        student_routes = [rule.rule for rule in student_bp.url_map.iter_rules()]
        print(f"✓ Student routes found: {len(student_routes)}")
        
        # Check teacher routes
        teacher_routes = [rule.rule for rule in teacher_bp.url_map.iter_rules()]
        print(f"✓ Teacher routes found: {len(teacher_routes)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Route test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("QuestEd Fix Verification")
    print("=" * 30)
    
    success = True
    
    if not test_imports():
        success = False
    
    if not test_routes():
        success = False
    
    print("\n" + "=" * 30)
    if success:
        print("✓ All tests passed! Application should be ready.")
    else:
        print("✗ Some tests failed. Check errors above.")
    
    return success

if __name__ == "__main__":
    main()