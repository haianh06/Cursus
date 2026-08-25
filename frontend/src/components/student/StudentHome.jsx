import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CalendarClock,
  CheckCheck,
  CheckCircle2,
  ChevronRight,
  Clock,
  FlaskConical,
  PlayCircle,
  RotateCcw,
  Target,
  TrendingUp,
  Zap,
} from 'lucide-react';
import Skeleton, { SkeletonRows } from '../shared/Skeleton';
import EmptyState from '../shared/EmptyState';
import ErrorState from '../shared/ErrorState';
import ProvenanceBadge from '../shared/ProvenanceBadge';
import SourceDrawer, { CitationChip } from '../shared/SourceDrawer';
import DeferTaskDialog from './DeferTaskDialog';
import CompleteTaskDialog from './CompleteTaskDialog';
import CuriContextPanel from './CuriContextPanel';
import { useGate2 } from '../../context/Gate2Context';
import { useLanguage } from '../../context/LanguageContext';
import { getTimeOfDay } from '../../lib/dates.js';

function formatMinutes(minutes, lang) {
  if (!minutes && minutes !== 0) return '—';
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest}${lang === 'vi' ? ' phút' : 'm'}`;
  if (rest === 0) return `${hours}${lang === 'vi' ? ' giờ' : 'h'}`;
  return `${hours}h${String(rest).padStart(2, '0')}`;
}

const STATUS_STYLE = {
  COMPLETED: { key: 'done', bg: 'var(--success-soft)', color: 'var(--success)' },
  IN_PROGRESS: { key: 'doing', bg: 'var(--accent-soft)', color: 'var(--accent)' },
  DEFERRED: { key: 'deferred', bg: 'var(--warning-soft)', color: 'var(--warning)' },
  SKIPPED: { key: 'skipped', bg: 'var(--bg-elevated)', color: 'var(--text-muted)' },
  TODO: null,
};

const STATUS_LABEL = {
  vi: { done: 'Hoàn thành', doing: 'Đang làm', deferred: 'Đã dời', skipped: 'Bỏ qua' },
  en: { done: 'Completed', doing: 'In progress', deferred: 'Deferred', skipped: 'Skipped' },
};

/* ── Hero: one next action, not four equal KPIs ───────────────────────── */
function NextBestAction({ user, task, onStart, onComplete, onDefer, onOpenCitation, busy, lang }) {
  const greeting =
    lang === 'vi'
      ? `Chào ${getTimeOfDay(lang)}, ${user?.name?.split(' ').pop() || 'bạn'}!`
      : `Good ${getTimeOfDay(lang)}, ${user?.name?.split(' ').shift() || 'there'}!`;

  return (
    <section
      aria-label={lang === 'vi' ? 'Việc nên làm tiếp theo' : 'Next best action'}
      /* radius/border/shadow come from .student-hero-card in index.css */
      className="student-hero-card p-6 md:p-7"
    >
      <h1 className="font-display text-2xl md:text-3xl font-bold mb-4 leading-tight text-fg">
        {greeting}
      </h1>

      <div className="nba-card p-4 border border-line bg-surface-card">
        <div className="flex items-center gap-1.5 mb-2">
          <Zap size={13} className="text-accent" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-accent-text-safe">
            {lang === 'vi' ? 'Việc nên làm tiếp theo' : 'Next best action'}
          </span>
        </div>

        {task ? (
          <>
            <p className="text-[16px] font-bold mb-1 text-fg">
              {task.title}
            </p>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="flex items-center gap-1 text-[12px] text-fg-muted">
                <Clock size={11} /> {formatMinutes(task.estimatedMinutes, lang)}
              </span>
              <ProvenanceBadge provenance={task.estimateProvenance} lang={lang} size="xs" />
              <span className="flex items-center gap-1 text-[12px] text-fg-muted">
                <CalendarClock size={11} /> {task.scheduledDate}
              </span>
              {task.sourceRefs?.map((ref) => (
                <CitationChip key={ref.chunkId} citation={ref} onOpen={onOpenCitation} lang={lang} />
              ))}
            </div>
            {task.suggestionReason && (
              <p className="text-[12px] italic mb-3 leading-relaxed text-fg-muted">
                <span className="not-italic font-semibold text-ai-insight">
                  {lang === 'vi' ? 'Vì sao Trợ lý Cursus đề xuất: ' : 'Why Cursus Assistant suggests this: '}
                </span>
                {task.suggestionReason}
              </p>
            )}
            <div className="flex gap-2 flex-wrap">
              {task.status === 'IN_PROGRESS' ? (
                <button
                  className="btn btn-accent text-[13px] px-4 min-h-10 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-card)]"
                  onClick={() => onComplete(task)}
                  disabled={busy}
                >
                  <CheckCircle2 size={14} /> {lang === 'vi' ? 'Hoàn thành' : 'Complete'}
                </button>
              ) : (
                <button
                  className="btn btn-accent text-[13px] px-4 min-h-10 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-card)]"
                  onClick={() => onStart(task)}
                  disabled={busy}
                >
                  <PlayCircle size={14} /> {lang === 'vi' ? 'Bắt đầu' : 'Start'}
                </button>
              )}
              <button
                className="btn btn-outline text-[13px] px-4 min-h-10 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-card)]"
                onClick={() => onDefer(task)}
                disabled={busy}
              >
                {lang === 'vi' ? 'Dời việc' : 'Defer'}
              </button>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2 py-1">
            <CheckCheck size={18} className="text-success shrink-0" />
            <div>
              <p className="text-[14px] font-semibold text-success">
                {lang === 'vi' ? 'Hết việc cho tuần này' : 'Nothing left this week'}
              </p>
              <p className="text-[12px] text-fg-muted">
                {lang === 'vi'
                  ? 'Sang bước Phản tư để chốt điều chỉnh cho tuần sau.'
                  : 'Head to Reflect to decide next week’s adjustments.'}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

/* ── Week progress ────────────────────────────────────────────────────── */
function WeekProgress({ plan, completedCount, totalCount, progressPct, lang }) {
  const actual = plan?.tasks?.reduce((sum, task) => sum + (task.actualMinutes || 0), 0) ?? 0;
  const estimated = plan?.plannedMinutes ?? 0;
  const deferred = plan?.tasks?.filter((task) => task.status === 'DEFERRED').length ?? 0;

  const metrics = [
    {
      label: lang === 'vi' ? 'Tiến độ tuần' : 'Week progress',
      value: `${progressPct}%`,
      sub: lang === 'vi' ? `${completedCount}/${totalCount} việc` : `${completedCount}/${totalCount} tasks`,
      color: 'var(--plan)',
      icon: <TrendingUp size={16} />,
    },
    {
      label: lang === 'vi' ? 'Thời gian thực tế' : 'Actual time',
      value: formatMinutes(actual, lang),
      sub: `${lang === 'vi' ? 'ước tính' : 'estimated'} ${formatMinutes(estimated, lang)}`,
      color: 'var(--do)',
      icon: <Clock size={16} />,
    },
    {
      label: lang === 'vi' ? 'Việc đã dời' : 'Deferred',
      value: deferred,
      sub: lang === 'vi' ? 'việc' : 'tasks',
      color: deferred > 0 ? 'var(--warning)' : 'var(--do)',
      icon: deferred > 0 ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />,
    },
  ];

  return (
    <section aria-label={lang === 'vi' ? 'Tiến độ tuần' : 'Week progress'}>
      <h2 className="text-[13px] font-bold uppercase tracking-widest mb-3 flex items-center gap-1.5 text-fg-muted">
        {lang === 'vi' ? 'Tiến độ tuần' : 'Week progress'}
        <ProvenanceBadge sourceType="system_derived" lang={lang} size="xs" />
      </h2>
      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {metrics.map((metric) => (
          <div key={metric.label} className="card p-4 flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <dt className="text-[12px] font-semibold text-fg-muted">
                {metric.label}
              </dt>
              <span style={{ color: metric.color }}>{metric.icon}</span>
            </div>
            <dd className="font-display text-2xl font-bold leading-none" style={{ color: metric.color }}>
              {metric.value}
            </dd>
            <span className="text-[11px] text-fg-muted">
              {metric.sub}
            </span>
          </div>
        ))}
      </dl>
    </section>
  );
}

/* ── Task list (the Do surface) ───────────────────────────────────────── */
function TaskRow({ task, onStart, onComplete, onDefer, onOpenCitation, busy, lang }) {
  const style = STATUS_STYLE[task.status];
  const done = task.status === 'COMPLETED';

  return (
    <li
      className={`p-3.5 rounded-xl border border-line transition-colors duration-200 hover:border-line-strong ${
        done ? 'bg-transparent opacity-70' : 'bg-surface-card'
      }`}
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`text-[14px] font-semibold leading-snug ${
                done ? 'line-through text-fg-muted' : 'text-fg'
              }`}
            >
              {task.title}
            </span>
            {style && (
              <span
                className="badge text-[10px]"
                style={{ background: style.bg, color: style.color }}
              >
                {STATUS_LABEL[lang === 'vi' ? 'vi' : 'en'][style.key]}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            <span className="flex items-center gap-1 text-[12px] text-fg-muted">
              <CalendarClock size={11} /> {task.scheduledDate}
            </span>
            <span className="flex items-center gap-1 text-[12px] text-fg-muted">
              <Clock size={11} />
              {formatMinutes(task.estimatedMinutes, lang)}
              {task.actualMinutes != null && (
                <>
                  {' → '}
                  <strong
                    className={
                      task.actualMinutes > task.estimatedMinutes ? 'text-warning' : 'text-success'
                    }
                  >
                    {formatMinutes(task.actualMinutes, lang)}
                  </strong>
                </>
              )}
            </span>
            <ProvenanceBadge provenance={task.estimateProvenance} lang={lang} size="xs" />
            {task.sourceRefs?.map((ref) => (
              <CitationChip key={ref.chunkId} citation={ref} onOpen={onOpenCitation} lang={lang} />
            ))}
          </div>

          {task.deferReasonLabel && (
            <p className="text-[11px] mt-1.5 flex items-center gap-1.5 text-warning">
              <ProvenanceBadge sourceType="user_entered" lang={lang} size="xs" />
              {lang === 'vi' ? 'Lý do dời' : 'Defer reason'}: {task.deferReasonLabel}
              {task.deferCount > 1 && ` (×${task.deferCount})`}
            </p>
          )}
        </div>

        {!done && (
          <div className="flex gap-1.5 shrink-0">
            {task.status === 'IN_PROGRESS' ? (
              <button
                type="button"
                className="btn btn-accent text-[12px] px-3 min-h-10 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
                onClick={() => onComplete(task)}
                disabled={busy}
              >
                {lang === 'vi' ? 'Hoàn thành' : 'Complete'}
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-outline text-[12px] px-3 min-h-10 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
                onClick={() => onStart(task)}
                disabled={busy}
              >
                {lang === 'vi' ? 'Bắt đầu' : 'Start'}
              </button>
            )}
            <button
              type="button"
              className="btn-ghost text-[12px] px-2.5 min-h-10 rounded-lg cursor-pointer disabled:opacity-50 text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
              onClick={() => onDefer(task)}
              disabled={busy}
            >
              {lang === 'vi' ? 'Dời' : 'Defer'}
            </button>
          </div>
        )}
      </div>
    </li>
  );
}

/* ── Plan → Do → Reflect stepper ──────────────────────────────────────── */
function PdrStepper({ phase, plan, completedCount, totalCount, lang, navigate }) {
  const steps = [
    {
      key: 'plan',
      label: 'Plan',
      icon: <Target size={17} />,
      color: 'var(--plan)',
      status: plan
        ? plan.status === 'DRAFT'
          ? lang === 'vi'
            ? 'Kế hoạch nháp — chờ bạn xác nhận'
            : 'Draft — waiting for your confirmation'
          : lang === 'vi'
            ? 'Đã xác nhận'
            : 'Confirmed'
        : lang === 'vi'
          ? 'Chưa có kế hoạch'
          : 'No plan yet',
      done: Boolean(plan) && plan.status !== 'DRAFT',
      cta: !plan || plan.status === 'DRAFT' ? (lang === 'vi' ? 'Mở Planner' : 'Open planner') : null,
      onCta: () => navigate('/student/planner'),
    },
    {
      key: 'do',
      label: 'Do',
      icon: <PlayCircle size={17} />,
      color: 'var(--do)',
      status:
        lang === 'vi'
          ? `${completedCount}/${totalCount} việc hoàn thành`
          : `${completedCount}/${totalCount} tasks done`,
      done: totalCount > 0 && completedCount === totalCount,
      progress: totalCount ? Math.round((completedCount / totalCount) * 100) : 0,
    },
    {
      key: 'reflect',
      label: 'Reflect',
      icon: <RotateCcw size={17} />,
      color: 'var(--reflect)',
      status:
        phase === 'next-plan'
          ? lang === 'vi'
            ? 'Đã phản tư — kế hoạch tuần sau đã tạo'
            : 'Reflected — next week planned'
          : lang === 'vi'
            ? 'Chưa phản tư tuần này'
            : 'Not reflected yet',
      done: phase === 'next-plan',
      cta: lang === 'vi' ? 'Mở Phản tư' : 'Open reflect',
      onCta: () => navigate('/student/reflection'),
    },
  ];

  return (
    <section aria-label={lang === 'vi' ? 'Vòng Plan–Do–Reflect' : 'Plan–Do–Reflect loop'}>
      <h2 className="text-[15px] font-bold font-display mb-3 text-fg">
        {lang === 'vi' ? 'Vòng Plan → Do → Reflect' : 'Plan → Do → Reflect'}
      </h2>
      <div className="card p-4 flex flex-col gap-3">
        {steps.map((step, index) => (
          <div key={step.key}>
            <div className="flex items-start gap-3">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5 bg-surface-elevated"
                style={{ color: step.color }}
              >
                {step.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[13px] font-bold" style={{ color: step.color }}>
                    {step.label}
                    {phase === step.key && (
                      <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded-full align-middle bg-accent-cta text-white">
                        {lang === 'vi' ? 'ĐANG Ở ĐÂY' : 'YOU ARE HERE'}
                      </span>
                    )}
                  </p>
                  {step.done && <CheckCircle2 size={14} className="text-success shrink-0" />}
                </div>
                <p className="text-[12px] mt-0.5 text-fg-secondary">
                  {step.status}
                </p>
                {step.progress !== undefined && (
                  <div
                    role="progressbar"
                    aria-valuenow={step.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={lang === 'vi' ? 'Tiến độ việc tuần này' : 'Task progress this week'}
                    title={`${step.progress}%`}
                    className="mt-2 w-full h-1 rounded-full overflow-hidden bg-line"
                  >
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${step.progress}%`, background: step.color }}
                    />
                  </div>
                )}
                {step.cta && (
                  <button
                    type="button"
                    className="mt-2 -ml-1 px-1 min-h-9 text-[12px] font-semibold inline-flex items-center gap-1 rounded-lg cursor-pointer transition-colors hover:bg-surface-elevated outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    style={{ color: step.color }}
                    onClick={step.onCta}
                  >
                    {step.cta} <ChevronRight size={12} />
                  </button>
                )}
              </div>
            </div>
            {index < steps.length - 1 && (
              <div className="ml-[18px] mt-1 mb-1 w-0.5 h-3 rounded-full bg-line" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── Main ─────────────────────────────────────────────────────────────── */
export default function StudentHome({ user }) {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const {
    assignment,
    course,
    currentPlan,
    deferReasons,
    tasks,
    completedCount,
    totalCount,
    progressPct,
    nextBestAction,
    phase,
    loading,
    error,
    mutating,
    reload,
    startTask,
    completeTask,
    deferTask,
    fastForward,
  } = useGate2();

  const [openCitation, setOpenCitation] = useState(null);
  const [deferTarget, setDeferTarget] = useState(null);
  const [completeTarget, setCompleteTarget] = useState(null);
  const [actionError, setActionError] = useState(null);

  const run = async (fn) => {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(err);
    }
  };

  const handleComplete = (task) => setCompleteTarget(task);

  const handleCompleteConfirm = async (actualMinutes) => {
    await run(() => completeTask(completeTarget.id, actualMinutes));
    setCompleteTarget(null);
  };

  const handleDeferConfirm = async (reasonCode, note) => {
    await run(() => deferTask(deferTarget.id, reasonCode, note));
    setDeferTarget(null);
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-4 md:p-6">
        <Skeleton className="h-40 w-full rounded-2xl" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-24 rounded-2xl" />
          ))}
        </div>
        <SkeletonRows count={4} rowClassName="h-20 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 md:p-6">
        <ErrorState
          title={lang === 'vi' ? 'Không tải được không gian học tập' : 'Could not load your workspace'}
          description={
            lang === 'vi'
              ? 'Máy chủ chưa phản hồi. Kiểm tra kết nối rồi thử lại.'
              : 'The server did not respond. Check your connection and retry.'
          }
          onRetry={reload}
          retryLabel={lang === 'vi' ? 'Thử lại' : 'Retry'}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 animate-fade-up w-full max-w-[1440px] mx-auto">
      <NextBestAction
        user={user}
        task={nextBestAction}
        onStart={(task) => run(() => startTask(task.id))}
        onComplete={handleComplete}
        onDefer={setDeferTarget}
        onOpenCitation={setOpenCitation}
        busy={mutating}
        lang={lang}
      />

      {actionError && (
        <div
          role="alert"
          className="rounded-xl p-3.5 text-[13px] flex items-start gap-2 bg-danger-soft text-danger"
        >
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <span>{actionError.message}</span>
        </div>
      )}

      <WeekProgress
        plan={currentPlan}
        completedCount={completedCount}
        totalCount={totalCount}
        progressPct={progressPct}
        lang={lang}
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 flex flex-col gap-6">
          <section aria-label={lang === 'vi' ? 'Kế hoạch tuần' : 'This week'} id="weekly-plan-section">
            <div className="flex items-center justify-between gap-2 flex-wrap mb-3">
              <h2 className="text-[18px] font-bold font-display text-fg">
                {lang === 'vi' ? 'Giờ học mỗi ngày trong tuần' : 'Daily study hours this week'}
              </h2>
              <div className="flex items-center gap-2">
                {/* Sandbox-only: lets a prospective institution evaluating the 3-role
                    trial skip ahead to next week's cycle without waiting a real week.
                    Real accounts run on real time and never see this. */}
                {currentPlan && user.isDemo && (
                  <button
                    type="button"
                    className="btn-ghost text-[11px] px-2.5 min-h-10 rounded-lg cursor-pointer inline-flex items-center gap-1 disabled:opacity-50 text-gold transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    onClick={() => run(fastForward)}
                    disabled={mutating}
                    title={
                      lang === 'vi'
                        ? 'Áp kết quả tuần theo kịch bản minh họa (dữ liệu mô phỏng, chỉ dành cho trải nghiệm thử).'
                        : 'Apply the scripted week outcome (simulated, sandbox trial only).'
                    }
                  >
                    <FlaskConical size={12} />
                    {lang === 'vi' ? 'Tua sang tuần sau' : 'Skip to next week'}
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-outline text-[12px] px-3 min-h-10 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  onClick={() => navigate('/student/planner')}
                >
                  {lang === 'vi' ? 'Mở Planner' : 'Open planner'}
                </button>
              </div>
            </div>

            <WeeklyStudyHoursChart tasks={tasks} lang={lang} />
          </section>

          <div id="qa-section">
            <CuriContextPanel
              subjectCode={course?.code ?? 'SSA101'}
              contextTask={nextBestAction}
              onOpenCitation={setOpenCitation}
              lang={lang}
            />
          </div>
        </div>

        <div className="lg:col-span-2 flex flex-col gap-6">
          <PdrStepper
            phase={phase}
            plan={currentPlan}
            completedCount={completedCount}
            totalCount={totalCount}
            lang={lang}
            navigate={navigate}
          />

          {assignment && (
            <section aria-label={lang === 'vi' ? 'Deadline sắp tới' : 'Upcoming deadline'}>
              <h2 className="text-[15px] font-bold font-display mb-3 text-fg">
                {lang === 'vi' ? 'Deadline sắp tới' : 'Upcoming deadline'}
              </h2>
              <div className="card p-4">
                <p className="text-[14px] font-semibold text-fg">
                  {assignment.title}
                </p>
                <p className="text-[12px] mt-1 text-fg-muted">
                  {new Date(assignment.dueAt).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US', {
                    weekday: 'long',
                    hour: '2-digit',
                    minute: '2-digit',
                    day: '2-digit',
                    month: '2-digit',
                  })}
                </p>
                <div className="mt-2">
                  <ProvenanceBadge provenance={assignment.provenance} lang={lang} size="xs" />
                </div>
                <ul className="mt-3 space-y-1">
                  {assignment.deliverables?.map((item) => (
                    <li
                      key={item.id}
                      className="text-[12px] flex items-center gap-1.5 text-fg-secondary"
                    >
                      <CheckCircle2 size={11} className="text-fg-muted" />
                      {item.title}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}
        </div>
      </div>

      <SourceDrawer citation={openCitation} onClose={() => setOpenCitation(null)} lang={lang} />
      <DeferTaskDialog
        task={deferTarget}
        reasons={deferReasons}
        onCancel={() => setDeferTarget(null)}
        onConfirm={handleDeferConfirm}
        busy={mutating}
        lang={lang}
      />
      <CompleteTaskDialog
        task={completeTarget}
        onCancel={() => setCompleteTarget(null)}
        onConfirm={handleCompleteConfirm}
        busy={mutating}
        lang={lang}
      />
    </div>
  );
}
