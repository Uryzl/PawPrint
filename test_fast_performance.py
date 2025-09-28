#!/usr/bin/env python3

from app import get_fast_demo_context, get_cached_recommendations
import time

def test_fast_performance():
    print("Testing ultra-fast performance...")
    
    student_id = 'RE14884'
    
    # Test fast context
    start = time.time()
    ctx = get_fast_demo_context(student_id)
    elapsed = (time.time() - start) * 1000
    print(f"Fast context: {elapsed:.2f}ms")
    print(f"Keys: {list(ctx.keys())}")
    print(f"Available courses: {len(ctx.get('available_courses', []))}")
    print(f"Similar students: {len(ctx.get('similar_students', []))}")
    
    # Test cached recommendations (first call)
    print(f"\nTesting cached recommendations (first call):")
    start = time.time()
    recs1, info1 = get_cached_recommendations(student_id)
    elapsed1 = (time.time() - start) * 1000
    print(f"First call: {elapsed1:.2f}ms ({len(recs1)} recommendations)")
    print(f"Context time: {info1.get('context_time_ms', 'N/A')}ms")
    print(f"AI time: {info1.get('ai_time_ms', 'N/A')}ms")
    
    # Test cached recommendations (second call - should be cached)
    print(f"\nTesting cached recommendations (second call - should be cached):")
    start = time.time()
    recs2, info2 = get_cached_recommendations(student_id)
    elapsed2 = (time.time() - start) * 1000
    print(f"Second call: {elapsed2:.2f}ms ({len(recs2)} recommendations)")
    print(f"Cached: {info2.get('cached', False)}")
    
    print(f"\n🚀 PERFORMANCE IMPROVEMENT:")
    print(f"   Fast context: {elapsed:.2f}ms (vs ~12,000ms before)")
    print(f"   First recommendations: {elapsed1:.2f}ms")  
    print(f"   Cached recommendations: {elapsed2:.2f}ms")
    print(f"   Speed improvement: {12000/elapsed:.1f}x faster context!")

if __name__ == "__main__":
    test_fast_performance()