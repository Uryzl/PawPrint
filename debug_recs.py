#!/usr/bin/env python3

from app import get_cached_recommendations

def debug_recommendations():
    print("Debugging recommendations...")
    
    recs, info = get_cached_recommendations('RE14884')
    
    print(f"Recommendations count: {len(recs)}")
    print(f"Context info: {info}")
    
    if recs:
        print(f"First recommendation: {recs[0].get('course_id', 'Unknown')}")
        print(f"First rec keys: {list(recs[0].keys())}")
    else:
        print("No recommendations returned!")

if __name__ == "__main__":
    debug_recommendations()