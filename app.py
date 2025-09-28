#!/usr/bin/env python3
"""
UMBC Degree Planner - Interactive tool for optimal graduation paths
Integrates Neo4j student data with Gemini AI for personalized guidance
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import logging
from datetime import datetime, date, timedelta
import secrets
import json
import time
from functools import wraps

# Import our custom modules
from neo4j_client import Neo4jClient
from gemini_client import GeminiClient
from degree_optimizer import DegreeOptimizer

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Custom JSON encoder for Neo4j data types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        # Handle Neo4j Date objects
        if hasattr(obj, 'year') and hasattr(obj, 'month') and hasattr(obj, 'day'):
            return f"{obj.year}-{obj.month:02d}-{obj.day:02d}"
        return super().default(obj)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.json_encoder = CustomJSONEncoder
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory cache for student data
student_cache = {}
CACHE_TTL = 300  # 5 minutes cache

def get_cached_student_data(student_id: str):
    """Get student data from cache or database"""
    current_time = time.time()
    
    # Check if data is in cache and not expired
    if student_id in student_cache:
        cached_data, timestamp = student_cache[student_id]
        if current_time - timestamp < CACHE_TTL:
            logger.info(f"Using cached data for student {student_id}")
            return cached_data
    
    # Fetch fresh data
    logger.info(f"Fetching fresh data for student {student_id}")
    data = neo4j_client.get_student_complete_data(student_id)
    
    if data:
        student_cache[student_id] = (data, current_time)
    
    return data

# Initialize clients with error handling
try:
    neo4j_client = Neo4jClient()
    logger.info("Neo4j client initialized")
except Exception as e:
    logger.error(f"Failed to initialize Neo4j client: {e}")
    neo4j_client = None

try:
    gemini_client = GeminiClient()
    logger.info("Gemini client initialized")
except Exception as e:
    logger.warning(f"Gemini client initialization failed: {e}")
    gemini_client = None

# Initialize optimizer
if neo4j_client:
    degree_optimizer = DegreeOptimizer(neo4j_client, gemini_client)
else:
    degree_optimizer = None
    logger.warning("Degree optimizer disabled - Neo4j connection required")

@app.route('/')
def index():
    """Home page with student search"""
    return render_template('home.html')

@app.route('/students')
def students():
    """Student listing page with search"""
    try:
        search = request.args.get('search', '')
        if not neo4j_client:
            students = []
        else:
            students = neo4j_client.search_students(search) if search else neo4j_client.get_all_students()
        return render_template('students.html', students=students, search=search)
    except Exception as e:
        logger.error(f"Error loading students page: {e}")
        return render_template('students.html', students=[], search='', error=str(e))

@app.route('/student/<student_id>')
def student_overview(student_id):
    """Student overview page - degree progress, timeline, risk factors"""
    try:
        if not neo4j_client:
            return render_template('error.html', error="Neo4j not connected"), 500
        
        # Get all data in one optimized call with caching
        data = get_cached_student_data(student_id)
        if not data:
            return render_template('error.html', error="Student not found"), 404
        
        return render_template('student_overview.html', 
                             student=data['student'],
                             completed_courses=data['completed_courses'],
                             enrolled_courses=data['enrolled_courses'],
                             degree_info=data['degree_info'])
    except Exception as e:
        logger.error(f"Error loading student overview for {student_id}: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/student/<student_id>/pathway')
def student_pathway(student_id):
    """Optimal graduation pathway page"""
    try:
        if not neo4j_client:
            return render_template('error.html', error="Neo4j not connected"), 500
        
        # Get cached student data (much faster)
        data = get_cached_student_data(student_id)
        if not data:
            return render_template('error.html', error="Student not found"), 404
        
        # Get existing optimized path if available
        optimized_path = None
        if degree_optimizer:
            try:
                optimized_path = degree_optimizer.find_optimal_path(student_id)
            except Exception as e:
                logger.warning("Could not generate optimal path: %s", e)
        
        return render_template('student_pathway.html', 
                             student=data['student'],
                             optimized_path=optimized_path)
    except Exception as e:
        logger.error("Error loading student pathway for %s: %s", student_id, e)
        return render_template('error.html', error=str(e)), 500

@app.route('/student/<student_id>/recommendations')
def student_recommendations(student_id):
    """AI-powered course recommendations page"""
    try:
        if not neo4j_client:
            return render_template('error.html', error="Neo4j not connected"), 500
        
        # Get cached student data (much faster)
        data = get_cached_student_data(student_id)
        if not data:
            return render_template('error.html', error="Student not found"), 404
        
        # Get recommendations
        recommendations = []
        similar_students = []
        if degree_optimizer:
            try:
                recommendations = degree_optimizer.get_course_recommendations(student_id)
            except Exception as e:
                logger.warning("Could not get recommendations: %s", e)
        
        try:
            similar_students = neo4j_client.get_similar_students(student_id)
        except Exception as e:
            logger.warning("Could not get similar students: %s", e)
        
        return render_template('student_recommendations.html', 
                             student=data['student'],
                             recommendations=recommendations,
                             similar_students=similar_students)
    except Exception as e:
        logger.error("Error loading student recommendations for %s: %s", student_id, e)
        return render_template('error.html', error=str(e)), 500

@app.route('/student/<student_id>/chat')
def student_chat(student_id):
    """AI assistant chat interface"""
    try:
        if not neo4j_client:
            return render_template('error.html', error="Neo4j not connected"), 500
        
        # Get cached student data (much faster)
        data = get_cached_student_data(student_id)
        if not data:
            return render_template('error.html', error="Student not found"), 404
        
        return render_template('student_chat.html', student=data['student'])
    except Exception as e:
        logger.error("Error loading student chat for %s: %s", student_id, e)
        return render_template('error.html', error=str(e)), 500

@app.route('/api/students')
def get_students():
    """Get list of students for search/selection"""
    try:
        if not neo4j_client:
            return jsonify({"success": False, "error": "Neo4j not connected"})
        
        students = neo4j_client.get_all_students()
        return jsonify({"success": True, "students": students})
    except Exception as e:
        logger.error(f"Error fetching students: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/student/<student_id>')
def get_student_info(student_id):
    """Get detailed student information including course history"""
    try:
        if not neo4j_client:
            return jsonify({"success": False, "error": "Neo4j not connected"})
            
        student = neo4j_client.get_student_details(student_id)
        if not student:
            return jsonify({"success": False, "error": "Student not found"})
        
        # Get course history and degree progress
        completed_courses = neo4j_client.get_student_completed_courses(student_id)
        enrolled_courses = neo4j_client.get_student_enrolled_courses(student_id)
        degree_info = neo4j_client.get_student_degree(student_id)
        
        return jsonify({
            "success": True,
            "student": student,
            "completed_courses": completed_courses,
            "enrolled_courses": enrolled_courses,
            "degree_info": degree_info
        })
    except Exception as e:
        logger.error(f"Error fetching student info for {student_id}: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/optimize-path/<student_id>')
def optimize_graduation_path(student_id):
    """Generate optimal graduation path for a student"""
    try:
        path_data = degree_optimizer.find_optimal_path(student_id)
        return jsonify({"success": True, "path": path_data})
    except Exception as e:
        logger.error(f"Error optimizing path for {student_id}: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/chat', methods=['POST'])
def chat_with_gemini():
    """Chat interface with Gemini for academic guidance"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        student_id = data.get('student_id', '')
        context = data.get('context', {})
        
        if not message:
            return jsonify({"success": False, "error": "No message provided"})
        
        # Get student context if student_id provided
        student_context = None
        if student_id:
            student_context = neo4j_client.get_student_context(student_id)
        
        # Get Gemini response
        response = gemini_client.get_academic_advice(
            message, student_context, context
        )
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/course-recommendations/<student_id>')
def get_course_recommendations(student_id):
    """Get AI-powered course recommendations"""
    try:
        recommendations = degree_optimizer.get_course_recommendations(student_id)
        return jsonify({"success": True, "recommendations": recommendations})
    except Exception as e:
        logger.error(f"Error getting recommendations for {student_id}: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/similar-students/<student_id>')
def get_similar_students(student_id):
    """Find similar students for peer learning insights"""
    try:
        similar = neo4j_client.get_similar_students(student_id)
        return jsonify({"success": True, "similar_students": similar})
    except Exception as e:
        logger.error(f"Error finding similar students for {student_id}: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test Neo4j connection
        neo4j_status = neo4j_client.test_connection()
        
        # Test Gemini connection  
        gemini_status = gemini_client.test_connection()
        
        return jsonify({
            "status": "healthy",
            "neo4j": neo4j_status,
            "gemini": gemini_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/debug/neo4j')
def debug_neo4j():
    """Debug endpoint to test Neo4j connection"""
    try:
        # Check environment variables
        env_vars = {
            'NEO4J_URI': os.getenv('NEO4J_URI'),
            'NEO4J_USERNAME': os.getenv('NEO4J_USERNAME'),
            'NEO4J_PASSWORD': '***' if os.getenv('NEO4J_PASSWORD') else None
        }
        
        # Test connection
        is_connected = neo4j_client.test_connection()
        has_driver = neo4j_client.driver is not None
        
        # Try to get students to see if we get demo data
        students = neo4j_client.get_all_students(limit=5)
        using_demo = len(students) > 0 and students[0].get('name') == 'Alice Johnson'
        
        return jsonify({
            "neo4j_status": {
                "has_driver": has_driver,
                "connection_test": is_connected,
                "using_demo_data": using_demo
            },
            "environment_variables": env_vars,
            "sample_students": students[:2],  # First 2 students
            "student_count": len(students)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "neo4j_status": "failed"
        }), 500

@app.route('/api/cache/clear')
def clear_cache():
    """Clear the student data cache"""
    global student_cache
    student_cache.clear()
    logger.info("Student cache cleared")
    return jsonify({
        "success": True,
        "message": "Cache cleared"
    })

@app.route('/api/cache/status')
def cache_status():
    """Get cache status information"""
    current_time = time.time()
    cache_info = {}
    
    for student_id, (data, timestamp) in student_cache.items():
        age = current_time - timestamp
        cache_info[student_id] = {
            "age_seconds": round(age, 1),
            "expires_in": round(CACHE_TTL - age, 1),
            "is_valid": age < CACHE_TTL
        }
    
    return jsonify({
        "cache_entries": len(student_cache),
        "cache_ttl": CACHE_TTL,
        "entries": cache_info
    })

@app.route('/api/setup/sample-data', methods=['POST'])
def create_sample_data():
    """Create sample data in Neo4j database"""
    try:
        if not neo4j_client:
            return jsonify({
                "success": False,
                "error": "Neo4j not connected"
            }), 500
        
        success = neo4j_client.create_sample_data()
        
        # Clear cache after creating new data
        global student_cache
        student_cache.clear()
        
        return jsonify({
            "success": success,
            "message": "Sample data created successfully" if success else "Failed to create sample data"
        })
        
    except Exception as e:
        logger.error("Error creating sample data: %s", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/debug/student/<student_id>/data')
def debug_student_data(student_id):
    """Debug endpoint to see raw student data"""
    try:
        if not neo4j_client:
            return jsonify({"error": "Neo4j not connected"}), 500
        
        data = get_cached_student_data(student_id)
        if not data:
            return jsonify({"error": "Student not found"}), 404
        
        return jsonify({
            "student": data['student'],
            "degree_info": data['degree_info'],
            "completed_courses_count": len(data['completed_courses']),
            "enrolled_courses_count": len(data['enrolled_courses']),
            "completed_courses_sample": data['completed_courses'][:2],  # First 2 for inspection
            "enrolled_courses_sample": data['enrolled_courses'][:2]
        })
    
    except Exception as e:
        logger.error("Error in debug endpoint: %s", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Check for environment variables
    if not os.getenv('NEO4J_URI'):
        logger.warning("NEO4J_URI not set, using default: bolt://localhost:7687")
    if not os.getenv('GOOGLE_API_KEY'):
        logger.warning("GOOGLE_API_KEY not set - Gemini features will be disabled")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
