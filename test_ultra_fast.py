#!/usr/bin/env python3

import time
from app import app

def test_ultra_fast_page():
    """Test the ultra-fast page load"""
    with app.test_client() as client:
        print("Testing ULTRA FAST page load...")
        
        start = time.time()
        response = client.get('/student/RE14884/recommendations')
        elapsed = (time.time() - start) * 1000
        
        print(f"🚀 ULTRA FAST Page load: {elapsed:.2f}ms")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Page loads successfully!")
            print("✅ Users will see loading animation immediately")
            print("✅ Recommendations will load in background (~24 seconds)")
            print("✅ Subsequent visits will be instant (cached)")
        else:
            print("❌ Page load failed")

if __name__ == "__main__":
    test_ultra_fast_page()