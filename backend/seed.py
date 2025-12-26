from app import create_app, db
from models.school import School
from models.class_model import Class
from models.teacher import Teacher
from models.student import Student
from models.subject import Subject

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    school = School(name="Echo High School")
    db.session.add(school)
    db.session.commit()

    c1 = Class(display_name="JSS 1A", level="JSS1", stream="A", school_id=school.id)
    db.session.add(c1)

    t1 = Teacher(first_name="John", last_name="Doe", school_id=school.id)
    db.session.add(t1)

    s1 = Student(first_name="Mary", last_name="Jane", school_id=school.id)
    db.session.add(s1)

    subj = Subject(
        name="Mathematics",
        class_id=c1.id,
        teacher_id=t1.id,
        school_id=school.id
    )

    db.session.add(subj)
    db.session.commit()

    print("✅ Database seeded successfully")
