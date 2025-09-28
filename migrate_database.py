#!/usr/bin/env python3
"""
Database Migration Script for PawPrint Degree Planner
Creates sample data matching the new Neo4j schema format
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from neo4j_client import Neo4jClient

def main():
    """Main migration function"""
    load_dotenv()
    
    print("🐾 PawPrint Database Migration")
    print("=" * 40)
    
    # Initialize Neo4j client
    try:
        client = Neo4jClient()
        print("✅ Connected to Neo4j")
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        return False
    
    # Test connection
    if not client.test_connection():
        print("❌ Neo4j connection test failed")
        return False
    
    print("✅ Neo4j connection test passed")
    
    # Create sample data
    print("\n📊 Creating sample data...")
    try:
        success = client.create_sample_data()
        if success:
            print("✅ Sample data created successfully")
            
            # Test the new data
            print("\n🔍 Testing new data structure...")
            students = client.get_all_students(limit=5)
            print(f"✅ Found {len(students)} students")
            
            if students:
                student_id = students[0]['id']
                student_data = client.get_student_complete_data(student_id)
                if student_data:
                    print(f"✅ Successfully loaded complete data for student {student_id}")
                    print(f"   - Completed courses: {len(student_data['completed_courses'])}")
                    print(f"   - Enrolled courses: {len(student_data['enrolled_courses'])}")
                else:
                    print(f"⚠️  Could not load complete data for student {student_id}")
            
        else:
            print("❌ Failed to create sample data")
            return False
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False
    
    finally:
        client.close()
    
    print("\n🎉 Migration completed successfully!")
    print("\nYou can now:")
    print("1. Start your Flask app: python app.py")
    print("2. Visit /debug/neo4j to check connection status")
    print("3. Navigate to student pages to see improved performance")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)