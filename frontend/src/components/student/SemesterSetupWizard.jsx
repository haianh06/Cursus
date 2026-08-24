import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, Check, Plus, Trash2, Save, BookOpenCheck } from 'lucide-react';
import Skeleton from '../shared/Skeleton';
import {
  getSemesterCatalog,
  getSemesterStatus,
  listSemesters,
  getSemester,
  createSemester,
  updateSemester,
} from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

const MAX_COURSES = 8;
const SLOTS = [
  { id: 1, start: '07:30', end: '09:00' },
  { id: 2, start: '09:10', end: '10:40' },
  { id: 3, start: '10:50', end: '12:20' },
  { id: 4, start: '12:50', end: '14:20' },
  { id: 5, start: '14:30', end: '16:00' },
  { id: 6, start: '16:10', end: '17:40' },
];
const WEEKDAYS = [0, 1, 2, 3, 4];
const WEEKDAY_LABEL = {
  vi: ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6'],
  en: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
};

function slotKey(weekday, slotId) {
  return `${weekday}:${slotId}`;
}

/**
 * Additive, optional student semester setup: pick courses for the term,
 * paint them onto a weekly slot grid, and mark holiday/exam-week date-range
 * exceptions. Talks to `/api/v1/student/semesters/*`.
 *
 * Deliberately NOT wired as a gate in front of the rest of the student app —
 * the existing Gate2 demo flow (`Gate2Context`) already owns course/
 * assignment provisioning for the demo path and must keep working
 * untouched. This screen is reachable only via its own route
 * (`/student/semester-setup`); see App.jsx / report for the navigation
 * decision.
 */
export default function SemesterSetupWizard() {
  const { lang } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [semesterId, setSemesterId] = useState(null);
  const [step, setStep] = useState(0);

  const [name, setName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [slots, setSlots] = useState({});
  const [brushId, setBrushId] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [query, setQuery] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitOk, setSubmitOk] = useState(false);

  const applySemester = useCallback((row) => {
    setSemesterId(row.id);
    setName(row.name || '');
    setStartDate(row.start_date || '');
    setEndDate(row.end_date || '');
    setSelectedIds(Array.isArray(row.course_ids) ? row.course_ids : []);
    const nextSlots = {};
    (row.weekly_slots || []).forEach((slot) => {
      nextSlots[slotKey(slot.weekday, slot.slot_id)] = slot.course_id;
    });
    setSlots(nextSlots);
    setExceptions(row.exceptions || []);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [catalogPayload, status, list] = await Promise.all([
        getSemesterCatalog(),
        getSemesterStatus(),
        listSemesters(),
      ]);
      setCatalog(catalogPayload?.courses || []);
      const targetId = list?.active_id ?? status?.activeSemesterId ?? null;
      if (targetId) {
        const current = await getSemester(targetId);
        applySemester(current);
      }
    } catch (err) {
      setLoadError(err);
    } finally {
      setLoading(false);
    }
  }, [applySemester]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredCatalog = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return catalog;
    return catalog.filter((course) => `${course.code} ${course.name}`.toLowerCase().includes(needle));
  }, [catalog, query]);

  const courseById = useMemo(() => Object.fromEntries(catalog.map((c) => [c.id, c])), [catalog]);
  const selectedCourses = useMemo(() => catalog.filter((c) => selectedIds.includes(c.id)), [catalog, selectedIds]);
  const coursesValid = selectedIds.length >= 1 && selectedIds.length <= MAX_COURSES;

  const toggleCourse = (courseId) => {
    setSelectedIds((prev) => {
      if (prev.includes(courseId)) {
        setSlots((cur) => {
          const next = { ...cur };
          Object.entries(next).forEach(([k, id]) => {
            if (id === courseId) delete next[k];
          });
          return next;
        });
        if (brushId === courseId) setBrushId(null);
        return prev.filter((id) => id !== courseId);
      }
      if (prev.length >= MAX_COURSES) return prev;
      return [...prev, courseId];
    });
  };

  const paintCell = (weekday, slotId) => {
    if (!brushId) return;
    const key = slotKey(weekday, slotId);
    setSlots((prev) => {
      const next = { ...prev };
      if (next[key] === brushId) {
        delete next[key];
      } else {
        next[key] = brushId;
      }
      return next;
    });
  };

  const addException = () => {
    setExceptions((prev) => [...prev, { kind: 'HOLIDAY', start_date: startDate || '', end_date: startDate || '', label: '' }]);
  };
  const removeException = (idx) => setExceptions((prev) => prev.filter((_, i) => i !== idx));
  const updateException = (idx, patch) =>
    setExceptions((prev) => prev.map((item, i) => (i === idx ? { ...item, ...patch } : item)));

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);
    setSubmitOk(false);
    const weeklySlots = Object.entries(slots).map(([key, courseId]) => {
      const [weekday, slotIdStr] = key.split(':');
      return { weekday: Number(weekday), slot_id: Number(slotIdStr), course_id: courseId };
    });
    const payload = {
      name,
      startDate: startDate,
      endDate: endDate,
      courseIds: selectedIds,
      weeklySlots,
      exceptions: exceptions.map((e) => ({
        kind: e.kind,
        start_date: e.start_date,
        end_date: e.end_date,
        label: e.label || '',
      })),
    };
    try {
      const result = semesterId
        ? await updateSemester(semesterId, payload)
        : await createSemester(payload);
      setSemesterId(result.id);
      setSubmitOk(true);
    } catch (err) {
      setSubmitError(err);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-14 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 animate-fade-up max-w-5xl">
      <div className="flex items-center justify-between border-b pb-4 border-line">
        <div className="text-left">
          <h1 className="font-display text-xl font-bold text-fg flex items-center gap-2">
            <CalendarDays size={20} className="text-accent" />
            {lang === 'vi' ? 'Thiết lập học kỳ' : 'Semester setup'}
          </h1>
          <p className="text-xs text-fg-muted mt-1">
            {lang === 'vi'
              ? 'Chọn môn học, xếp lịch tuần và đánh dấu ngày nghỉ/kỳ thi cho học kỳ này. Tùy chọn — không bắt buộc.'
              : 'Pick courses, build your weekly schedule, and mark holidays/exam weeks. Optional, not required.'}
          </p>
        </div>
      </div>

      {loadError && (
        <div className="p-3.5 rounded-xl bg-danger-soft border border-danger/20 text-xs text-danger">
          {loadError.message}
        </div>
      )}

      {/* Step tabs */}
      <div className="flex gap-2">
        {['courses', 'slots', 'exceptions'].map((key, i) => (
          <button
            key={key}
            type="button"
            className={`px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-colors ${
              step === i ? 'bg-accent-cta text-white' : 'bg-surface-elevated text-fg-secondary hover:text-fg'
            }`}
            onClick={() => setStep(i)}
          >
            {i + 1}.{' '}
            {key === 'courses'
              ? lang === 'vi' ? 'Môn học & thời gian' : 'Courses & dates'
              : key === 'slots'
                ? lang === 'vi' ? 'Lịch tuần' : 'Weekly slots'
                : lang === 'vi' ? 'Ngày nghỉ' : 'Exceptions'}
          </button>
        ))}
      </div>

      {step === 0 && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label htmlFor="semester-name" className="block text-xs font-semibold text-fg-secondary mb-1.5">
                {lang === 'vi' ? 'Tên học kỳ' : 'Semester name'}
              </label>
              <input id="semester-name" className="input text-xs w-full" value={name} onChange={(e) => setName(e.target.value)} placeholder="HK1 2026" />
            </div>
            <div>
              <label htmlFor="semester-start-date" className="block text-xs font-semibold text-fg-secondary mb-1.5">
                {lang === 'vi' ? 'Ngày bắt đầu' : 'Start date'}
              </label>
              <input id="semester-start-date" type="date" className="input text-xs w-full" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <label htmlFor="semester-end-date" className="block text-xs font-semibold text-fg-secondary mb-1.5">
                {lang === 'vi' ? 'Ngày kết thúc' : 'End date'}
              </label>
              <input id="semester-end-date" type="date" className="input text-xs w-full" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>

          <input
            className="input text-xs w-full"
            placeholder={lang === 'vi' ? 'Tìm môn học…' : 'Search courses…'}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-72 overflow-y-auto">
            {filteredCatalog.map((course) => {
              const selected = selectedIds.includes(course.id);
              return (
                <button
                  key={course.id}
                  type="button"
                  onClick={() => toggleCourse(course.id)}
                  className={`text-left p-3 rounded-lg border cursor-pointer transition-colors flex items-center justify-between ${
                    selected ? 'border-accent bg-accent-soft' : 'border-line bg-surface-elevated hover:border-accent'
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block text-xs font-bold text-fg truncate">{course.code}</span>
                    <span className="block text-[11px] text-fg-muted truncate">{course.name}</span>
                  </span>
                  {selected && <Check size={14} className="text-accent shrink-0 ml-2" />}
                </button>
              );
            })}
          </div>
          <p className="text-[11px] text-fg-muted">
            {selectedIds.length}/{MAX_COURSES} {lang === 'vi' ? 'môn đã chọn' : 'courses selected'}
          </p>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3">
          <p className="text-xs text-fg-muted">
            {lang === 'vi' ? 'Chọn môn ở dưới rồi bấm vào ô lịch để gán.' : 'Pick a course below, then click grid cells to assign it.'}
          </p>
          <div className="flex flex-wrap gap-2">
            {selectedCourses.map((course) => (
              <button
                key={course.id}
                type="button"
                onClick={() => setBrushId(course.id === brushId ? null : course.id)}
                className={`text-[11px] px-2.5 py-1.5 rounded-lg border cursor-pointer font-bold ${
                  brushId === course.id ? 'border-accent bg-accent-cta text-white' : 'border-line bg-surface-elevated text-fg-secondary'
                }`}
              >
                {course.code}
              </button>
            ))}
            {selectedCourses.length === 0 && (
              <p className="text-[11px] text-fg-muted">
                {lang === 'vi' ? 'Chưa chọn môn nào ở bước 1.' : 'No courses selected in step 1 yet.'}
              </p>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr>
                  <th className="p-2 text-left text-[10px] text-fg-muted"></th>
                  {WEEKDAYS.map((wd) => (
                    <th key={wd} className="p-2 text-[10px] font-bold text-fg-muted">
                      {WEEKDAY_LABEL[lang === 'en' ? 'en' : 'vi'][wd]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SLOTS.map((slot) => (
                  <tr key={slot.id}>
                    <td className="p-2 text-[10px] text-fg-muted whitespace-nowrap">
                      {slot.start}–{slot.end}
                    </td>
                    {WEEKDAYS.map((wd) => {
                      const key = slotKey(wd, slot.id);
                      const assigned = slots[key];
                      const course = assigned ? courseById[assigned] : null;
                      return (
                        <td key={wd} className="p-1">
                          <button
                            type="button"
                            onClick={() => paintCell(wd, slot.id)}
                            disabled={!brushId && !assigned}
                            aria-label={`${WEEKDAY_LABEL[lang === 'en' ? 'en' : 'vi'][wd]}, ${slot.start}-${slot.end}, ${
                              course ? course.code : lang === 'vi' ? 'chưa gán môn' : 'unassigned'
                            }`}
                            className={`w-full h-12 rounded-md border text-[10px] font-bold cursor-pointer transition-colors ${
                              course ? 'border-accent bg-accent-soft text-accent-text-safe' : 'border-dashed border-line text-fg-muted hover:border-accent'
                            }`}
                          >
                            {course ? course.code : ''}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-fg-muted">
              {lang === 'vi' ? 'Ngày nghỉ / tuần thi trong khoảng học kỳ.' : 'Holidays / exam weeks within the semester range.'}
            </p>
            <button
              type="button"
              className="btn btn-outline text-xs px-3 py-1.5 rounded-lg cursor-pointer flex items-center gap-1.5"
              onClick={addException}
            >
              <Plus size={13} /> {lang === 'vi' ? 'Thêm' : 'Add'}
            </button>
          </div>
          {exceptions.length === 0 ? (
            <p className="text-[11px] text-fg-muted p-4 text-center border border-dashed border-line rounded-lg">
              {lang === 'vi' ? 'Chưa có mục nào.' : 'None yet.'}
            </p>
          ) : (
            <div className="space-y-2">
              {exceptions.map((item, idx) => (
                <div key={idx} className="flex flex-wrap items-center gap-2 p-2.5 rounded-lg border border-line bg-surface-elevated">
                  <select
                    className="input text-xs w-32"
                    value={item.kind}
                    onChange={(e) => updateException(idx, { kind: e.target.value })}
                  >
                    <option value="HOLIDAY">{lang === 'vi' ? 'Nghỉ lễ' : 'Holiday'}</option>
                    <option value="EXAM_WEEK">{lang === 'vi' ? 'Tuần thi' : 'Exam week'}</option>
                  </select>
                  <input
                    type="date"
                    className="input text-xs w-36"
                    value={item.start_date}
                    onChange={(e) => updateException(idx, { start_date: e.target.value })}
                  />
                  <input
                    type="date"
                    className="input text-xs w-36"
                    value={item.end_date}
                    onChange={(e) => updateException(idx, { end_date: e.target.value })}
                  />
                  <input
                    className="input text-xs flex-1 min-w-[120px]"
                    placeholder={lang === 'vi' ? 'Ghi chú' : 'Label'}
                    value={item.label}
                    onChange={(e) => updateException(idx, { label: e.target.value })}
                  />
                  <button
                    type="button"
                    className="btn-ghost p-1.5 rounded-md hover:text-danger cursor-pointer"
                    onClick={() => removeException(idx)}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {submitError && (
        <div className="p-3.5 rounded-xl bg-danger-soft border border-danger/20 text-xs text-danger">
          {submitError.message}
        </div>
      )}
      {submitOk && (
        <div className="p-3.5 rounded-xl bg-success-soft border border-success/20 text-xs text-success flex items-center justify-between gap-3 flex-wrap">
          <span>{lang === 'vi' ? 'Đã lưu học kỳ.' : 'Semester saved.'}</span>
          <Link
            to="/student/lecture-plan"
            className="btn btn-outline text-xs px-3 py-1.5 rounded-lg cursor-pointer flex items-center gap-1.5 shrink-0"
          >
            <BookOpenCheck size={13} />
            {lang === 'vi' ? 'Tạo kế hoạch tuần này' : 'Generate this week’s plan'}
          </Link>
        </div>
      )}

      <div className="flex items-center justify-end gap-2 border-t pt-4 border-line">
        <button
          type="button"
          className="btn btn-accent text-xs px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          disabled={!coursesValid || !name.trim() || !startDate || !endDate || submitting}
          onClick={handleSubmit}
        >
          <Save size={13} />
          {submitting
            ? lang === 'vi' ? 'Đang lưu…' : 'Saving…'
            : semesterId
              ? lang === 'vi' ? 'Cập nhật học kỳ' : 'Update semester'
              : lang === 'vi' ? 'Tạo học kỳ' : 'Create semester'}
        </button>
      </div>
    </div>
  );
}
