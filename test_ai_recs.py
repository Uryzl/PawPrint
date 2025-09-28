#!/usr/bin/env python3

from gemini_client import GeminiClient
from neo4j_client import Neo4jClient

def test_ai_recommendations():
    print("Testing AI course recommendations...")
    
    # Initialize clients
    gemini = GeminiClient()
    neo4j = Neo4jClient()
    
    # Get enhanced context
    print("Getting enhanced student context...")
    context = neo4j.get_enhanced_student_context('RE14884')
    
    print(f"Enhanced context keys: {list(context.keys())}")
    print(f"Available courses: {len(context.get('available_courses', []))}")
    print(f"Similar students: {len(context.get('similar_students', []))}")
    
    # Get recommendations
    print("\nGenerating AI recommendations...")
    recs = gemini.get_course_recommendations(
        context, 
        context.get('available_courses', []), 
        context.get('similar_students', [])
    )
    
    print(f"\nGenerated {len(recs)} recommendations:")
    for i, r in enumerate(recs[:3], 1):
        print(f"\n{i}. Course: {r.get('course_id', 'Unknown')}: {r.get('course_name', 'Unknown')}")
        print(f"   Priority: {r.get('priority', 'Unknown')}")
        print(f"   Score: {r.get('recommendation_score', 0)}")
        print(f"   Reasoning: {r.get('ai_reasoning', 'No reasoning provided')[:100]}...")

if __name__ == "__main__":
    test_ai_recommendations()