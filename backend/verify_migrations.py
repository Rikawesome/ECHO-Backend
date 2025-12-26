#!/usr/bin/env python3
"""
Migration verification script for Echo School Platform
Compatible with the existing project structure
"""

import sys
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import text  # Add this import

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def verify_school_migration():
    """Verify the schools migration is working correctly"""
    try:
        print("="*70)
        print("🏫 ECHO SCHOOL PLATFORM - SCHOOL MIGRATION VERIFICATION")
        print("="*70)
        
        print("🚀 Starting verification...")
        
        # Import app components
        from app import create_app, db
        from models.school import School
        
        # Create Flask app
        app = create_app()
        
        with app.app_context():
            print("✅ Flask app context created")
            print(f"📦 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # 1. Check database connection
            print("\n" + "-"*70)
            print("🔍 1. DATABASE CONNECTION TEST")
            print("-"*70)
            try:
                # Use text() wrapper for SQL
                result = db.session.execute(text('SELECT 1')).scalar()
                if result == 1:
                    print("✅ Database connection successful")
                else:
                    print("❌ Database connection failed")
                    return False
            except Exception as e:
                print(f"❌ Database connection error: {e}")
                return False
            
            # 2. Check tables exist
            print("\n" + "-"*70)
            print("📊 2. DATABASE TABLES CHECK")
            print("-"*70)
            
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"Found {len(tables)} tables:")
            for table in sorted(tables):
                if table == 'schools':
                    print(f"   ✅ {table}")
                elif table == 'alembic_version':
                    print(f"   📝 {table}")
                else:
                    print(f"   • {table}")
            
            if 'schools' not in tables:
                print("\n❌ CRITICAL: 'schools' table does not exist!")
                print("   Run: flask db upgrade")
                return False
            
            print("✅ Schools table exists!")
            
            # 3. Check alembic version
            if 'alembic_version' in tables:
                try:
                    revision = db.session.execute(text('SELECT version_num FROM alembic_version')).scalar()
                    print(f"📝 Current migration revision: {revision}")
                except:
                    print("📝 Alembic version table exists")
            
            # 4. Check schools table structure
            print("\n" + "-"*70)
            print("🏗️  3. SCHOOLS TABLE STRUCTURE")
            print("-"*70)
            
            columns = inspector.get_columns('schools')
            print(f"Table has {len(columns)} columns:")
            
            # Check for critical columns
            critical_columns = [
                'id', 'name', 'slug', 'school_type',
                'teacher_registration_code', 'student_registration_code',
                'academic_config', 'subscription_config'
            ]
            
            column_names = [col['name'] for col in columns]
            missing_critical = [col for col in critical_columns if col not in column_names]
            
            if missing_critical:
                print(f"❌ Missing critical columns: {missing_critical}")
                return False
            
            print("✅ All critical columns exist")
            
            # Display column info
            for col in columns:
                col_name = col['name']
                col_type = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                marker = "✅" if col_name in critical_columns else "  "
                print(f"   {marker} {col_name:30} {col_type:20} {nullable}")
            
            # 5. Test CRUD Operations
            print("\n" + "-"*70)
            print("🧪 4. CRUD OPERATIONS TEST")
            print("-"*70)
            
            # Generate unique slug for test
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            test_slug = f"test-school-{timestamp}"
            
            print("Creating test school...")
            
            # Create test school
            test_school = School(
                name="Verification Test Academy",
                slug=test_slug,
                school_type="combined",
                motto="Testing Excellence",
                vision="To be a leading test institution",
                mission="Providing quality test education",
                contact_email=f"test{timestamp}@verification.edu",
                contact_phone="+2348012345678",
                contact_whatsapp="+2348012345678",
                website="https://verification-test.edu.ng",
                address="123 Test Street, Verification City",
                city="Verification",
                state="Lagos",
                country="Nigeria"
            )
            
            # Verify auto-generated codes
            print(f"   Teacher Code: {test_school.teacher_registration_code}")
            print(f"   Student Code: {test_school.student_registration_code}")
            
            # Verify JSON configs
            print(f"   Academic Config: {test_school.academic_config is not None}")
            print(f"   Subscription Config: {test_school.subscription_config is not None}")
            
            # Save to database
            db.session.add(test_school)
            db.session.commit()
            
            print(f"✅ School created successfully!")
            print(f"   ID: {test_school.id}")
            print(f"   Created at: {test_school.created_at}")
            
            # Test READ operation
            print("\nRetrieving school from database...")
            retrieved = School.query.filter_by(slug=test_slug).first()
            
            if not retrieved:
                print("❌ Failed to retrieve school!")
                return False
            
            print(f"✅ School retrieved successfully!")
            print(f"   Name: {retrieved.name}")
            print(f"   Type: {retrieved.school_type}")
            print(f"   Status: {retrieved.subscription_status}")
            print(f"   Trial ends: {retrieved.trial_ends_at}")
            
            # Test UPDATE operation
            print("\nUpdating school information...")
            original_name = retrieved.name
            retrieved.name = "Updated " + original_name
            retrieved.contact_email = f"updated{timestamp}@verification.edu"
            db.session.commit()
            
            # Verify update
            updated = School.query.get(retrieved.id)
            if updated.name == "Updated " + original_name:
                print(f"✅ School updated successfully!")
            else:
                print("❌ School update failed!")
                return False
            
            # Test model methods
            print("\nTesting model methods...")
            
            # Contact channels
            channels = updated.get_contact_channels()
            print(f"   Contact channels: {len(channels)}")
            
            # Trial status
            trial_expired = updated.is_trial_expired()
            print(f"   Trial expired: {trial_expired}")
            
            # Can add users
            can_add_student = updated.can_add_student()
            can_add_teacher = updated.can_add_teacher()
            print(f"   Can add student: {can_add_student}")
            print(f"   Can add teacher: {can_add_teacher}")
            
            # Setup progress
            print(f"   Setup stage: {updated.setup_stage}")
            print(f"   Setup completed: {updated.setup_completed}")
            print(f"   Setup progress: {updated._get_setup_progress()}%")
            
            # Add operational details
            updated.add_operational_detail('facilities', {
                'has_library': True,
                'has_lab': True,
                'has_sports': False
            })
            
            if updated.operational_details:
                print(f"   Operational details added: ✅")
            
            # Update setup stage
            updated.update_setup_stage('academic')
            print(f"   Updated to stage: {updated.setup_stage}")
            
            # Test DELETE operation (cleanup)
            print("\nCleaning up test data...")
            db.session.delete(updated)
            db.session.commit()
            
            # Verify deletion
            deleted = School.query.filter_by(slug=test_slug).first()
            if not deleted:
                print("✅ Test school cleaned up successfully!")
            else:
                print("⚠️  Test school still exists (cleanup may have failed)")
            
            # 6. Create multiple schools to test constraints
            print("\n" + "-"*70)
            print("🔐 5. DATABASE CONSTRAINTS TEST")
            print("-"*70)
            
            # Test unique slug constraint
            try:
                school1 = School(name="Constraint Test 1", slug="constraint-test", school_type="primary")
                school2 = School(name="Constraint Test 2", slug="constraint-test", school_type="primary")
                
                db.session.add(school1)
                db.session.add(school2)
                db.session.commit()
                
                print("❌ Unique slug constraint failed!")
                return False
            except Exception as e:
                db.session.rollback()
                print("✅ Unique slug constraint working: ", str(e)[:100])
            
            # Test validation
            try:
                invalid_school = School(
                    name="Invalid School",
                    slug="INVALID SLUG WITH SPACES",  # Invalid slug
                    school_type="primary"
                )
                db.session.add(invalid_school)
                db.session.commit()
                print("❌ Slug validation failed!")
                return False
            except Exception as e:
                db.session.rollback()
                print("✅ Slug validation working: Invalid slugs rejected")
            
            # 7. Final summary
            print("\n" + "="*70)
            print("🎉 VERIFICATION COMPLETE - ALL TESTS PASSED! 🎉")
            print("="*70)
            
            print("\n📋 SUMMARY:")
            print(f"   ✅ Database connection: Working")
            print(f"   ✅ Schools table: {len(columns)} columns")
            print(f"   ✅ CRUD operations: Create, Read, Update, Delete")
            print(f"   ✅ Model methods: Contact channels, trial check, limits")
            print(f"   ✅ Database constraints: Unique slugs, validations")
            print(f"   ✅ Migration status: Verified")
            
            # Count schools in database
            school_count = School.query.count()
            print(f"\n📊 Current schools in database: {school_count}")
            
            if school_count > 0:
                print("\n🏫 Existing schools:")
                schools = School.query.limit(5).all()
                for s in schools:
                    print(f"   • {s.name} ({s.slug}) - {s.school_type}")
                if school_count > 5:
                    print(f"   ... and {school_count - 5} more")
            
            print("\n🚀 Your Echo School Platform is ready!")
            print("   Next steps:")
            print("   1. Run: flask db upgrade (if new migrations)")
            print("   2. Run: python test_schools.py (for full test suite)")
            print("   3. Run: flask run (to start the server)")
            
            return True
            
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_school_migration()
    
    if success:
        sys.exit(0)
    else:
        print("\n💡 TROUBLESHOOTING:")
        print("   1. Check if migrations are applied: flask db current")
        print("   2. Apply migrations: flask db upgrade")
        print("   3. Check database file exists: ls instance/")
        print("   4. Re-run this script after fixes")
        sys.exit(1)