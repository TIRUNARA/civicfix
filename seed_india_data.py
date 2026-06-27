#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.request
from pathlib import Path

# Add parent directory to path so database module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ensure DATABASE_URL is set; fallback to default if not present
NEON_DB_URL = "postgresql://neondb_owner:npg_SYnM09aVotlc@ep-billowing-frog-ad0w23w1.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = NEON_DB_URL
    print(f"ℹ️ DATABASE_URL not set in env. Defaulting to Neon: {NEON_DB_URL}")

from database import get_db, init_db

# Direct high-quality Unsplash URLs that are extremely stable and fast to fetch
IMAGE_DATASET = [
    {
        "filename": "delhi_pothole_dwarka.jpg",
        "url": "https://images.unsplash.com/photo-1515162305285-0293e4767cc2?q=80&w=800",
        "lat": 28.5804,
        "lng": 77.0583,
        "tags": ["Pothole", "Road Hazard", "Asphalt Damage"],
        "dept": "Municipal Roads",
        "priority": 4,
        "description": "A deep, dangerous pothole near Sector 10 Dwarka metro station, causing vehicles to swerve suddenly.",
        "city": "Delhi"
    },
    {
        "filename": "delhi_pothole_chandni.jpg",
        "url": "https://images.unsplash.com/photo-1576086213369-97a306d36557?q=80&w=800",
        "lat": 28.6562,
        "lng": 77.2309,
        "tags": ["Pothole", "Pedestrian Hazard"],
        "dept": "Municipal Roads",
        "priority": 3,
        "description": "Deep asphalt cavity in the walking path near Chandni Chowk bazaar, representing a pedestrian trip hazard.",
        "city": "Delhi"
    },
    {
        "filename": "delhi_garbage_cp.jpg",
        "url": "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?q=80&w=800",
        "lat": 28.6304,
        "lng": 77.2177,
        "tags": ["Garbage Dump", "Litter", "Public Space"],
        "dept": "Solid Waste",
        "priority": 3,
        "description": "Overflowing waste and scattered plastic wrapping on a sidewalk block in Connaught Place inner circle.",
        "city": "Delhi"
    },
    {
        "filename": "delhi_garbage_karol.jpg",
        "url": "https://images.unsplash.com/photo-1530587191325-3db32d826c18?q=80&w=800",
        "lat": 28.6444,
        "lng": 77.1873,
        "tags": ["Garbage Dump", "Public Health", "Stray Animals"],
        "dept": "Solid Waste",
        "priority": 4,
        "description": "A large pile of unsorted household garbage dumped near Karol Bagh market area attracting street animals.",
        "city": "Delhi"
    },
    {
        "filename": "delhi_streetlight_rohini.jpg",
        "url": "https://images.unsplash.com/photo-1509021436665-8f07dbf5bf1d?q=80&w=800",
        "lat": 28.7282,
        "lng": 77.1215,
        "tags": ["Broken Streetlight", "Dark Spot", "Public Safety"],
        "dept": "Utility Streetlighting",
        "priority": 3,
        "description": "Shattered street lighting post near a green belt in Rohini Sector 11, leaving the lane completely dark at night.",
        "city": "Delhi"
    },
    {
        "filename": "delhi_waterlogging_okhla.jpg",
        "url": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=800",
        "lat": 28.5355,
        "lng": 77.2739,
        "tags": ["Waterlogging", "Stagnant Water", "Drain Blockage"],
        "dept": "Water & Sanitation",
        "priority": 5,
        "description": "Severe water clogging under the Okhla flyover subway blocking traffic lanes and raising hygiene concerns.",
        "city": "Delhi"
    },
    {
        "filename": "delhi_sewage_indiagate.jpg",
        "url": "https://images.unsplash.com/photo-1616401784845-180882ba9ba8?q=80&w=800",
        "lat": 28.6129,
        "lng": 77.2295,
        "tags": ["Blocked Sewage", "Wastewater Spill"],
        "dept": "Water & Sanitation",
        "priority": 4,
        "description": "Overflowing sewer manhole leaking dirty black water and spreading foul odor along the boulevard near India Gate.",
        "city": "Delhi"
    },
    {
        "filename": "mumbai_garbage_andheri.jpg",
        "url": "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?q=80&w=800",
        "lat": 19.1200,
        "lng": 72.8277,
        "tags": ["Garbage Dump", "Illegal Dumping"],
        "dept": "Solid Waste",
        "priority": 3,
        "description": "Large garbage heap on the side of a busy commuter road in Andheri West, blocking the pedestrian walkway.",
        "city": "Mumbai"
    }
]

def download_images(upload_dir: Path):
    print("⏳ Downloading public-domain image files into uploads directory...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    
    for item in IMAGE_DATASET:
        dest_path = upload_dir / item["filename"]
        if dest_path.exists() and dest_path.stat().st_size > 1000:
            print(f"✅ Image already exists: {item['filename']} ({dest_path.stat().st_size} bytes)")
            continue
            
        print(f"📥 Fetching: {item['url']} -> {item['filename']}")
        try:
            req = urllib.request.Request(item["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response, open(dest_path, "wb") as out_file:
                out_file.write(response.read())
            print(f"   Done! ({dest_path.stat().st_size} bytes)")
        except Exception as e:
            print(f"❌ Failed to download {item['filename']}: {e}")

def seed_database():
    # 1. Prepare target directory
    base_dir = Path(__file__).parent
    upload_dir = base_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Fetch images
    download_images(upload_dir)
    
    # 3. Connect to database
    print("\n⚡ Initializing database tables...")
    init_db()
    
    print("🔌 Connecting to database to seed reports...")
    conn = get_db()
    cursor = conn.cursor()
    
    # Optional clean-up
    clean_old = input("Do you want to clear existing reports in the database first? (y/n) [n]: ").strip().lower()
    if clean_old == 'y':
        print("🧹 Cleaning old report records...")
        cursor.execute("DELETE FROM reports")
        cursor.execute("DELETE FROM leaderboard")
        conn.commit()

    # Seed Leaderboard Delhi Users
    delhi_users = [
        ("delhi.fixer@civicfix.org", "Delhi_Fixer", "https://api.dicebear.com/7.x/bottts/svg?seed=delhifixer", 210, 8),
        ("capital.clean@civicfix.org", "CapitalClean", "https://api.dicebear.com/7.x/bottts/svg?seed=capitalclean", 120, 5),
        ("shiva@civicfix.org", "Shiva_The_Fixer", "https://api.dicebear.com/7.x/bottts/svg?seed=shiva", 150, 6)
    ]
    
    print("🏆 Seeding leaderboard accounts...")
    for email, username, avatar, pts, reports_submitted in delhi_users:
        if hasattr(conn, "is_pg") and conn.is_pg:
            # Check conflict for postgres
            cursor.execute("SELECT email FROM leaderboard WHERE email = %s", (email,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO leaderboard (email, username, avatar_url, civic_points, reports_submitted) VALUES (%s, %s, %s, %s, %s)",
                    (email, username, avatar, pts, reports_submitted)
                )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO leaderboard (email, username, avatar_url, civic_points, reports_submitted) VALUES (?, ?, ?, ?, ?)",
                (email, username, avatar, pts, reports_submitted)
            )
            
    # Seed Reports
    print("📸 Seeding civic reports all over India/Delhi...")
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    
    for i, item in enumerate(IMAGE_DATASET):
        r_id = f"CF-DEL{100 + i}"
        
        # Verify file downloaded, else fallback to mock name
        img_file = item["filename"]
        local_img_path = upload_dir / img_file
        if not local_img_path.exists():
            print(f"⚠️ Image {img_file} download failed. Seeding record anyway.")
            db_image_path = json.dumps([f"/uploads/{img_file}"])
        else:
            import base64
            with open(local_img_path, "rb") as f:
                img_data = f.read()
            encoded = base64.b64encode(img_data).decode("utf-8")
            db_image_path = json.dumps([f"data:image/jpeg;base64,{encoded}"])
            
        tags_json = json.dumps(item["tags"])
        
        # Assign reporters
        reporter_email = "delhi.fixer@civicfix.org" if i % 2 == 0 else "capital.clean@civicfix.org"
        reporter_name = "Delhi_Fixer" if i % 2 == 0 else "CapitalClean"
        
        # Check if record already exists to prevent duplicate keys
        check_query = "SELECT 1 FROM reports WHERE id = ?"
        cursor.execute(check_query, (r_id,))
        if cursor.fetchone():
            print(f"⏭️ Skipping {r_id} (already exists)")
            continue
            
        insert_query = """
        INSERT INTO reports (
            id, latitude, longitude, image_path, tags, 
            department, priority, votes, status, created_at, updated_at, reporter_email, reporter_name, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(insert_query, (
            r_id, item["lat"], item["lng"], db_image_path, tags_json,
            item["dept"], item["priority"], 8 - item["priority"], "Pending", now_str, now_str,
            reporter_email, reporter_name, item["description"]
        ))
        print(f"🎉 Seeded {r_id} ({item['city']} - {item['dept']})")
        
    conn.commit()
    conn.close()
    print("\n⭐ Successfully seeded all datasets into the CivicFix database!")

if __name__ == "__main__":
    try:
        seed_database()
    except KeyboardInterrupt:
        print("\n🛑 Execution interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during database seeding: {e}")
        sys.exit(1)
