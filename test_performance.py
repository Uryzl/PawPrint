#!/usr/bin/env python3

import time
from gemini_client import GeminiClient
from neo4j_client import Neo4jClient

def test_performance_improvements():
    print("Testing performance improvements...")
    
    # Initialize clients
    gemini = GeminiClient()
    neo4j = Neo4jClient()
    
    student_id = 'RE14884'
    
    # Test 1: Basic context vs Enhanced context
    print("\n1. Testing context generation times:")
    
    start = time.time()
    basic_context = neo4j.get_student_context(student_id)
    basic_time = (time.time() - start) * 1000
    print(f"   Basic context: {basic_time:.2f}ms")
    
    start = time.time()
    enhanced_context = neo4j.get_enhanced_student_context(student_id)
    enhanced_time = (time.time() - start) * 1000
    print(f"   Enhanced context: {enhanced_time:.2f}ms")
    
    # Test 2: AI Recommendations (first call - no cache)
    print("\n2. Testing AI recommendations (first call):")
    start = time.time()
    recs1 = gemini.get_course_recommendations(
        enhanced_context, 
        enhanced_context.get('available_courses', []), 
        enhanced_context.get('similar_students', [])
    )
    ai_time1 = (time.time() - start) * 1000
    print(f"   First AI call: {ai_time1:.2f}ms ({len(recs1)} recommendations)")
    
    # Test 3: AI Recommendations (second call - should be same)
    print("\n3. Testing AI recommendations (second call):")
    start = time.time()
    recs2 = gemini.get_course_recommendations(
        enhanced_context, 
        enhanced_context.get('available_courses', []), 
        enhanced_context.get('similar_students', [])
    )
    ai_time2 = (time.time() - start) * 1000
    print(f"   Second AI call: {ai_time2:.2f}ms ({len(recs2)} recommendations)")
    
    # Summary
    print(f"\n📊 PERFORMANCE SUMMARY for {student_id}:")
    print(f"   Basic context: {basic_time:.2f}ms")
    print(f"   Enhanced context: {enhanced_time:.2f}ms")
    print(f"   AI recommendations: {ai_time1:.2f}ms")
    print(f"   Context keys: {list(enhanced_context.keys())}")
    print(f"   Available courses: {len(enhanced_context.get('available_courses', []))}")
    print(f"   Similar students: {len(enhanced_context.get('similar_students', []))}")

if __name__ == "__main__":
    test_performance_improvements()