-- Attach the hosted Demo Student to the August 2026 academic calendar.
-- 2026-08-10 is a Monday, so 2026-08-24 through 2026-08-30 resolves to week 3.
BEGIN;

DELETE FROM semester_setups WHERE student_id = 'student_01';

INSERT INTO semester_setups
    (id, student_id, name, start_date, end_date, is_active, created_at)
VALUES
    ('semester_demo_student_01', 'student_01', 'Fall 2026 — Cursus Uni',
     DATE '2026-08-10', DATE '2026-10-18', TRUE, NOW());

INSERT INTO semester_courses (id, semester_id, course_id) VALUES
    ('semester_course_demo_csi', 'semester_demo_student_01', 'course_mock_csi106'),
    ('semester_course_demo_cea', 'semester_demo_student_01', 'course_mock_cea201'),
    ('semester_course_demo_prf', 'semester_demo_student_01', 'course_mock_prf192'),
    ('semester_course_demo_pro', 'semester_demo_student_01', 'PRO192');

-- A balanced weekly timetable for the four enrolled subjects.
INSERT INTO semester_week_slots (id, semester_id, weekday, slot_id, course_id) VALUES
    ('semester_slot_demo_csi', 'semester_demo_student_01', 0, 1, 'course_mock_csi106'),
    ('semester_slot_demo_cea', 'semester_demo_student_01', 1, 2, 'course_mock_cea201'),
    ('semester_slot_demo_prf', 'semester_demo_student_01', 2, 3, 'course_mock_prf192'),
    ('semester_slot_demo_pro', 'semester_demo_student_01', 3, 4, 'PRO192');

COMMIT;
