# migrate.py (Version 2 - Fixes created_at issue)

import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# --- Database Setup (Copied from your database.py) ---
print("--- Starting Database Migration Script ---")
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL not found in .env file. Please check your configuration.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- The Migration Logic ---
def run_migration():
    db = SessionLocal()
    inspector = inspect(engine) # To check if tables/columns exist

    try:
        print("\nStep 1: Checking database connection...")
        db.execute(text("SELECT 1"))
        print("✅ Connection successful.")

        # --- Part 1: Modify the 'quizzes' table ---
        print("\nStep 2: Modifying the 'quizzes' table...")
        if not 'is_ai_generated' in [c['name'] for c in inspector.get_columns('quizzes')]:
            db.execute(text("ALTER TABLE quizzes ADD COLUMN is_ai_generated BOOLEAN DEFAULT FALSE NOT NULL"))
            print("  - Added 'is_ai_generated' column to 'quizzes' table.")
        else:
            print("  - 'is_ai_generated' column already exists. Skipping.")

        # --- FIX IS HERE ---
        if not 'created_at' in [c['name'] for c in inspector.get_columns('quizzes')]:
            # Use TIMESTAMPTZ for PostgreSQL for timezone-aware timestamps
            db.execute(text("ALTER TABLE quizzes ADD COLUMN created_at TIMESTAMPTZ")) # <-- NEW LINE
            print("  - Added 'created_at' column to 'quizzes' table.") # <-- NEW LINE
        else:
            print("  - 'created_at' column already exists. Skipping.")
        # --- END FIX ---

        # Set existing manual quizzes correctly
        db.execute(text("UPDATE quizzes SET is_ai_generated = FALSE WHERE is_ai_generated IS NULL"))
        print("  - Ensured all existing quizzes are marked as 'manual' (is_ai_generated = false).")


        # --- Part 2: Migrate AI Quizzes ---
        print("\nStep 3: Migrating data from 'ai_quizzes' to 'quizzes'...")
        if not inspector.has_table('ai_quizzes'):
             print("  - 'ai_quizzes' table not found. Nothing to migrate. Skipping.")
        else:
            # Fetch all AI quizzes
            ai_quizzes = db.execute(text("SELECT id, title, chapter_id, created_at FROM ai_quizzes")).fetchall()
            print(f"  - Found {len(ai_quizzes)} AI-generated quizzes to migrate.")

            if len(ai_quizzes) > 0:
                for old_quiz in ai_quizzes:
                    old_quiz_id = old_quiz[0]
                    print(f"\n  Migrating AI Quiz ID: {old_quiz_id}, Title: '{old_quiz[1]}'")

                    # Insert into the main quizzes table and get the new ID
                    insert_quiz_sql = text("""
                        INSERT INTO quizzes (title, chapter_id, created_at, is_ai_generated)
                        VALUES (:title, :chapter_id, :created_at, TRUE)
                        RETURNING id
                    """)
                    result = db.execute(insert_quiz_sql, {
                        'title': old_quiz[1],
                        'chapter_id': old_quiz[2],
                        'created_at': old_quiz[3]
                    })
                    new_quiz_id = result.scalar_one()
                    print(f"    - Copied to 'quizzes' table with new ID: {new_quiz_id}")

                    # --- Part 3: Migrate AI Questions for this Quiz ---
                    ai_questions = db.execute(text("SELECT id, question_text, marks, question_type FROM ai_questions WHERE quiz_id = :old_id"), {'old_id': old_quiz_id}).fetchall()
                    print(f"    - Found {len(ai_questions)} questions to migrate for this quiz.")

                    for old_question in ai_questions:
                        old_question_id = old_question[0]

                        # Insert into the main questions table
                        insert_question_sql = text("""
                            INSERT INTO questions (question_text, quiz_id, marks, question_type)
                            VALUES (:text, :quiz_id, :marks, :type)
                            RETURNING id
                        """)
                        result = db.execute(insert_question_sql, {
                            'text': old_question[1],
                            'quiz_id': new_quiz_id,
                            'marks': old_question[2],
                            'type': old_question[3]
                        })
                        new_question_id = result.scalar_one()
                        print(f"      - Question copied to 'questions' table with new ID: {new_question_id}")

                        # --- Part 4: Migrate AI Options for this Question ---
                        ai_options = db.execute(text("SELECT option_text, is_correct FROM ai_options WHERE question_id = :old_id"), {'old_id': old_question_id}).fetchall()
                        for old_option in ai_options:
                            insert_option_sql = text("""
                                INSERT INTO options (question_id, option_text, is_correct)
                                VALUES (:q_id, :text, :correct)
                            """)
                            db.execute(insert_option_sql, {
                                'q_id': new_question_id,
                                'text': old_option[0],
                                'correct': old_option[1]
                            })
                        print(f"      - Copied {len(ai_options)} options for this question.")

        # Commit all the changes at once
        print("\nStep 4: Committing all changes to the database...")
        db.commit()
        print("✅ Commit successful.")
        print("\n--- MIGRATION COMPLETE ---")
        print("All AI quizzes, questions, and options have been copied to the main tables.")
        print("The old 'ai_quizzes', 'ai_questions', 'ai_options' tables still exist as a backup.")
        print("You can verify the data and delete them manually later when you are confident.")

    except Exception as e:
        print("\n❌ AN ERROR OCCURRED. Rolling back all changes.")
        print(f"Error details: {e}")
        db.rollback()
    finally:
        db.close()
        print("\n--- Script finished. Database connection closed. ---")

if __name__ == "__main__":
    run_migration()