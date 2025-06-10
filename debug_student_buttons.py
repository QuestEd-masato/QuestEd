#!/usr/bin/env python3
"""
Debug script to help identify student dashboard button issues
This script can be run independently or integrated into the Flask app
"""

# Route information extracted from code analysis
STUDENT_DASHBOARD_ROUTES = {
    'Survey Routes': {
        'student.interest_survey_edit': {
            'function': 'interest_survey_edit',
            'file': 'app/student/__init__.py:450',
            'decorators': ['@login_required', '@student_required'],
            'requirements': 'Existing InterestSurvey record',
            'redirect_on_missing': 'student.interest_survey'
        },
        'student.interest_survey': {
            'function': 'interest_survey',
            'file': 'app/student/__init__.py:417',
            'decorators': ['@login_required', '@student_required'],
            'requirements': 'None',
            'redirect_on_existing': 'student.interest_survey_edit'
        },
        'student.personality_survey_edit': {
            'function': 'personality_survey_edit',
            'file': 'app/student/__init__.py:515',
            'decorators': ['@login_required', '@student_required'],
            'requirements': 'Existing PersonalitySurvey record',
            'redirect_on_missing': 'student.personality_survey'
        },
        'student.personality_survey': {
            'function': 'personality_survey',
            'file': 'app/student/__init__.py:482',
            'decorators': ['@login_required', '@student_required'],
            'requirements': 'None',
            'redirect_on_existing': 'student.personality_survey_edit'
        }
    },
    'Theme Routes': {
        'student.view_themes': {
            'function': 'view_themes',
            'file': 'app/student/__init__.py:1210',
            'decorators': ['@login_required'],
            'requirements': 'class_id parameter (optional)',
            'notes': 'Shows class selection if no class_id provided'
        }
    },
    'BaseBuilder Routes': {
        'basebuilder_module.index': {
            'function': 'index',
            'file': 'basebuilder/routes.py:24',
            'decorators': ['@login_required'],
            'requirements': 'User enrolled in classes',
            'notes': 'Different view for students vs teachers'
        },
        'basebuilder_module.theme_relations': {
            'function': 'theme_relations',
            'file': 'basebuilder/routes.py:1791',
            'decorators': ['@login_required'],
            'requirements': 'Teacher role access',
            'notes': 'May require teacher permissions'
        }
    },
    'Activity Routes': {
        'student.activities': {
            'function': 'activities',
            'file': 'app/student/__init__.py:548',
            'decorators': ['@login_required', '@student_required'],
            'requirements': 'class_id parameter (optional)',
            'notes': 'Shows class selection if no class_id provided'
        },
        'student.new_activity': {
            'function': 'new_activity',
            'file': 'app/student/__init__.py:615',
            'decorators': ['@login_required', '@student_required', '@upload_limit()'],
            'requirements': 'class_id parameter REQUIRED',
            'redirect_on_missing': 'student.activities'
        }
    },
    'Todo and Goals Routes': {
        'student.todos': {
            'function': 'todos',
            'file': 'app/student/__init__.py:928',
            'decorators': ['@login_required', '@student_required'],
            'requirements': 'None'
        },
        'student.goals': {
            'function': 'goals',
            'file': 'app/student/__init__.py:1067',
            'decorators': ['@login_required', '@student_required'],
            'requirements': 'None'
        }
    },
    'Chat Routes': {
        'student.chat_page': {
            'function': 'chat_page',
            'file': 'app/student/__init__.py:2048',
            'decorators': ['@login_required'],
            'requirements': 'class_id parameter (optional for students)',
            'notes': 'Shows class selection if no class_id provided for students'
        }
    }
}

def print_route_analysis():
    """Print detailed analysis of all routes"""
    print("STUDENT DASHBOARD BUTTON LINK ANALYSIS")
    print("=" * 60)
    
    for category, routes in STUDENT_DASHBOARD_ROUTES.items():
        print(f"\n📁 {category}")
        print("-" * 40)
        
        for endpoint, info in routes.items():
            print(f"🔗 {endpoint}")
            print(f"   Function: {info['function']}()")
            print(f"   Location: {info['file']}")
            print(f"   Decorators: {', '.join(info['decorators'])}")
            print(f"   Requirements: {info['requirements']}")
            
            if 'redirect_on_missing' in info:
                print(f"   Redirects to: {info['redirect_on_missing']} (if requirements not met)")
            if 'redirect_on_existing' in info:
                print(f"   Redirects to: {info['redirect_on_existing']} (if already exists)")
            if 'notes' in info:
                print(f"   Notes: {info['notes']}")
            print()

def identify_potential_issues():
    """Identify potential issues with routes"""
    print("\nPOTENTIAL ISSUES ANALYSIS")
    print("=" * 60)
    
    issues = []
    
    # Check for routes requiring parameters
    print("\n🚨 Routes requiring parameters:")
    for category, routes in STUDENT_DASHBOARD_ROUTES.items():
        for endpoint, info in routes.items():
            if 'class_id' in info['requirements']:
                required = 'REQUIRED' in info['requirements']
                status = "❌ REQUIRED" if required else "⚠️  OPTIONAL"
                print(f"   {endpoint}: class_id parameter {status}")
                if required:
                    issues.append(f"{endpoint} requires class_id parameter")
    
    # Check for routes with special access requirements
    print("\n🔒 Routes with special access requirements:")
    for category, routes in STUDENT_DASHBOARD_ROUTES.items():
        for endpoint, info in routes.items():
            if '@student_required' in info['decorators']:
                print(f"   {endpoint}: Student role required")
            if '@upload_limit()' in info['decorators']:
                print(f"   {endpoint}: Upload rate limiting applied")
            if 'Teacher role' in info['requirements']:
                print(f"   {endpoint}: ⚠️  May require teacher role")
                issues.append(f"{endpoint} may not be accessible to students")
    
    # Check for routes that redirect
    print("\n🔄 Routes that redirect based on conditions:")
    for category, routes in STUDENT_DASHBOARD_ROUTES.items():
        for endpoint, info in routes.items():
            if 'redirect_on_missing' in info or 'redirect_on_existing' in info:
                print(f"   {endpoint}: Conditional redirects")
    
    if issues:
        print(f"\n⚠️  POTENTIAL ISSUES FOUND ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("\n✅ No obvious issues detected")

def debugging_checklist():
    """Provide debugging checklist"""
    print("\nDEBUGGING CHECKLIST")
    print("=" * 60)
    
    checklist = [
        "1. Check user authentication status (current_user.is_authenticated)",
        "2. Verify user role (current_user.role == 'student')",
        "3. Check class enrollments (current_user.enrolled_classes)",
        "4. Verify survey completion status",
        "5. Check browser console for JavaScript errors",
        "6. Monitor Flask application logs",
        "7. Test routes individually with required parameters",
        "8. Verify database connectivity and data integrity",
        "9. Check CSRF token validity",
        "10. Verify blueprint registration in app factory"
    ]
    
    for item in checklist:
        print(f"   □ {item}")

def main():
    """Main function"""
    print_route_analysis()
    identify_potential_issues()
    debugging_checklist()
    
    print("\n" + "=" * 60)
    print("CONCLUSION: All button routes exist, issues likely related to:")
    print("- Missing required parameters (especially class_id)")
    print("- User authentication/authorization problems")
    print("- Database state or enrollment issues")
    print("- Frontend JavaScript or CSRF token problems")

if __name__ == '__main__':
    main()