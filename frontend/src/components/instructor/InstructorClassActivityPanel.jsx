import React, { useCallback, useEffect, useState } from 'react';
import { CalendarClock, Trash2 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  createClassActivity,
  deleteClassActivity,
  getInstructorDashboard,
  listClassActivities,
  userFacingApiError,
} from '../../lib/api';

const KINDS = [
  { id: 'ASSIGNMENT', labelKey: 'instructor.kindAssignment' },
  { id: 'PROGRESS_TEST', labelKey: 'instructor.kindProgressTest' },
  { id: 'LAB', labelKey: 'instructor.kindLab' },
  { id: 'OTHER', labelKey: 'instructor.kindOther' },
];

const STATUS_KEYS = {
  scheduled: 'common.activityStatusScheduled',
  open: 'common.activityStatusOpen',
  closed: 'common.activityStatusClosed',
};

function formatDateTimeLabel(iso) {
  if (!iso) return '';
  return iso.replace('T', ' ').slice(0, 16);
}

export default function InstructorClassActivityPanel() {
  const { t, lang } = useLanguage();
  const [courses, setCourses] = useState([]);
  const [activities, setActivities] = useState([]);
  const [window_, setWindow] = useState(null);
  const [form, setForm] = useState({
    course_id: '',
    activity_date: '',
    kind: 'ASSIGNMENT',
    title: '',
    opens_at: '',
    closes_at: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const [dash, listed] = await Promise.all([
        getInstructorDashboard(),
        listClassActivities(),
      ]);
      setCourses(dash?.courses || []);
      setActivities(listed?.activities || []);
      setWindow(listed?.window || null);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.activityError'));
    }
  }, [lang, t]);

  useEffect(() => {
    load();
  }, [load]);

  const submit = async () => {
    if (!form.course_id || !form.activity_date) return;
    if (form.opens_at && form.closes_at && form.opens_at >= form.closes_at) {
      setError(t('instructor.activityWindowOrderError'));
      return;
    }
    setSaving(true);
    setError('');
    try {
      await createClassActivity({
        ...form,
        opens_at: form.opens_at || undefined,
        closes_at: form.closes_at || undefined,
      });
      setForm((prev) => ({ ...prev, activity_date: '', title: '', opens_at: '', closes_at: '' }));
      await load();
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.activityError'));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (activityId) => {
    setError('');
    try {
      await deleteClassActivity(activityId);
      await load();
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.activityError'));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="bg-surface-elevated border border-line rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-1 min-w-0">
          <h1 className="text-2xl font-black text-fg font-serif-heading">{t('instructor.activityTitle')}</h1>
          <p className="text-xs text-fg-muted font-medium">{t('instructor.activityHint')}</p>
        </div>
      </div>

      <div className="card p-6 space-y-4 text-left">
      <div className="flex items-center justify-between border-b border-line pb-3">
        <h2 className="text-base font-black text-fg flex items-center gap-2 font-serif-heading">
          <CalendarClock className="w-5 h-5 text-accent" />
          <span>{t('instructor.activityTitle')}</span>
        </h2>
      </div>
      {window_ && (
        <p className="text-[11px] text-slate-600 dark:text-slate-400 font-medium">
          {t('instructor.activityWindowHint', { start: window_.term_start, end: window_.last_activity_date })}
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <label className="block">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.activityCourse')}</span>
          <select
            className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={form.course_id}
            onChange={(event) => setForm((prev) => ({ ...prev, course_id: event.target.value }))}
          >
            <option value="">{t('instructor.activityCourse')}</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>{course.code} · {course.name}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.activityDate')}</span>
          <input
            type="date"
            min={window_?.term_start || undefined}
            max={window_?.last_activity_date || undefined}
            className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={form.activity_date}
            onChange={(event) => setForm((prev) => ({ ...prev, activity_date: event.target.value }))}
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.activityKind')}</span>
          <select
            className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={form.kind}
            onChange={(event) => setForm((prev) => ({ ...prev, kind: event.target.value }))}
          >
            {KINDS.map((kind) => (
              <option key={kind.id} value={kind.id}>{t(kind.labelKey)}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.activityTitleField')}</span>
          <input
            className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={form.title}
            onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.activityOpensAt')}</span>
          <input
            type="datetime-local"
            className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={form.opens_at}
            onChange={(event) => setForm((prev) => ({ ...prev, opens_at: event.target.value }))}
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.activityClosesAt')}</span>
          <input
            type="datetime-local"
            className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={form.closes_at}
            onChange={(event) => setForm((prev) => ({ ...prev, closes_at: event.target.value }))}
          />
        </label>
      </div>
      <button
        type="button"
        className="px-4 py-2 rounded-xl bg-accent hover:bg-accent-hover text-white text-sm font-black shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
        disabled={saving || !form.course_id || !form.activity_date}
        onClick={submit}
      >
        {t('instructor.activityAdd')}
      </button>
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-xl flex items-start gap-2" role="alert">
          <span className="text-[11px] font-bold text-red-900 dark:text-red-300">{error}</span>
        </div>
      )}
      {activities.length === 0 ? (
        <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
          {t('instructor.activityEmpty')}
        </div>
      ) : (
        <ul className="divide-y divide-line border border-line rounded-2xl max-h-[22rem] overflow-y-auto">
          {activities.map((item) => (
            <li key={item.id} className="px-3 py-2.5 flex items-center justify-between gap-3">
              <div>
                <p className="font-mono-code text-xs font-black text-accent flex items-center gap-2">
                  {item.course_code} · {item.kind_label}
                  {item.status && STATUS_KEYS[item.status] && (
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase font-mono-code ${
                        item.status === 'open'
                          ? 'bg-success-soft text-success-ink dark:bg-emerald-950/40 dark:text-emerald-300'
                          : item.status === 'closed'
                            ? 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                      }`}
                    >
                      {t(STATUS_KEYS[item.status])}
                    </span>
                  )}
                </p>
                <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">{item.activity_date} · {item.title}</p>
                {(item.opens_at || item.closes_at) && (
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 font-mono-code">
                    {t('instructor.activityWindowRange', {
                      opens: formatDateTimeLabel(item.opens_at),
                      closes: formatDateTimeLabel(item.closes_at),
                    })}
                  </p>
                )}
              </div>
              <button
                type="button"
                className="inline-flex items-center gap-1 text-xs font-bold text-danger-ink hover:text-red-800 dark:hover:text-red-300 cursor-pointer"
                onClick={() => remove(item.id)}
              >
                <Trash2 size={12} /> {t('instructor.activityDelete')}
              </button>
            </li>
          ))}
        </ul>
      )}
      </div>
    </div>
  );
}
