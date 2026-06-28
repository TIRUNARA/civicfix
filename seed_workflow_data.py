# Projects/civicfix/seed_workflow_data.py
import sys
import os

# Ensure the database module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_db

def seed():
    conn = get_db()
    cursor = conn.cursor()
    
    # Clear existing reviewers and fixers
    cursor.execute("DELETE FROM reviewers")
    cursor.execute("DELETE FROM fixers")
    
    # Mock Reviewers (Location close to reports in Bengaluru: lat ~12.97, lng ~77.59)
    reviewers = [
        ("REV-01", "Inspector Rajesh (Roads)", "Municipal Roads", 12.9700, 77.5900, 1),
        ("REV-02", "Inspector Amit (Roads)", "Municipal Roads", 12.9800, 77.6100, 1),
        ("REV-03", "Inspector Priya (Water)", "Water & Sanitation", 12.9750, 77.6000, 1),
        ("REV-04", "Inspector Kiran (Water)", "Water & Sanitation", 12.9650, 77.5850, 1),
        ("REV-05", "Inspector Sunil (Waste)", "Solid Waste", 12.9300, 77.6100, 1),
        ("REV-06", "Inspector Deepa (Lights)", "Utility Streetlighting", 12.9200, 77.5800, 1)
    ]
    
    for r_id, name, dept, lat, lon, avail in reviewers:
        cursor.execute(
            "INSERT INTO reviewers (id, name, department, latitude, longitude, is_available) VALUES (?, ?, ?, ?, ?, ?)",
            (r_id, name, dept, lat, lon, avail)
        )
        
    # Mock Fixers
    fixers = [
        ("FIX-01", "Road Crew Alpha", "Municipal Roads", 1),
        ("FIX-02", "Road Crew Beta", "Municipal Roads", 1),
        ("FIX-03", "Sanitation Crew Alpha", "Water & Sanitation", 1),
        ("FIX-04", "Sanitation Crew Beta", "Water & Sanitation", 1),
        ("FIX-05", "Solid Waste Team A", "Solid Waste", 1),
        ("FIX-06", "Electric Repair Team 1", "Utility Streetlighting", 1)
    ]
    
    for f_id, name, dept, avail in fixers:
        cursor.execute(
            "INSERT INTO fixers (id, name, department, is_available) VALUES (?, ?, ?, ?)",
            (f_id, name, dept, avail)
        )
        
    conn.commit()
    conn.close()
    print("Workflow seeder completed successfully.")

if __name__ == "__main__":
    seed()
