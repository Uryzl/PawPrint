#!/usr/bin/env python3

import time
from app import app

def test_api_performance():
    """Test the async API endpoint performance"""
    with app.test_client() as client:
        print("Testing API endpoint performance...")
        
        # Test first call (no cache)
        start = time.time()
        response = client.get('/api/course-recommendations/RE14884')
        elapsed = (time.time() - start) * 1000
        
        data = response.get_json()
        
        print(f"First API call: {elapsed:.2f}ms")
        print(f"Success: {data.get('success', False)}")
        print(f"Recommendations: {len(data.get('recommendations', []))}")
        print(f"Cached: {data.get('cached', False)}")
        
        if data.get('context_info'):
            print(f"Context time: {data['context_info'].get('context_time_ms', 'N/A')}ms")
            print(f"AI time: {data['context_info'].get('ai_time_ms', 'N/A')}ms")
        
        # Test second call (should be cached)
        print(f"\nTesting second call (should be cached):")
        start = time.time()
        response2 = client.get('/api/course-recommendations/RE14884')
        elapsed2 = (time.time() - start) * 1000
        
        data2 = response2.get_json()
        print(f"Second API call: {elapsed2:.2f}ms")
        print(f"Cached: {data2.get('cached', False)}")
        
        # Test page load performance
        print(f"\nTesting page load (should be instant):")
        start = time.time()
        page_response = client.get('/student/RE14884/recommendations')
        page_elapsed = (time.time() - start) * 1000
        
        print(f"Page load time: {page_elapsed:.2f}ms")
        print(f"Status: {page_response.status_code}")

if __name__ == "__main__":
    test_api_performance()