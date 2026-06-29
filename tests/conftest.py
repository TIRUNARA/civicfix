import os
import sys
from pathlib import Path

# Force the database module to use a separate test database file
# to prevent tests from wiping/polluting the development database.
test_db_path = str(Path(__file__).parent / "civicfix_test.db")
os.environ["DB_PATH"] = test_db_path

# Clean up test database if it exists from a previous run
if os.path.exists(test_db_path):
    try:
        os.remove(test_db_path)
    except Exception:
        pass
