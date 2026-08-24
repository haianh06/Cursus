# Prompt: Nạp Toàn Bộ Dữ Liệu Sang Database Mới Trống

## Mục Tiêu
Chuyển toàn bộ dữ liệu từ database hiện tại sang một database mới hoàn toàn trống, duy trì toàn bộ quan hệ và tính toàn vẹn dữ liệu.

## Bước 1: Chuẩn Bị

### 1.1 Backup Database Hiện Tại
```bash
# Backup database SQLite hiện tại (nếu là SQLite)
cp data/test.db data/test.db.backup
cp data/test_auth.db data/test_auth.db.backup

# Hoặc nếu dùng PostgreSQL/MySQL:
pg_dump -U postgres database_name > backup.sql
```

### 1.2 Tạo Database Mới Trống
```bash
# SQLite: Xóa hoặc tạo file mới
rm data/test_new.db
# Hoặc tạo bằng script

# PostgreSQL/MySQL:
createdb new_database_name
# hoặc
mysql -u root -p -e "CREATE DATABASE new_database;"
```

## Bước 2: Chạy Migration Script

### 2.1 Tạo Migration Script Python

Tạo file: `scripts/migrate_all_data.py`

```python
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.models import Base
from db.connection import SessionLocal
# Import all models
from db.models import (
    User, AuthSession, Invitation, VerificationToken,
    MfaTotpCredential, MfaRecoveryCode, MfaTrustedDevice,
    AuditLog, CurriculumVersion, Program, Course, CourseSection,
    Enrollment, Module, Lesson, Document, DocumentChunk,
    Announcement, SemesterSetup, SemesterCourse, SemesterWeekSlot,
    SemesterException, AcademicTerm, CourseExam, CourseExamSession,
    CourseExamSessionStudent, ClassActivity, CalendarEvent,
    Assignment, AssignmentOverride, Quiz, QuizQuestion, Rubric,
    RubricCriterion, Submission, LearningGoal, WeeklyPlan, DailyPlan,
    ScheduleBlock, SelfStudySession, StudyTask, ReplanProposal,
    ProgressEvent, Reminder, ReminderDelivery, ResourceAccessEvent,
    Conversation, Message, RAGTrace, LLMUsageEvent, GuardrailEvent,
    GuardrailRule, AdminCourseOverride, CourseIngestJob, RiskPolicy,
    AdminSetting, WeeklyReflection, RiskSignal, InstructorIntervention,
    RAGEvaluationCase, RAGEvaluationResult, GuardrailEvaluationCase,
    GuardrailEvaluationResult, PracticeSet, PracticeItem
)

# ===== CONFIGURATION =====
SOURCE_DB_URL = "sqlite:///data/test.db"  # Database hiện tại
SOURCE_AUTH_DB_URL = "sqlite:///data/test_auth.db"  # Auth DB nếu có
TARGET_DB_URL = "sqlite:///data/test_new.db"  # Database mới

# Mapping các table từ auth DB sang main DB (nếu cần)
SOURCE_TO_TARGET_MAPPING = {
    "source_db": SOURCE_DB_URL,
    "target_db": TARGET_DB_URL,
}

# ===== CONFIGURATION END =====

class DatabaseMigrator:
    def __init__(self, source_url: str, target_url: str):
        self.source_engine = create_engine(source_url, echo=False)
        self.target_engine = create_engine(target_url, echo=False)
        self.source_session = Session(self.source_engine)
        self.target_session = Session(self.target_engine)
        self.migration_log = []
        
    def create_tables(self):
        """Tạo tất cả tables trong database mới"""
        print("[INFO] Tạo tất cả tables trong database mới...")
        try:
            Base.metadata.create_all(self.target_engine)
            print("[✓] Tất cả tables đã được tạo thành công")
            self.migration_log.append(f"{datetime.now()} - Tables created successfully")
        except Exception as e:
            print(f"[ERROR] Lỗi khi tạo tables: {e}")
            self.migration_log.append(f"{datetime.now()} - ERROR creating tables: {e}")
            raise
    
    def get_all_table_classes(self):
        """Lấy danh sách tất cả model classes"""
        return [
            User, AuthSession, Invitation, VerificationToken,
            MfaTotpCredential, MfaRecoveryCode, MfaTrustedDevice,
            AuditLog, CurriculumVersion, Program, Course, CourseSection,
            Enrollment, Module, Lesson, Document, DocumentChunk,
            Announcement, SemesterSetup, SemesterCourse, SemesterWeekSlot,
            SemesterException, AcademicTerm, CourseExam, CourseExamSession,
            CourseExamSessionStudent, ClassActivity, CalendarEvent,
            Assignment, AssignmentOverride, Quiz, QuizQuestion, Rubric,
            RubricCriterion, Submission, LearningGoal, WeeklyPlan, DailyPlan,
            ScheduleBlock, SelfStudySession, StudyTask, ReplanProposal,
            ProgressEvent, Reminder, ReminderDelivery, ResourceAccessEvent,
            Conversation, Message, RAGTrace, LLMUsageEvent, GuardrailEvent,
            GuardrailRule, AdminCourseOverride, CourseIngestJob, RiskPolicy,
            AdminSetting, WeeklyReflection, RiskSignal, InstructorIntervention,
            RAGEvaluationCase, RAGEvaluationResult, GuardrailEvaluationCase,
            GuardrailEvaluationResult, PracticeSet, PracticeItem
        ]
    
    def migrate_data(self):
        """Nạp tất cả dữ liệu từ source sang target"""
        table_classes = self.get_all_table_classes()
        
        for table_class in table_classes:
            try:
                print(f"[→] Đang nạp {table_class.__tablename__}...")
                
                # Lấy tất cả records từ source DB
                records = self.source_session.query(table_class).all()
                
                if not records:
                    print(f"    └─ Không có dữ liệu")
                    self.migration_log.append(f"{datetime.now()} - {table_class.__tablename__}: 0 records")
                    continue
                
                # Thêm vào target DB
                for record in records:
                    self.target_session.add(record)
                
                # Commit sau mỗi table
                self.target_session.commit()
                print(f"    └─ ✓ Nạp {len(records)} records thành công")
                self.migration_log.append(f"{datetime.now()} - {table_class.__tablename__}: {len(records)} records migrated")
                
            except IntegrityError as e:
                print(f"    └─ ⚠ Lỗi Foreign Key: {e}")
                self.target_session.rollback()
                self.migration_log.append(f"{datetime.now()} - {table_class.__tablename__}: INTEGRITY ERROR - {e}")
            except Exception as e:
                print(f"    └─ ✗ Lỗi: {e}")
                self.target_session.rollback()
                self.migration_log.append(f"{datetime.now()} - {table_class.__tablename__}: ERROR - {e}")
    
    def verify_migration(self):
        """Kiểm tra xem dữ liệu đã được nạp đúng không"""
        print("\n[INFO] Kiểm tra tính toàn vẹn dữ liệu...")
        
        table_classes = self.get_all_table_classes()
        all_match = True
        
        for table_class in table_classes:
            source_count = self.source_session.query(table_class).count()
            target_count = self.target_session.query(table_class).count()
            
            status = "✓" if source_count == target_count else "✗"
            print(f"  {status} {table_class.__tablename__}: Source={source_count}, Target={target_count}")
            
            if source_count != target_count:
                all_match = False
            
            self.migration_log.append(f"{datetime.now()} - {table_class.__tablename__}: Source count={source_count}, Target count={target_count}")
        
        print(f"\n[{'✓' if all_match else '✗'}] Kiểm tra tính toàn vẹn: {'THÀNH CÔNG' if all_match else 'CÓ SỰ KHÔNG PHÙ HỢP'}")
        return all_match
    
    def save_migration_log(self):
        """Lưu nhật ký migration"""
        with open('logs/migration.log', 'w') as f:
            f.write('\n'.join(self.migration_log))
        print(f"\n[INFO] Nhật ký migration đã lưu tại: logs/migration.log")
    
    def close(self):
        """Đóng kết nối database"""
        self.source_session.close()
        self.target_session.close()
        self.source_engine.dispose()
        self.target_engine.dispose()

def main():
    migrator = DatabaseMigrator(SOURCE_DB_URL, TARGET_DB_URL)
    
    try:
        # Bước 1: Tạo tables
        migrator.create_tables()
        
        # Bước 2: Nạp dữ liệu
        print("\n[INFO] Bắt đầu nạp dữ liệu...")
        migrator.migrate_data()
        
        # Bước 3: Kiểm tra
        print("\n")
        is_valid = migrator.verify_migration()
        
        # Bước 4: Lưu log
        migrator.save_migration_log()
        
        if is_valid:
            print("\n[✓] MIGRATION THÀNH CÔNG!")
            print(f"[INFO] Database mới đã sẵn sàng tại: {TARGET_DB_URL}")
        else:
            print("\n[⚠] MIGRATION CÓ CÁC VẤNĐỀ - VUI LÒNG KIỂM TRA LOG")
        
    except Exception as e:
        print(f"\n[✗] MIGRATION THẤT BẠI: {e}")
        migrator.save_migration_log()
    finally:
        migrator.close()

if __name__ == "__main__":
    main()
```

### 2.2 Chạy Migration Script

```bash
# Vào thư mục project
cd c:\Documents\AIinAction\Neural_Forge

# Chạy migration
python scripts/migrate_all_data.py

# Hoặc sử dụng Make command nếu có
make migrate-database
```

## Bước 3: Xử Lý Foreign Key Constraints

Nếu gặp lỗi Foreign Key, hãy tuân theo thứ tự sau khi nạp dữ liệu:

**Thứ tự ưu tiên (Independent → Dependent):**

1. **Users** - Base table
   - User
   - CurriculumVersion
   - Program

2. **Authentication & Security**
   - AuthSession
   - Invitation
   - VerificationToken
   - MfaTotpCredential
   - MfaRecoveryCode
   - MfaTrustedDevice
   - AuditLog

3. **Academic Structure**
   - Course
   - CourseSection
   - Module
   - Lesson
   - Document
   - DocumentChunk
   - Announcement

4. **Enrollment & Assessment**
   - Enrollment
   - Assignment
   - AssignmentOverride
   - Quiz
   - QuizQuestion
   - Rubric
   - RubricCriterion
   - Submission

5. **Academic Calendar**
   - AcademicTerm
   - CourseExam
   - CourseExamSession
   - CourseExamSessionStudent
   - ClassActivity
   - CalendarEvent

6. **Student Planning**
   - SemesterSetup
   - SemesterCourse
   - SemesterWeekSlot
   - SemesterException
   - WeeklyPlan
   - DailyPlan
   - ScheduleBlock
   - StudyTask
   - SelfStudySession

7. **Tracking & Events**
   - LearningGoal
   - ProgressEvent
   - ResourceAccessEvent
   - Reminder
   - ReminderDelivery
   - ReplanProposal

8. **Chat & Q&A**
   - Conversation
   - Message
   - RAGTrace
   - LLMUsageEvent
   - GuardrailEvent
   - GuardrailRule

9. **Risk Management**
   - RiskPolicy
   - RiskSignal
   - InstructorIntervention

10. **Admin & Configuration**
    - AdminSetting
    - AdminCourseOverride
    - CourseIngestJob

11. **Practice & Evaluation**
    - PracticeSet
    - PracticeItem
    - RAGEvaluationCase
    - RAGEvaluationResult
    - GuardrailEvaluationCase
    - GuardrailEvaluationResult

12. **Weekly Reflection** (phụ thuộc vào User)
    - WeeklyReflection

## Bước 4: Xác Thực Dữ Liệu

```python
# Script kiểm tra: scripts/validate_migration.py
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

def validate_database(db_url):
    """Kiểm tra database migration"""
    engine = create_engine(db_url)
    session = Session(engine)
    
    checks = {
        "Users": "SELECT COUNT(*) FROM users",
        "Enrollments": "SELECT COUNT(*) FROM enrollments",
        "Courses": "SELECT COUNT(*) FROM courses",
        "Messages": "SELECT COUNT(*) FROM messages",
        "Submissions": "SELECT COUNT(*) FROM submissions",
        "RiskSignals": "SELECT COUNT(*) FROM risk_signals",
    }
    
    print(f"[INFO] Kiểm tra database: {db_url}\n")
    
    for name, query in checks.items():
        try:
            result = session.execute(query).scalar()
            print(f"  ✓ {name}: {result} records")
        except Exception as e:
            print(f"  ✗ {name}: ERROR - {e}")
    
    session.close()

if __name__ == "__main__":
    validate_database("sqlite:///data/test_new.db")
```

## Bước 5: Sử Dụng Database Mới

```bash
# Cập nhật .env hoặc config để sử dụng database mới
# DATABASE_URL=sqlite:///data/test_new.db

# Hoặc rename database
mv data/test.db data/test.db.old
mv data/test_new.db data/test.db

# Chạy server với database mới
python src/main.py
```

## Bước 6: Backup & Cleanup

```bash
# Xác nhận migration thành công trước khi xóa
# Nếu thành công, có thể xóa backup cũ
rm data/test.db.old
rm data/test.db.backup
```

## Troubleshooting

### Lỗi 1: Foreign Key Constraint Violation
**Nguyên nhân:** Dữ liệu parent chưa được nạp
**Giải pháp:** Sử dụng thứ tự nạp dữ liệu đúng hoặc tạm thời vô hiệu hóa FK constraints

```python
# Tạm vô hiệu hóa FK constraints (SQLite)
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.close()
```

### Lỗi 2: Duplicate Key
**Nguyên nhân:** Dữ liệu trùng lặp
**Giải pháp:** Kiểm tra unique constraints, xóa records trùng trong source DB

### Lỗi 3: Memory Issues
**Nguyên nhân:** Database lớn
**Giải pháp:** Nạp dữ liệu theo batch, không load tất cả vào memory

```python
# Nạp theo batch
BATCH_SIZE = 1000
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i+BATCH_SIZE]
    for record in batch:
        target_session.add(record)
    target_session.commit()
```

## Kiểm Tra Cuối Cùng

- [ ] Backup database cũ
- [ ] Chạy migration script
- [ ] Xác minh record counts khớp
- [ ] Kiểm tra referential integrity
- [ ] Test các tính năng chính
- [ ] Xóa database cũ khi chắc chắn

## Notes

- Đảm bảo timestamp được giữ nguyên khi migrate
- Kiểm tra enum values khớp giữa old và new DB
- Verify metadata_info (JSON) được nạp chính xác
- Test RAG vectors/embeddings trong chroma DB nếu cần
