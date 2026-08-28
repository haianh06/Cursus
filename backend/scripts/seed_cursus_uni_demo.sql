-- Cursus Uni production demo reset/seed.  Keeps the official course catalog,
-- documents and document_chunks intact; all rows below are operational/demo data.
-- Timeline: W1 2026-08-10, W2 2026-08-17, W3 2026-08-24.
BEGIN;

-- Detach retained curriculum documents from deleted demo users first.
UPDATE documents SET validated_by = NULL, published_by = NULL;

-- Delete children before their owners.  The list deliberately excludes courses,
-- curriculum_versions, documents and document_chunks (the chatbot corpus).
DELETE FROM reminder_deliveries; DELETE FROM reminders; DELETE FROM progress_events;
DELETE FROM self_study_sessions; DELETE FROM study_tasks; DELETE FROM schedule_blocks;
DELETE FROM daily_plans; DELETE FROM replan_proposals; DELETE FROM weekly_plans;
DELETE FROM weekly_reflections; DELETE FROM semester_week_slots; DELETE FROM semester_exceptions;
DELETE FROM semester_courses; DELETE FROM calendar_events; DELETE FROM semester_setups;
DELETE FROM course_exam_session_students; DELETE FROM course_exam_sessions; DELETE FROM course_exams;
DELETE FROM submissions; DELETE FROM quiz_questions; DELETE FROM quizzes;
DELETE FROM rubric_criteria; DELETE FROM rubrics; DELETE FROM assignment_overrides; DELETE FROM assignments;
DELETE FROM instructor_interventions; DELETE FROM instructor_student_notes; DELETE FROM risk_signals;
DELETE FROM practice_set_decisions; DELETE FROM practice_items; DELETE FROM practice_sets;
DELETE FROM chat_messages; DELETE FROM chat_conversations; DELETE FROM chat_action_proposals;
DELETE FROM chat_briefing_impressions; DELETE FROM crisis_escalations;
DELETE FROM guardrail_events; DELETE FROM conversations; DELETE FROM messages;
DELETE FROM resource_access_events; DELETE FROM learning_goals; DELETE FROM data_requests;
DELETE FROM announcements; DELETE FROM admin_announcements; DELETE FROM class_activities;
DELETE FROM lessons; DELETE FROM modules; DELETE FROM enrollments; DELETE FROM course_sections;
DELETE FROM org_invites; DELETE FROM verification_tokens; DELETE FROM mfa_recovery_codes;
DELETE FROM mfa_totp_credentials; DELETE FROM mfa_trusted_devices; DELETE FROM sessions;
DELETE FROM audit_logs; DELETE FROM access_requests; DELETE FROM admin_settings;
DELETE FROM risk_policies; DELETE FROM guardrail_policy_versions; DELETE FROM guardrail_rules;
DELETE FROM mock_lms_sync_versions; DELETE FROM course_ingest_jobs;
DELETE FROM organization_memberships; DELETE FROM users;
DELETE FROM academic_terms;
INSERT INTO organizations (id, name, slug, kind, created_at)
VALUES ('org_cursus_demo', 'Cursus Uni', 'cursus-demo', 'sandbox', NOW())
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name, slug = EXCLUDED.slug, kind = EXCLUDED.kind;

-- Move the four official, pre-ingested courses into the demo tenant.  Their
-- original documents/chunks stay exactly as uploaded and remain RAG sources.
UPDATE courses SET organization_id = 'org_cursus_demo'
WHERE id IN ('course_mock_csi106', 'course_mock_cea201', 'course_mock_prf192', 'PRO192');

INSERT INTO users (id,email,password_hash,full_name,role,is_email_verified,is_active,created_at,organization_id,major,student_code,preferences)
VALUES
 ('user_demo_admin','admin@demo.com','$argon2id$v=19$m=65536,t=3,p=4$2+adiwcisSBCm7Z7w0KAMQ$G03ajIu4z4r9AX16uTC3rUelS/SxsJpNLaBIIoYGeFg','Cursus Uni Admin','ADMIN',true,true,NOW(),'org_cursus_demo',NULL,NULL,'{}'),
 ('user_demo_instructor','demo.instructor@cursusdemo.local','$argon2id$v=19$m=65536,t=3,p=4$2+adiwcisSBCm7Z7w0KAMQ$G03ajIu4z4r9AX16uTC3rUelS/SxsJpNLaBIIoYGeFg','Nguyễn Đức Chung','INSTRUCTOR',true,true,NOW(),'org_cursus_demo',NULL,NULL,'{}');

DO $$
DECLARE i int; cls text; first_names text[] := ARRAY['Minh','Anh','Khánh','Linh','Quang','Hà','Phúc','Trang','Đức','Thảo','Huy','Vy']; last_names text[] := ARRAY['Nguyễn','Trần','Lê','Phạm','Hoàng','Vũ','Đặng','Bùi','Đỗ','Hồ'];
BEGIN
 FOR i IN 1..60 LOOP
   cls := CASE WHEN i <= 20 THEN 'SE2001' WHEN i <= 40 THEN 'SE2002' ELSE 'SE2003' END;
   INSERT INTO users (id,email,password_hash,full_name,role,is_email_verified,is_active,created_at,organization_id,major,student_code,preferences)
   VALUES ('student_'||lpad(i::text,2,'0'), CASE WHEN i=1 THEN 'demo.student@cursusdemo.local' ELSE 'student'||lpad(i::text,2,'0')||'@cursusuni.demo' END,
     '$argon2id$v=19$m=65536,t=3,p=4$2+adiwcisSBCm7Z7w0KAMQ$G03ajIu4z4r9AX16uTC3rUelS/SxsJpNLaBIIoYGeFg',
     last_names[1+((i-1)%10)]||' '||first_names[1+((i-1)%12)]||' '||chr(65+((i*7)%25))||chr(65+((i*11)%25)), 'STUDENT',true,true,NOW()-interval '20 days','org_cursus_demo','Software Engineering',cls||lpad(i::text,2,'0'),'{}');
 END LOOP;
END $$;

INSERT INTO organization_memberships (id,user_id,organization_id,role,created_at)
SELECT 'mem_'||id,id,'org_cursus_demo',role,NOW() FROM users WHERE organization_id='org_cursus_demo';

INSERT INTO course_sections (id,course_id,instructor_id,term,section_code)
SELECT 'sec_'||c.code||'_'||s.code,c.id,CASE WHEN c.code='CEA201' THEN 'user_demo_instructor' ELSE NULL END,'Fall 2026',s.code
FROM courses c CROSS JOIN (VALUES ('SE2001'),('SE2002'),('SE2003')) AS s(code)
WHERE c.id IN ('course_mock_csi106','course_mock_cea201','course_mock_prf192','PRO192');

INSERT INTO enrollments (id,student_id,section_id,status,enrolled_at)
SELECT 'enr_'||u.id||'_'||cs.id,u.id,cs.id,'ENROLLED','2026-08-10'::timestamp
FROM users u JOIN course_sections cs ON cs.section_code=left(u.student_code,6)
WHERE u.role='STUDENT' AND u.organization_id='org_cursus_demo';

INSERT INTO academic_terms (id,organization_id,name,start_date,study_weeks,exam_weeks,is_active,created_at)
VALUES ('term_fall_2026','org_cursus_demo','Fall 2026','2026-08-10',10,2,true,NOW());

INSERT INTO assignments (id,section_id,title,description,due_date,max_points,assessment_type)
SELECT 'asg_w'||w||'_'||cs.id,cs.id,'CEA201 · Week '||w||' Architecture Lab','Apply the concepts from the official CEA201 syllabus and submit a concise lab report.',('2026-08-10'::date + ((w*7)-2)*interval '1 day' + interval '23 hours 59 minutes'),100,'LAB'
FROM course_sections cs CROSS JOIN generate_series(1,3) w WHERE cs.course_id='course_mock_cea201';

INSERT INTO quizzes (id,section_id,title,description,time_limit_minutes,due_date,max_points,created_by,is_published,opens_at)
SELECT 'quiz_w3_'||cs.id,cs.id,'CEA201 · Week 3 Knowledge Check','Short formative quiz based on the uploaded CEA201 materials.',20,'2026-08-29 23:59',10,'user_demo_instructor',true,'2026-08-25 08:00'
FROM course_sections cs WHERE cs.course_id='course_mock_cea201';

INSERT INTO quiz_questions (id,quiz_id,question_text,question_type,correct_answer,options,points,order_index)
SELECT 'qq1_'||id,id,'Which component coordinates instruction execution?','MULTIPLE_CHOICE','Control Unit','{"options":["Control Unit","Cache","ALU","Register File"]}',5,1 FROM quizzes;

INSERT INTO submissions (id,assignment_id,student_id,submitted_at,content,grading_status,grade,feedback,is_late)
SELECT 'sub_'||a.id||'_'||u.id,a.id,u.id,
 CASE WHEN right(u.id,2)::int % 10 < 2 AND a.id LIKE 'asg_w2%' THEN '2026-08-25 08:30'::timestamp ELSE a.due_date - interval '6 hours' END,
 '{"summary":"Demo submission linked to the assigned CEA201 lab."}',
 CASE WHEN a.id LIKE 'asg_w3%' THEN 'PENDING' ELSE 'GRADED' END,
 CASE WHEN a.id LIKE 'asg_w3%' THEN NULL ELSE 65 + (right(u.id,2)::int % 31) END,
 CASE WHEN a.id LIKE 'asg_w3%' THEN NULL ELSE 'Reviewed with actionable feedback.' END,
 right(u.id,2)::int % 10 < 2 AND a.id LIKE 'asg_w2%'
FROM assignments a JOIN enrollments e ON e.section_id=a.section_id JOIN users u ON u.id=e.student_id
WHERE a.id NOT LIKE 'asg_w3%' OR right(u.id,2)::int % 4 <> 0;

INSERT INTO risk_signals (id,student_id,section_id,assignment_id,risk_type,risk_level,triggered_rules,evidence,recommended_action,generated_at,resolved_at,resolution_type,policy_version,instructor_note)
SELECT 'risk_'||i,'student_'||lpad(i::text,2,'0'),'sec_CEA201_'||CASE WHEN i<=20 THEN 'SE2001' WHEN i<=40 THEN 'SE2002' ELSE 'SE2003' END,'asg_w2_sec_CEA201_'||CASE WHEN i<=20 THEN 'SE2001' WHEN i<=40 THEN 'SE2002' ELSE 'SE2003' END,
 CASE WHEN i%2=0 THEN 'LATE_SUBMISSION' ELSE 'WEEKLY_GOAL_FAILURE' END,CASE WHEN i IN (7,19,33) THEN 'HIGH' ELSE 'MEDIUM' END,'{"source":"week_1_2_activity"}','{"summary":"Neutral demo risk signal based on Week 1–2 learning activity."}','Review workload and agree on the next achievable step.','2026-08-26',CASE WHEN i IN (12,26) THEN '2026-08-27'::timestamp END,CASE WHEN i IN (12,26) THEN 'FOLLOW_UP_COMPLETED' END,NULL,CASE WHEN i IN (12,26) THEN 'Student confirmed an adjusted study plan.' END
FROM unnest(ARRAY[7,12,19,26,33,48]) AS i;

INSERT INTO admin_announcements (id,title,content,created_by,organization_id,created_at)
VALUES ('admin_notice_w3','Week 3 teaching update','Please review the Week 3 learner-risk queue before Friday.','user_demo_admin','org_cursus_demo','2026-08-25 08:00');

COMMIT;
