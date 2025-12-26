# test_import.py
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test importing from models package
try:
    from models import db, BaseModel, School
    print("✅ Successfully imported from models package:")
    print(f"   - db: {db}")
    print(f"   - BaseModel: {BaseModel}")
    print(f"   - School: {School}")
    
    # Test creating a School instance
    test_school = School(
        name="Test Academy",
        slug="test-academy",
        school_type="senior"
    )
    print(f"✅ Created School instance: {test_school}")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Current directory:", os.getcwd())
    print("Python path:", sys.path)
except Exception as e:
    print(f"❌ Error: {e}")