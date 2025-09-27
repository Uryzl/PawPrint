#!/usr/bin/env python3
"""
Neo4j Client for UMBC Degree Planner
Handles all database connections and queries
"""

from neo4j import GraphDatabase
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        # Default to bolt:// for local instances, neo4j:// for cloud
        default_uri = 'bolt://localhost:7687'
        self.uri = os.getenv('NEO4J_URI', default_uri)
        self.username = os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        
        # Fix URI scheme if needed
        if self.uri.startswith('neo4j://localhost'):
            self.uri = self.uri.replace('neo4j://', 'bolt://')
            logger.info(f"Converted URI scheme to bolt:// for local connection")
        
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            # Test connection
            self.driver.verify_connectivity()
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j at {self.uri}")
            logger.error(f"Username: {self.username}")
            logger.error(f"Error: {e}")
            logger.warning("Neo4j features will be disabled. Check your credentials and ensure Neo4j is running.")
            self.driver = None

    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()

    def test_connection(self) -> bool:
        """Test if Neo4j connection is working"""
        if not self.driver:
            return False
            
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                return bool(result.single())
        except Exception as e:
            logger.error(f"Neo4j connection test failed: {e}")
            return False

    def _check_connection(self):
        """Check if driver is available, raise exception if not"""
        if not self.driver:
            raise Exception("Neo4j connection not available. Check your credentials and ensure Neo4j is running.")

    def _convert_neo4j_types(self, data):
        """Convert Neo4j types to JSON-serializable types"""
        if isinstance(data, dict):
            return {key: self._convert_neo4j_types(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_neo4j_types(item) for item in data]
        elif hasattr(data, 'year') and hasattr(data, 'month') and hasattr(data, 'day'):
            # Neo4j Date object
            return f"{data.year}-{data.month:02d}-{data.day:02d}"
        elif hasattr(data, 'isoformat'):
            # Python datetime/date objects
            return data.isoformat()
        else:
            return data

    def get_all_students(self, limit: int = 100) -> List[Dict]:
        """Get list of all students for selection"""
        if not self.driver:
            logger.warning("Neo4j not connected, returning demo data")
            return self._get_demo_students()
            
        query = """
        MATCH (s:Student)
        OPTIONAL MATCH (s)-[:PURSUING]->(d:Degree)
        RETURN s.id as id, s.name as name, s.learningStyle as learning_style,
               d.name as degree_name, s.expectedGraduation as expected_graduation
        ORDER BY s.name
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, limit=limit)
                students = [dict(record) for record in result]
                return [self._convert_neo4j_types(student) for student in students]
        except Exception as e:
            logger.error(f"Error fetching students: {e}")
            return self._get_demo_students()

    def _get_demo_students(self) -> List[Dict]:
        """Return demo student data when Neo4j is not available"""
        return [
            {
                "id": "ST12345",
                "name": "Alice Johnson",
                "learning_style": "Visual",
                "degree_name": "Bachelor of Science in Computer Science",
                "expected_graduation": "2025-05-15"
            },
            {
                "id": "ST23456", 
                "name": "Bob Smith",
                "learning_style": "Kinesthetic",
                "degree_name": "Bachelor of Arts in Computer Science",
                "expected_graduation": "2025-12-15"
            },
            {
                "id": "ST34567",
                "name": "Carol Davis",
                "learning_style": "Auditory", 
                "degree_name": "Bachelor of Science in Biology",
                "expected_graduation": "2026-05-15"
            },
            {
                "id": "ST45678",
                "name": "David Wilson",
                "learning_style": "Reading-Writing",
                "degree_name": "Bachelor of Arts in Biology", 
                "expected_graduation": "2025-08-15"
            }
        ]

    def get_student_details(self, student_id: str) -> Optional[Dict]:
        """Get detailed information about a specific student"""
        query = """
        MATCH (s:Student {id: $student_id})
        OPTIONAL MATCH (s)-[:PURSUING]->(d:Degree)
        RETURN s.id as id, s.name as name, s.learningStyle as learning_style,
               s.preferredCourseLoad as preferred_course_load,
               s.preferredPace as preferred_pace,
               s.workHoursPerWeek as work_hours_per_week,
               s.financialAidStatus as financial_aid_status,
               s.preferredInstructionMode as preferred_instruction_mode,
               s.enrollmentDate as enrollment_date,
               s.expectedGraduation as expected_graduation,
               d.id as degree_id, d.name as degree_name,
               d.totalCredits as total_credits
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            record = result.single()
            return dict(record) if record else None

    def get_student_completed_courses(self, student_id: str) -> List[Dict]:
        """Get courses completed by a student"""
        query = """
        MATCH (s:Student {id: $student_id})-[comp:COMPLETED]->(c:Course)
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.department as department, c.level as level,
               comp.grade as grade, comp.term as term,
               comp.studyHours as study_hours, comp.difficulty as difficulty
        ORDER BY comp.term, c.level, c.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            return [dict(record) for record in result]

    def get_student_enrolled_courses(self, student_id: str) -> List[Dict]:
        """Get courses currently enrolled by a student"""
        query = """
        MATCH (s:Student {id: $student_id})-[enr:ENROLLED_IN]->(c:Course)
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.department as department, c.level as level,
               enr.term as term, enr.expectedGrade as expected_grade
        ORDER BY enr.term, c.level, c.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            return [dict(record) for record in result]

    def get_student_degree(self, student_id: str) -> Optional[Dict]:
        """Get degree program information for a student"""
        query = """
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (rg:RequirementGroup)-[:PART_OF]->(d)
        OPTIONAL MATCH (c:Course)-[:FULFILLS]->(rg)
        WITH d, rg, COUNT(c) as courses_in_group
        RETURN d.id as degree_id, d.name as degree_name, d.department as department,
               d.type as degree_type, d.totalCredits as total_credits,
               COLLECT({
                   id: rg.id,
                   name: rg.name,
                   required_courses: rg.requiredCourses,
                   credits_required: rg.creditsRequired,
                   course_count: courses_in_group
               }) as requirement_groups
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            record = result.single()
            return dict(record) if record else None

    def get_available_courses(self, student_id: str, term: str = None) -> List[Dict]:
        """Get courses available to a student (prerequisites met, not already taken)"""
        query = """
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (c:Course)-[:FULFILLS]->(:RequirementGroup)-[:PART_OF]->(d)
        
        // Ensure prerequisites are met
        WHERE NOT EXISTS {
            MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
            WHERE NOT (s)-[:COMPLETED]->(prereq)
        }
        
        // Student hasn't already completed the course
        AND NOT (s)-[:COMPLETED]->(c)
        AND NOT (s)-[:ENROLLED_IN]->(c)
        
        // If term is specified, check if course is offered
        """ + ("""
        AND EXISTS((c)-[:OFFERED_IN]->(:Term {id: $term}))
        """ if term else "") + """
        
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.department as department, c.level as level,
               c.avgDifficulty as avg_difficulty, c.instructionModes as instruction_modes,
               c.tags as tags
        ORDER BY c.level, c.name
        """
        
        with self.driver.session() as session:
            params = {"student_id": student_id}
            if term:
                params["term"] = term
            result = session.run(query, **params)
            return [dict(record) for record in result]

    def get_course_prerequisites(self, course_id: str) -> List[Dict]:
        """Get prerequisites for a specific course"""
        query = """
        MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c:Course {id: $course_id})
        RETURN prereq.id as course_id, prereq.name as course_name,
               prereq.credits as credits, prereq.level as level
        ORDER BY prereq.level, prereq.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, course_id=course_id)
            return [dict(record) for record in result]

    def get_courses_unlocked_by(self, course_id: str) -> List[Dict]:
        """Get courses that would be unlocked by taking a specific course"""
        query = """
        MATCH (c:Course {id: $course_id})-[:PREREQUISITE_FOR]->(unlocked:Course)
        RETURN unlocked.id as course_id, unlocked.name as course_name,
               unlocked.credits as credits, unlocked.level as level
        ORDER BY unlocked.level, unlocked.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, course_id=course_id)
            return [dict(record) for record in result]

    def get_similar_students(self, student_id: str, min_similarity: float = 0.7) -> List[Dict]:
        """Find students similar to the given student"""
        query = """
        MATCH (s:Student {id: $student_id})
        MATCH (s)-[sim:SIMILAR_LEARNING_STYLE|SIMILAR_PERFORMANCE]->(similar:Student)
        WHERE sim.similarity >= $min_similarity
        
        // Get their performance info
        OPTIONAL MATCH (similar)-[comp:COMPLETED]->(c:Course)
        WITH s, similar, sim, 
             AVG(CASE comp.grade
                 WHEN 'A' THEN 4.0 WHEN 'A-' THEN 3.7 WHEN 'B+' THEN 3.3
                 WHEN 'B' THEN 3.0 WHEN 'B-' THEN 2.7 WHEN 'C+' THEN 2.3
                 WHEN 'C' THEN 2.0 WHEN 'C-' THEN 1.7 WHEN 'D+' THEN 1.3
                 WHEN 'D' THEN 1.0 ELSE 0.0 
             END) AS avg_gpa,
             COUNT(comp) as courses_completed
             
        RETURN similar.id as id, similar.name as name, similar.learningStyle as learning_style,
               sim.similarity as similarity, type(sim) as similarity_type,
               avg_gpa, courses_completed
        ORDER BY sim.similarity DESC
        LIMIT 10
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id, min_similarity=min_similarity)
            return [dict(record) for record in result]

    def get_student_context(self, student_id: str) -> Dict:
        """Get comprehensive context about a student for AI recommendations"""
        student = self.get_student_details(student_id)
        if not student:
            return {}
            
        completed = self.get_student_completed_courses(student_id)
        enrolled = self.get_student_enrolled_courses(student_id)
        degree = self.get_student_degree(student_id)
        available = self.get_available_courses(student_id)
        similar = self.get_similar_students(student_id)
        
        return {
            "student": student,
            "completed_courses": completed,
            "enrolled_courses": enrolled,
            "degree_info": degree,
            "available_courses": available,
            "similar_students": similar
        }

    def get_optimal_course_sequence(self, student_id: str) -> List[Dict]:
        """Find optimal course sequence considering prerequisites and learning style"""
        query = """
        // Get student's degree and available courses
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (c:Course)-[:FULFILLS]->(:RequirementGroup)-[:PART_OF]->(d)
        
        // Ensure prerequisites are met or can be met
        WHERE NOT EXISTS {
            MATCH (prereq:Course)-[:PREREQUISITE_FOR]->(c)
            WHERE NOT (s)-[:COMPLETED]->(prereq)
        }
        AND NOT (s)-[:COMPLETED]->(c)
        AND NOT (s)-[:ENROLLED_IN]->(c)
        
        // Get similar students' experiences with these courses
        OPTIONAL MATCH (s)-[sim:SIMILAR_LEARNING_STYLE]->(similar:Student)-[comp:COMPLETED]->(c)
        WHERE sim.similarity > 0.7
        
        // Calculate predicted difficulty and success rate
        WITH c, s, 
             CASE WHEN COUNT(comp) > 0 
                  THEN AVG(comp.difficulty) 
                  ELSE c.avgDifficulty 
             END as predicted_difficulty,
             CASE WHEN COUNT(comp) > 0
                  THEN AVG(CASE WHEN comp.grade IN ['A', 'A-', 'B+'] THEN 1.0 ELSE 0.0 END)
                  ELSE 0.7
             END as success_rate,
             COUNT(comp) as similar_student_data
        
        // Count courses this would unlock
        OPTIONAL MATCH (c)-[:PREREQUISITE_FOR]->(unlocked:Course)-[:FULFILLS]->(:RequirementGroup)-[:PART_OF]->(d:Degree)
        WHERE NOT (s)-[:COMPLETED]->(unlocked)
        
        RETURN c.id as course_id, c.name as course_name, c.credits as credits,
               c.level as level, c.department as department,
               predicted_difficulty, success_rate, similar_student_data,
               COUNT(unlocked) as courses_unlocked,
               c.instructionModes as instruction_modes
        ORDER BY c.level ASC, predicted_difficulty ASC, courses_unlocked DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            return [dict(record) for record in result]

    def get_degree_requirements_progress(self, student_id: str) -> Dict:
        """Get detailed progress on degree requirements"""
        query = """
        MATCH (s:Student {id: $student_id})-[:PURSUING]->(d:Degree)
        MATCH (rg:RequirementGroup)-[:PART_OF]->(d)
        
        // Get courses that fulfill this requirement group
        OPTIONAL MATCH (course:Course)-[:FULFILLS]->(rg)
        
        // Get completed courses in this requirement group
        OPTIONAL MATCH (s)-[:COMPLETED]->(completed_course:Course)-[:FULFILLS]->(rg)
        
        // Get enrolled courses in this requirement group  
        OPTIONAL MATCH (s)-[:ENROLLED_IN]->(enrolled_course:Course)-[:FULFILLS]->(rg)
        
        WITH rg, 
             COLLECT(DISTINCT {
                 id: course.id, 
                 name: course.name, 
                 credits: course.credits,
                 level: course.level
             }) as all_courses,
             COLLECT(DISTINCT {
                 id: completed_course.id,
                 name: completed_course.name,
                 credits: completed_course.credits
             }) as completed_courses,
             COLLECT(DISTINCT {
                 id: enrolled_course.id,
                 name: enrolled_course.name, 
                 credits: enrolled_course.credits
             }) as enrolled_courses,
             SUM(completed_course.credits) as completed_credits,
             SUM(enrolled_course.credits) as enrolled_credits
             
        RETURN rg.id as requirement_id, rg.name as requirement_name,
               rg.creditsRequired as credits_required,
               rg.requiredCourses as courses_required,
               COALESCE(completed_credits, 0) as completed_credits,
               COALESCE(enrolled_credits, 0) as enrolled_credits,
               all_courses, completed_courses, enrolled_courses
        ORDER BY rg.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, student_id=student_id)
            requirements = [dict(record) for record in result]
            
            # Calculate overall progress
            total_required = sum(req['credits_required'] for req in requirements)
            total_completed = sum(req['completed_credits'] for req in requirements)
            total_enrolled = sum(req['enrolled_credits'] for req in requirements)
            
            return {
                "requirements": requirements,
                "total_credits_required": total_required,
                "total_credits_completed": total_completed,
                "total_credits_enrolled": total_enrolled,
                "total_credits_remaining": total_required - total_completed - total_enrolled,
                "completion_percentage": (total_completed / total_required * 100) if total_required > 0 else 0
            }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
