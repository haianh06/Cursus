BEGIN;
DELETE FROM enrollments WHERE student_id = 'student_01' AND (section_id LIKE 'section_mock_%' OR section_id = 'section_gate2_ssa101_se_k20');
DELETE FROM weekly_reflections WHERE student_id = 'student_01';
DELETE FROM weekly_plans WHERE student_id = 'student_01';
INSERT INTO weekly_plans (id,student_id,week_number,goals,study_hours_allocated) VALUES
('plan_demo_w1','student_01',1,'{"statement":"Establish a consistent study routine across CSI, CEA, PRF and PRO."}',10),
('plan_demo_w2','student_01',2,'{"statement":"Complete CEA architecture lab and review feedback."}',12),
('plan_demo_w3','student_01',3,'{"statement":"Prepare CEA knowledge check and submit Week 3 lab."}',12);
INSERT INTO daily_plans (id,weekly_plan_id,date,status)
SELECT 'day_'||p.id||'_'||d,p.id,('2026-08-10'::date + ((p.week_number-1)*7+d-1))::timestamp,CASE WHEN p.week_number=3 THEN 'IN_PROGRESS' ELSE 'COMPLETED' END FROM weekly_plans p CROSS JOIN generate_series(1,5) d WHERE p.student_id='student_01';
INSERT INTO schedule_blocks (id,daily_plan_id,start_time,end_time,activity_description)
SELECT 'block_'||dp.id,dp.id,dp.date+interval '19 hours',dp.date+interval '20 hours 30 minutes','Focused study session' FROM daily_plans dp JOIN weekly_plans p ON p.id=dp.weekly_plan_id WHERE p.student_id='student_01';
INSERT INTO study_tasks (id,schedule_block_id,assignment_id,title,planned_minutes,actual_minutes,priority,status,difficulty,rescheduled_count)
SELECT 'task_'||b.id,b.id,'asg_w3_sec_CEA201_SE2001','CEA201 review and lab preparation',90,CASE WHEN p.week_number<3 THEN 80 ELSE NULL END,'HIGH',CASE WHEN p.week_number<3 THEN 'COMPLETED' ELSE 'TODO' END,'MEDIUM',0 FROM schedule_blocks b JOIN daily_plans d ON d.id=b.daily_plan_id JOIN weekly_plans p ON p.id=d.weekly_plan_id WHERE p.student_id='student_01';
INSERT INTO weekly_reflections (id,student_id,week_number,content,generated_at,metrics) VALUES
('reflection_demo_w1','student_01',1,'Week 1: established a realistic evening study routine and completed the core tasks.','2026-08-16 20:00','{"completionRate":0.9}'),
('reflection_demo_w2','student_01',2,'Week 2: the CEA lab took longer than expected; I will start revision earlier in Week 3.','2026-08-23 20:00','{"completionRate":0.75}');
UPDATE users SET share_reflection_summary=true WHERE id='student_01';
COMMIT;
