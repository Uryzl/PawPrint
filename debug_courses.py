#!/usr/bin/env python3
"""
Debug script to test the course data issue
"""

from neo4j_client import Neo4jClient

def test_student_data():
    client = Neo4jClient()
    
    print("Testing student data retrieval...")
    
    # Test the complete data method
    data = client.get_student_complete_data("RE14884")
    
    if data:
        print(f"Student: {data['student']['name']}")
        print(f"Student data keys: {list(data['student'].keys())}")
        print(f"Learning style: {data['student'].get('learning_style', 'NOT FOUND')}")
        print(f"Learning style (alt): {data['student'].get('learningStyle', 'NOT FOUND')}")
        print(f"Preferred course load: {data['student'].get('preferred_course_load', 'NOT FOUND')}")
        print(f"Preferred course load (alt): {data['student'].get('preferredCourseLoad', 'NOT FOUND')}")
        print(f"Work hours: {data['student'].get('work_hours_per_week', 'NOT FOUND')}")
        print(f"Work hours (alt): {data['student'].get('workHoursPerWeek', 'NOT FOUND')}")
        print(f"Completed courses: {len(data.get('completed_courses', []))}")
        print(f"Enrolled courses: {len(data.get('enrolled_courses', []))}")
    else:
        print("No data returned!")
    
    client.close()

if __name__ == "__main__":
    test_student_data()