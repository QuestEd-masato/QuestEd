#!/usr/bin/env python3
"""
Test script to verify all routes referenced in student_dashboard.html exist
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from flask import url_for

def test_routes():
    """Test all routes referenced in the student dashboard template"""
    
    app = create_app()
    
    with app.app_context():
        routes_to_test = [
            # Survey routes
            ('student.interest_survey_edit', 'Interest Survey Edit'),
            ('student.interest_survey', 'Interest Survey'),
            ('student.personality_survey_edit', 'Personality Survey Edit'), 
            ('student.personality_survey', 'Personality Survey'),
            
            # Theme routes
            ('student.view_themes', 'View Themes'),
            
            # Activity routes
            ('student.activities', 'Activities List'),
            ('student.new_activity', 'New Activity'),
            
            # Todo and Goals routes
            ('student.todos', 'Todo List'),
            ('student.goals', 'Goals List'),
            
            # Chat route
            ('student.chat_page', 'Chat Page'),
            
            # BaseBuilder routes
            ('basebuilder_module.index', 'BaseBuilder Index'),
            ('basebuilder_module.theme_relations', 'BaseBuilder Theme Relations'),
        ]
        
        print("Testing Student Dashboard Routes:")
        print("=" * 50)
        
        working_routes = []
        missing_routes = []
        
        for endpoint, description in routes_to_test:
            try:
                url = url_for(endpoint)
                working_routes.append((endpoint, description, url))
                print(f"✅ {description:<30} -> {endpoint}")
            except Exception as e:
                missing_routes.append((endpoint, description, str(e)))
                print(f"❌ {description:<30} -> {endpoint} (ERROR: {e})")
        
        print("\n" + "=" * 50)
        print(f"Summary: {len(working_routes)} working, {len(missing_routes)} missing")
        
        if missing_routes:
            print("\nMissing Routes:")
            print("-" * 30)
            for endpoint, description, error in missing_routes:
                print(f"- {endpoint}: {error}")
                
        return len(missing_routes) == 0

if __name__ == '__main__':
    success = test_routes()
    sys.exit(0 if success else 1)