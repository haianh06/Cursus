import React, { useCallback, useEffect, useState } from 'react';
import { CalendarRange, Plus, Trash2, Save, GraduationCap } from 'lucide-react';
import {
  getActiveAcademicTerm,
  setActiveAcademicTerm,
  getCourseExams,
  upsertCourseExam,
  deleteCourseExam,
} from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';
import ConfirmDialog from '../shared/ConfirmDialog';

const EXAM_KINDS = ['MIDTERM', 'PROGRESS_TEST', 'FINAL'];

/**
 * Admin: active academic term (name, start date, study/exam weeks) +
 * course exam scheduling (midterm/final/progress-test sessions).
 *
 * Backend note: request bodies to /admin/academic-terms/active and
 * /admin/course-exams are camelCase, but the response payloads
 * (`AcademicTermOut`, `CourseExamOut`) are plain snake_case — this panel
 * reads snake_case fields off responses and sends camelCase in requests,
 * matching src/api/admin_schemas.py exactly (no populate_by_name alias
 * there, unlike practice.py/companion.py).
 */
export default function AdminAcademicPanel() {
  const { lang } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [term, setTerm] = useState(null);
  const [termForm, setTermForm] = useState({ name: '', startDate: '', studyWeeks: 10, examWeeks: 2 });
  const [savingTerm, setSavingTerm] = useState(false);

  const [courses, setCourses] = useState([]);
  const [exams, setExams] = useState([]);
  const [slots, setSlots] = useState([]);
  const [examForm, setExamForm] = useState({ courseId: '', kind: 'MIDTERM', sessions: [{ examDate: '', slotId: 1, label: '' }] });
  const [savingExam, setSavingExam] = useState(false);
  const [examError, setExamError] = useState(null);
  const [confirmDeleteExam, setConfirmDeleteExam] = useState(null); // exam object | null
  const [deletingExam, setDeletingExam] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const activeTerm = await getActiveAcademicTerm();
      setTerm(activeTerm);
      if (activeTerm) {
        setTermForm({
          name: activeTerm.name,
          startDate: activeTerm.start_date,
          studyWeeks: activeTerm.study_weeks,
          examWeeks: activeTerm.exam_weeks,
        });
      }
      try {
        const payload = await getCourseExams();
        setCourses(payload?.courses || []);
        setExams(payload?.exams || []);
        setSlots(payload?.slots || []);
      } catch (err) {
        if (err?.status !== 404) throw err;
        setCourses([]);
        setExams([]);
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSaveTerm = async () => {
    setSavingTerm(true);
    setError(null);
    try {
      const saved = await setActiveAcademicTerm(termForm);
      setTerm(saved);
      const payload = await getCourseExams();
      setCourses(payload?.courses || []);
      setExams(payload?.exams || []);
      setSlots(payload?.slots || []);
    } catch (err) {
      setError(err);
    } finally {
      setSavingTerm(false);
    }
  };

  const addSession = () =>
    setExamForm((prev) => ({ ...prev, sessions: [...prev.sessions, { examDate: '', slotId: 1, label: '' }] }));
  const updateSession = (idx, patch) =>
    setExamForm((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s, i) => (i === idx ? { ...s, ...patch } : s)),
    }));
  const removeSession = (idx) =>
    setExamForm((prev) => ({ ...prev, sessions: prev.sessions.filter((_, i) => i !== idx) }));

  const handleSaveExam = async () => {
    if (!examForm.courseId || examForm.sessions.length === 0) return;
    setSavingExam(true);
    setExamError(null);
    try {
      await upsertCourseExam(examForm);
      const payload = await getCourseExams();
      setExams(payload?.exams || []);
      setExamForm({ courseId: '', kind: 'MIDTERM', sessions: [{ examDate: '', slotId: 1, label: '' }] });
    } catch (err) {
      setExamError(err);
    } finally {
      setSavingExam(false);
    }
  };

  const handleDeleteExam = async (examId) => {
    setExamError(null);
    try {
      await deleteCourseExam(examId);
      setExams((prev) => prev.filter((e) => e.id !== examId));
    } catch (err) {
      setExamError(err);
    }
  };

  const confirmAndDeleteExam = async () => {
    if (!confirmDeleteExam) return;
    setDeletingExam(true);
    try {
      await handleDeleteExam(confirmDeleteExam.id);
      setConfirmDeleteExam(null);
    } finally {
      setDeletingExam(false);
    }
  };

  if (loading) {
    return <div className="card p-5 text-xs text-fg-muted">{lang === 'vi' ? 'Đang tải…' : 'Loading…'}</div>;
  }

  return (
    <div className="flex flex-col gap-6 text-left">
      {error && (
        <div className="p-3.5 rounded-xl bg-danger-soft border border-danger/20 text-xs text-danger">
          {error.message}
        </div>
      )}

      {/* Academic term */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <CalendarRange size={16} className="text-accent" />
          <h2 className="text-sm font-bold text-fg">{lang === 'vi' ? 'Học kỳ hiện hành' : 'Active academic term'}</h2>
          {term && <span className="badge badge-success text-[9px] font-bold uppercase">{lang === 'vi' ? 'Đang áp dụng' : 'Active'}</span>}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
          <div>
            <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{lang === 'vi' ? 'Tên học kỳ' : 'Name'}</label>
            <input className="input text-xs w-full" value={termForm.name} onChange={(e) => setTermForm((p) => ({ ...p, name: e.target.value }))} />
          </div>
          <div>
            <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{lang === 'vi' ? 'Ngày bắt đầu' : 'Start date'}</label>
            <input type="date" className="input text-xs w-full" value={termForm.startDate} onChange={(e) => setTermForm((p) => ({ ...p, startDate: e.target.value }))} />
          </div>
          <div>
            <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{lang === 'vi' ? 'Số tuần học' : 'Study weeks'}</label>
            <input type="number" min={1} max={20} className="input text-xs w-full" value={termForm.studyWeeks} onChange={(e) => setTermForm((p) => ({ ...p, studyWeeks: Number(e.target.value) }))} />
          </div>
          <div>
            <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{lang === 'vi' ? 'Số tuần thi' : 'Exam weeks'}</label>
            <input type="number" min={1} max={6} className="input text-xs w-full" value={termForm.examWeeks} onChange={(e) => setTermForm((p) => ({ ...p, examWeeks: Number(e.target.value) }))} />
          </div>
        </div>
        {term && (
          <p className="text-[11px] text-fg-muted mb-3">
            {lang === 'vi' ? 'Học kỳ' : 'Term'}: {term.start_date} → {term.end_date}
            {term.exam_start && ` · ${lang === 'vi' ? 'Thi' : 'Exams'}: ${term.exam_start} → ${term.exam_end}`}
          </p>
        )}
        <button
          type="button"
          className="btn btn-accent text-xs px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          disabled={!termForm.name.trim() || !termForm.startDate || savingTerm}
          onClick={handleSaveTerm}
        >
          <Save size={13} /> {savingTerm ? (lang === 'vi' ? 'Đang lưu…' : 'Saving…') : (lang === 'vi' ? 'Lưu học kỳ' : 'Save term')}
        </button>
      </div>

      {/* Course exams */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <GraduationCap size={16} className="text-accent" />
          <h2 className="text-sm font-bold text-fg">{lang === 'vi' ? 'Lịch thi theo môn' : 'Course exam schedule'}</h2>
        </div>

        {!term ? (
          <p className="text-xs text-fg-muted">{lang === 'vi' ? 'Cần thiết lập học kỳ trước.' : 'Set up the academic term first.'}</p>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <div>
                <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{lang === 'vi' ? 'Môn học' : 'Course'}</label>
                <select className="input text-xs w-full" value={examForm.courseId} onChange={(e) => setExamForm((p) => ({ ...p, courseId: e.target.value }))}>
                  <option value="">{lang === 'vi' ? 'Chọn môn' : 'Select course'}</option>
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{lang === 'vi' ? 'Loại kỳ thi' : 'Exam kind'}</label>
                <select className="input text-xs w-full" value={examForm.kind} onChange={(e) => setExamForm((p) => ({ ...p, kind: e.target.value }))}>
                  {EXAM_KINDS.map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-2 mb-3">
              {examForm.sessions.map((session, idx) => (
                <div key={idx} className="flex flex-wrap items-center gap-2 p-2 rounded-lg bg-surface-elevated border border-line">
                  <input type="date" className="input text-xs w-36" value={session.examDate} onChange={(e) => updateSession(idx, { examDate: e.target.value })} />
                  <select className="input text-xs w-40" value={session.slotId} onChange={(e) => updateSession(idx, { slotId: Number(e.target.value) })}>
                    {(slots.length ? slots : [1, 2, 3, 4, 5, 6].map((id) => ({ id }))).map((s) => (
                      <option key={s.id} value={s.id}>{s.start ? `${s.id} (${s.start}-${s.end})` : `Slot ${s.id}`}</option>
                    ))}
                  </select>
                  <input className="input text-xs flex-1 min-w-[100px]" placeholder={lang === 'vi' ? 'Ghi chú' : 'Label'} value={session.label} onChange={(e) => updateSession(idx, { label: e.target.value })} />
                  <button type="button" className="btn-ghost p-1.5 rounded-md hover:text-danger cursor-pointer" onClick={() => removeSession(idx)}>
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
              <button type="button" className="btn btn-outline text-xs px-3 py-1.5 rounded-lg cursor-pointer flex items-center gap-1.5" onClick={addSession}>
                <Plus size={13} /> {lang === 'vi' ? 'Thêm ca thi' : 'Add session'}
              </button>
            </div>

            {examError && <p className="text-[11px] text-danger mb-2">{examError.message}</p>}

            <button
              type="button"
              className="btn btn-accent text-xs px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              disabled={!examForm.courseId || savingExam}
              onClick={handleSaveExam}
            >
              <Save size={13} /> {savingExam ? (lang === 'vi' ? 'Đang lưu…' : 'Saving…') : (lang === 'vi' ? 'Lưu lịch thi' : 'Save exam')}
            </button>

            <div className="mt-4 overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    {[lang === 'vi' ? 'Môn' : 'Course', lang === 'vi' ? 'Loại' : 'Kind', lang === 'vi' ? 'Ca thi' : 'Sessions', ''].map((h) => (
                      <th key={h} scope="col">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {exams.map((exam) => (
                    <tr key={exam.id}>
                      <td className="font-bold text-fg">{exam.course_code || exam.course_id}</td>
                      <td>{exam.kind}</td>
                      <td className="text-fg-secondary">
                        {(exam.sessions || []).map((s) => `${s.exam_date} (slot ${s.slot_id})`).join(', ')}
                      </td>
                      <td className="text-right">
                        <button type="button" className="btn-ghost p-1.5 rounded-md hover:text-danger cursor-pointer" onClick={() => setConfirmDeleteExam(exam)}>
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {exams.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-4 text-center text-fg-muted">{lang === 'vi' ? 'Chưa có lịch thi.' : 'No exams scheduled.'}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <ConfirmDialog
        open={confirmDeleteExam}
        lang={lang}
        danger
        busy={deletingExam}
        title={lang === 'vi' ? 'Xoá lịch thi này?' : 'Delete this exam?'}
        message={
          lang === 'vi'
            ? `Xoá lịch thi ${confirmDeleteExam?.course_code || confirmDeleteExam?.course_id || ''} — task "Ôn thi" tự sinh cho sinh viên dựa trên lịch này có thể bị ảnh hưởng.`
            : `Delete the ${confirmDeleteExam?.course_code || confirmDeleteExam?.course_id || ''} exam schedule — auto-generated "Exam prep" tasks for students may be affected.`
        }
        confirmLabel={lang === 'vi' ? 'Xoá lịch thi' : 'Delete exam'}
        onCancel={() => setConfirmDeleteExam(null)}
        onConfirm={confirmAndDeleteExam}
      />
    </div>
  );
}
