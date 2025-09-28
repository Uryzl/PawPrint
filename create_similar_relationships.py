#!/usr/bin/env python3
"""
Script to create more similar student relationships in the database
"""

import os
import random
from dotenv import load_dotenv
from neo4j_client import Neo4jClient

# Load environment variables
load_dotenv()

def create_similar_student_relationships():
    """Create similar student relationships based on learning styles and performance"""
    print("🔗 Creating Similar Student Relationships")
    print("=" * 50)
    
    # Initialize Neo4j client
    neo4j_client = Neo4jClient()
    
    if not neo4j_client or not neo4j_client.driver:
        print("❌ Neo4j client not available")
        return False
    
    try:
        with neo4j_client.driver.session() as session:
            # First, get all students
            students_query = """
            MATCH (s:Student)
            RETURN s.id as id, s.name as name, s.learningStyle as learning_style
            ORDER BY s.id
            """
            result = session.run(students_query)
            students = [dict(record) for record in result]
            
            print(f"Found {len(students)} students")
            
            if len(students) < 2:
                print("❌ Need at least 2 students to create relationships")
                return False
            
            # Group students by learning style
            learning_style_groups = {}
            for student in students:
                style = student['learning_style'] or 'Unknown'
                if style not in learning_style_groups:
                    learning_style_groups[style] = []
                learning_style_groups[style].append(student)
            
            print(f"Learning style groups: {list(learning_style_groups.keys())}")
            
            relationships_created = 0
            
            # Create SIMILAR_LEARNING_STYLE relationships
            for style, group in learning_style_groups.items():
                if len(group) > 1:
                    print(f"\nCreating relationships for {style} learning style ({len(group)} students):")
                    
                    for i, student1 in enumerate(group):
                        for j, student2 in enumerate(group):
                            if i != j:  # Don't create self-relationships
                                # Create relationship with random similarity score
                                similarity = round(random.uniform(0.65, 0.95), 2)
                                
                                create_rel_query = """
                                MATCH (s1:Student {id: $student1_id}), (s2:Student {id: $student2_id})
                                MERGE (s1)-[:SIMILAR_LEARNING_STYLE {
                                    similarity: $similarity,
                                    reason: 'Same learning style: ' + $learning_style
                                }]->(s2)
                                """
                                
                                session.run(create_rel_query, 
                                           student1_id=student1['id'],
                                           student2_id=student2['id'],
                                           similarity=similarity,
                                           learning_style=style)
                                
                                relationships_created += 1
                                print(f"   {student1['name']} -> {student2['name']} (similarity: {similarity})")
            
            # Create some cross-style SIMILAR_PERFORMANCE relationships
            print(f"\nCreating cross-style performance relationships:")
            
            # Create random performance-based relationships between different learning styles
            for i in range(min(20, len(students) * 2)):  # Create up to 20 relationships
                student1 = random.choice(students)
                student2 = random.choice(students)
                
                if student1['id'] != student2['id']:
                    # Create performance similarity with random score
                    similarity = round(random.uniform(0.70, 0.90), 2)
                    common_courses = random.sample([
                        "CSCC 200", "MATH 150", "ENGL 100", "HIST 200", 
                        "BIOL 100", "CHEM 150", "PHYS 200", "STAT 100"
                    ], random.randint(2, 5))
                    
                    create_perf_query = """
                    MATCH (s1:Student {id: $student1_id}), (s2:Student {id: $student2_id})
                    MERGE (s1)-[:SIMILAR_PERFORMANCE {
                        similarity: $similarity,
                        courses: $common_courses,
                        reason: 'Similar academic performance patterns'
                    }]->(s2)
                    """
                    
                    session.run(create_perf_query,
                               student1_id=student1['id'],
                               student2_id=student2['id'],
                               similarity=similarity,
                               common_courses=common_courses)
                    
                    relationships_created += 1
                    print(f"   {student1['name']} -> {student2['name']} (perf similarity: {similarity})")
            
            print(f"\n✅ Created {relationships_created} similar student relationships")
            
            # Verify the relationships were created
            verify_query = """
            MATCH ()-[r:SIMILAR_LEARNING_STYLE|SIMILAR_PERFORMANCE]->()
            RETURN type(r) as relationship_type, count(r) as count
            """
            result = session.run(verify_query)
            print(f"\nVerification:")
            for record in result:
                print(f"   {record['relationship_type']}: {record['count']} relationships")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating relationships: {e}")
        return False

if __name__ == "__main__":
    success = create_similar_student_relationships()
    if success:
        print("\n🎉 Similar student relationships created successfully!")
    else:
        print("\n💥 Failed to create similar student relationships")