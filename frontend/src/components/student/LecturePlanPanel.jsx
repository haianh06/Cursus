import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpenCheck, RefreshCw, CalendarDays } from 'lucide-react';
import Skeleton from '../shared/Skeleton';
import { generateLecturePlan, getLatestLecturePlan } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Lecture-driven weekly plan: a second, independent plan-generation flow
 * built from the student's timetable (class + exam sessions), not from a
 * Gate2 assignment. Talks only to `/api/v1/student/lecture-plan/*`.
 *
 * Deliberately NOT part of Gate2's `Gate2Context`/`StudentHome` — reachable
 * only via its own route (`/student/lecture-plan`) and a link from
 * `SemesterSetupWizard`, same "additive, not gating" pattern as the wizard
 * itself. This keeps the Gate2 demo path fully untouched.
 */
export default function LecturePlanPanel() {
  const { lang } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [availableHours, setAvailableHours] = useState(6);

  const loadLatest = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getLatestLecturePlan();
      setPlan(data);
    } catch (err) {
      setError(err);
      setPlan(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLatest();
  }, [loadLatest]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateLecturePlan({ availableHours, language: lang === 'en' ? 'en' : 'vi' });
      setPlan(data);
    } catch (err) {
      setError(err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 animate-fade-up max-w-4xl">
      <div className="flex items-center justify-between border-b pb-4 border-line">
        <div className="text-left">
          <h1 className="font-display text-xl font-bold text-fg flex items-center gap-2">
            <BookOpenCheck size={20} className="text-accent" />
            {lang === 'vi' ? 'Kế hoạch theo lịch học' : 'Lecture-based weekly plan'}
          </h1>
          <p className="text-xs text-fg-muted mt-1">
            {lang === 'vi'
              ? 'Tạo việc ôn tập/luyện tập tự động từ lịch học và lịch thi trong học kỳ của bạn. Độc lập với kế hoạch bài tập ở Trang chủ.'
              : 'Auto-generate review/practice tasks from your semester timetable and exam schedule. Independent from the assignment plan on Home.'}
          </p>
        </div>
        <Link
          to="/student/planner"
          className="btn btn-outline text-xs px-3 py-1.5 rounded-lg cursor-pointer flex items-center gap-1.5 shrink-0"
        >
          <CalendarDays size={13} />
          {lang === 'vi' ? 'Sửa học kỳ' : 'Edit semester'}
        </Link>
      </div>

      <div className="flex flex-wrap items-end gap-3 p-4 rounded-xl border border-line bg-surface-elevated">
        <div>
          <label htmlFor="lecture-plan-available-hours" className="block text-xs font-semibold text-fg-secondary mb-1.5">
            {lang === 'vi' ? 'Số giờ rảnh trong tuần' : 'Available hours this week'}
          </label>
          <input
            id="lecture-plan-available-hours"
            type="number"
            min="0"
            max="80"
            step="0.5"
            className="input text-xs w-28"
            value={availableHours}
            onChange={(e) => setAvailableHours(Number(e.target.value) || 0)}
          />
        </div>
        <button
          type="button"
          className="btn btn-accent text-xs px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          disabled={generating}
          onClick={handleGenerate}
        >
          <RefreshCw size={13} className={generating ? 'animate-spin' : ''} />
          {generating
            ? lang === 'vi' ? 'Đang tạo…' : 'Generating…'
            : lang === 'vi' ? 'Tạo kế hoạch tuần này' : 'Generate this week’s plan'}
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-danger-soft border border-danger/20 text-xs text-danger">
          {error.message}
        </div>
      )}

      {loading ? (
        <Skeleton className="h-48 w-full rounded-2xl" />
      ) : plan ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-bold text-fg">{plan.goal}</p>
            <span className="text-[11px] text-fg-muted">
              {lang === 'vi' ? 'Tuần' : 'Week'} {plan.weekNumber} · {plan.weekStart}
            </span>
          </div>
          {plan.tasks.length === 0 ? (
            <p className="text-xs text-fg-muted p-4 text-center border border-dashed border-line rounded-lg">
              {lang === 'vi' ? 'Chưa có việc nào.' : 'No tasks yet.'}
            </p>
          ) : (
            <ul className="space-y-2">
              {plan.tasks.map((task) => (
                <li
                  key={task.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg border border-line bg-surface-elevated"
                >
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-fg truncate">{task.title}</p>
                    <p className="text-[11px] text-fg-muted">
                      {task.scheduledDate} · {task.estimatedMinutes} {lang === 'vi' ? 'phút' : 'min'}
                    </p>
                  </div>
                  <span className="text-[10px] font-bold uppercase text-fg-muted shrink-0">{task.priority}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <p className="text-xs text-fg-muted p-6 text-center border border-dashed border-line rounded-lg">
          {lang === 'vi'
            ? 'Chưa có kế hoạch nào cho tuần này. Bấm "Tạo kế hoạch tuần này" để bắt đầu.'
            : 'No plan for this week yet. Click "Generate this week’s plan" to start.'}
        </p>
      )}
    </div>
  );
}
