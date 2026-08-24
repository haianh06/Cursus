import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Clock, Sparkles } from 'lucide-react';
import { SkeletonRows } from '../shared/Skeleton';
import ProvenanceBadge from '../shared/ProvenanceBadge';
import DeferTaskDialog from './DeferTaskDialog';
import Timetable from './Timetable';
import { useGate2 } from '../../context/Gate2Context';
import { useLanguage } from '../../context/LanguageContext';
import { isToday } from '../../lib/dates.js';
import { requestCompanionReminder } from '../../lib/companionChatBus';

const STATUS_LABEL = {
  vi: { COMPLETED: 'Hoàn thành', IN_PROGRESS: 'Đang làm', DEFERRED: 'Đã dời' },
  en: { COMPLETED: 'Completed', IN_PROGRESS: 'In progress', DEFERRED: 'Deferred' },
};

function formatMinutes(minutes, lang) {
  if (!minutes && minutes !== 0) return '—';
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest}${lang === 'vi' ? ' phút' : 'm'}`;
  if (rest === 0) return `${hours}${lang === 'vi' ? ' giờ' : 'h'}`;
  return `${hours}h${String(rest).padStart(2, '0')}`;
}

/* ── One row of the today checklist — start/complete/defer the real task ── */
function TodayTaskRow({ task, onStart, onComplete, onDefer, busy, lang }) {
  const done = task.status === 'COMPLETED';
  const deferred = task.status === 'DEFERRED';
  return (
    <li
      className={`p-3 rounded-xl border border-line flex items-start justify-between gap-3 ${
        done ? 'opacity-60' : 'bg-surface-card'
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`text-[13px] font-semibold ${done ? 'line-through text-fg-muted' : 'text-fg'}`}
          >
            {task.title}
          </span>
          {(done || deferred) && (
            <span
              className={`badge text-[10px] ${deferred ? 'bg-warning-soft text-warning' : 'bg-success-soft text-success'}`}
            >
              {STATUS_LABEL[lang === 'vi' ? 'vi' : 'en'][task.status]}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="flex items-center gap-1 text-[11px] text-fg-muted">
            <Clock size={10} /> {formatMinutes(task.estimatedMinutes, lang)}
          </span>
          <ProvenanceBadge sourceType="ai_suggested" lang={lang} size="xs" />
        </div>
        {task.sourceLabel && (
          <p className="text-[10px] mt-1 italic text-fg-muted">
            {lang === 'vi' ? 'Nguồn: ' : 'Source: '}
            {task.sourceLabel}
          </p>
        )}
      </div>

      {!done && !deferred && (
        <div className="flex gap-1.5 shrink-0">
          {task.status === 'IN_PROGRESS' ? (
            <button
              type="button"
              className="btn btn-accent text-[11px] px-2.5 min-h-9 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
              onClick={() => onComplete(task)}
              disabled={busy}
            >
              {lang === 'vi' ? 'Xong' : 'Done'}
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-outline text-[11px] px-2.5 min-h-9 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
              onClick={() => onStart(task)}
              disabled={busy}
            >
              {lang === 'vi' ? 'Bắt đầu' : 'Start'}
            </button>
          )}
          <button
            type="button"
            className="btn-ghost text-[11px] px-2 min-h-9 rounded-lg cursor-pointer disabled:opacity-50 text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={() => onDefer(task)}
            disabled={busy}
          >
            {lang === 'vi' ? 'Dời' : 'Defer'}
          </button>
        </div>
      )}
    </li>
  );
}

/**
 * "Kế hoạch hôm nay" — the day-focused counterpart to the weekly Home/Planner
 * screens. Left: the real hour-by-hour calendar (`Timetable`, defaulted to
 * its existing "day" view — classes + self-study blocks, unchanged data).
 * Right: a checklist of today's real StudyTasks (same start/complete/defer
 * actions as everywhere else in Gate2). On first load, if there are open
 * tasks due today, it asks the floating companion chat to proactively
 * surface a reminder (see lib/companionChatBus.js) — real task data, not a
 * scripted chat line.
 */
export default function TodayPlanScreen() {
  const { lang } = useLanguage();
  const { tasks, deferReasons, loading, mutating, startTask, completeTask, deferTask } = useGate2();
  const [deferTarget, setDeferTarget] = useState(null);
  const [actionError, setActionError] = useState(null);
  const remindedRef = useRef(false);

  const todayTasks = useMemo(
    () => (tasks || []).filter((task) => isToday(task.scheduledDate)),
    [tasks],
  );

  useEffect(() => {
    if (loading || remindedRef.current) return;
    remindedRef.current = true;
    const openTasks = todayTasks.filter(
      (task) => task.status !== 'COMPLETED' && task.status !== 'DEFERRED',
    );
    if (openTasks.length > 0) {
      requestCompanionReminder({
        tasks: openTasks.slice(0, 3).map((task) => ({
          id: task.id,
          title: task.title,
          estimatedMinutes: task.estimatedMinutes,
        })),
      });
    }
  }, [loading, todayTasks]);

  const run = async (fn) => {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(err);
    }
  };

  const handleDeferConfirm = async (reasonCode, note) => {
    await run(() => deferTask(deferTarget.id, reasonCode, note));
    setDeferTarget(null);
  };

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 animate-fade-up w-full max-w-[1440px] mx-auto">
      <header>
        <h1 className="font-display text-2xl font-bold text-fg">
          {lang === 'vi' ? 'Kế hoạch hôm nay' : "Today's plan"}
        </h1>
        <p className="text-[13px] mt-1 text-fg-secondary">
          {lang === 'vi'
            ? 'Lịch chi tiết theo giờ và danh sách việc cần làm hôm nay.'
            : "Your hour-by-hour schedule and today's checklist."}
        </p>
      </header>

      {actionError && (
        <div
          role="alert"
          className="rounded-xl p-3.5 text-[13px] flex items-start gap-2 bg-danger-soft text-danger"
        >
          <span>{actionError.message}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <section className="lg:col-span-3 min-w-0" aria-label={lang === 'vi' ? 'Lịch hôm nay' : "Today's schedule"}>
          <Timetable initialView="day" />
        </section>

        <section
          className="lg:col-span-2 flex flex-col gap-3"
          aria-label={lang === 'vi' ? 'Việc cần làm hôm nay' : "Today's checklist"}
        >
          <h2 className="text-[15px] font-bold font-display text-fg">
            {lang === 'vi' ? 'Việc cần làm hôm nay' : "Today's checklist"}
          </h2>
          {loading ? (
            <SkeletonRows count={3} rowClassName="h-20 rounded-xl" />
          ) : todayTasks.length === 0 ? (
            <div className="card p-6 text-center">
              <Sparkles size={22} className="mx-auto mb-2 text-fg-muted" />
              <p className="text-[12px] text-fg-muted">
                {lang === 'vi'
                  ? 'Không có việc nào được lên lịch cho hôm nay.'
                  : 'Nothing scheduled for today.'}
              </p>
            </div>
          ) : (
            <ul className="space-y-2">
              {todayTasks.map((task) => (
                <TodayTaskRow
                  key={task.id}
                  task={task}
                  onStart={(item) => run(() => startTask(item.id))}
                  onComplete={(item) => run(() => completeTask(item.id, item.estimatedMinutes))}
                  onDefer={setDeferTarget}
                  busy={mutating}
                  lang={lang}
                />
              ))}
            </ul>
          )}
        </section>
      </div>

      <DeferTaskDialog
        task={deferTarget}
        reasons={deferReasons}
        onCancel={() => setDeferTarget(null)}
        onConfirm={handleDeferConfirm}
        busy={mutating}
        lang={lang}
      />
    </div>
  );
}
