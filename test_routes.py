#!/usr/bin/env python3
"""
Test script to verify chat route conflicts are resolved
"""

import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_routes():
    """Test that chat routes are properly configured"""
    try:
        # Import the application
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            print("Checking chat-related routes:")
            print("=" * 50)
            
            chat_routes = []
            for rule in app.url_map.iter_rules():
                if 'chat' in str(rule.rule):
                    chat_routes.append((rule.rule, rule.endpoint, rule.methods))
                    print(f"Route: {rule.rule}")
                    print(f"Endpoint: {rule.endpoint}")
                    print(f"Methods: {rule.methods}")
                    print("-" * 30)
            
            # Check for conflicts
            if len(chat_routes) == 0:
                print("❌ No chat routes found!")
                return False
                
            routes_by_path = {}
            for route, endpoint, methods in chat_routes:
                if route in routes_by_path:
                    routes_by_path[route].append((endpoint, methods))
                else:
                    routes_by_path[route] = [(endpoint, methods)]
            
            print("\nRoute conflict analysis:")
            print("=" * 50)
            
            conflicts_found = False
            for route_path, endpoints in routes_by_path.items():
                if len(endpoints) > 1:
                    print(f"❌ CONFLICT at {route_path}:")
                    for endpoint, methods in endpoints:
                        print(f"   - {endpoint} ({methods})")
                    conflicts_found = True
                else:
                    endpoint, methods = endpoints[0]
                    print(f"✅ {route_path} -> {endpoint} ({methods})")
            
            if not conflicts_found:
                print("\n✅ No route conflicts found!")
                return True
            else:
                print("\n❌ Route conflicts detected!")
                return False
                
    except Exception as e:
        print(f"❌ Error testing routes: {e}")
        return False

if __name__ == "__main__":
    success = test_routes()
    sys.exit(0 if success else 1)