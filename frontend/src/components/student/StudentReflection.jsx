import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  Eye,
  History,
  Lock,
  Pencil,
  RotateCcw,
  Sparkles,
  Wand2,
} from 'lucide-react';
import Skeleton, { SkeletonRows } from '../shared/Skeleton';
import ErrorState from '../shared/ErrorState';
import ProvenanceBadge from '../shared/ProvenanceBadge';
import Timetable from './Timetable';
import { useGate2 } from '../../context/Gate2Context';
import { useLanguage } from '../../context/LanguageContext';
import { getReflectionPreview, previewReflectionSummary } from '../../lib/api';

function formatMinutes(minutes, lang) {
  if (!minutes && minutes !== 0) return '—';
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest}${lang === 'vi' ? ' phút' : 'm'}`;
  if (rest === 0) return `${hours}${lang === 'vi' ? ' giờ' : 'h'}`;
  return `${hours}h${String(rest).padStart(2, '0')}`;
}

/* ── Step 1: evidence, shown without judgement ─────────────────────────── */
function EvidenceSummary({ facts, bandLabel, lang }) {
  const items = [
    {
      label: lang === 'vi' ? 'Hoàn thành' : 'Completed',
      value: `${facts.completedTasks}/${facts.totalTasks}`,
      color: 'var(--do)',
    },
    {
      label: lang === 'vi' ? 'Đã dời' : 'Deferred',
      value: facts.deferredTasks,
      color: facts.deferredTasks > 0 ? 'var(--warning)' : 'var(--text-muted)',
    },
    {
      label: lang === 'vi' ? 'Ước tính' : 'Estimated',
      value: formatMinutes(facts.estimatedMinutes, lang),
      color: 'var(--text-secondary)',
    },
    {
      label: lang === 'vi' ? 'Thực tế' : 'Actual',
      value: formatMinutes(facts.actualMinutes, lang),
      color:
        facts.actualMinutes > facts.estimatedMinutes ? 'var(--warning)' : 'var(--text-secondary)',
    },
  ];

  return (
    <section className="card p-5" aria-label={lang === 'vi' ? 'Dữ liệu thực tế' : 'Your actual data'}>
      <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
        <h2 className="text-[15px] font-bold font-display text-fg">
          {lang === 'vi' ? 'Tuần vừa rồi thực tế thế nào' : 'What actually happened'}
        </h2>
        <ProvenanceBadge sourceType="system_derived" lang={lang} size="xs" />
      </div>
      <p className="text-[12px] mb-4 text-fg-muted">
        {lang === 'vi'
          ? 'Số liệu lấy trực tiếp từ việc và sự kiện của bạn — không đánh giá đúng/sai.'
          : 'Taken straight from your tasks and events — no judgement attached.'}{' '}
        <span className="text-accent-text-safe font-semibold">{bandLabel}</span>
      </p>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {items.map((item) => (
          <div
            key={item.label}
            className="rounded-[var(--radius-sm)] p-3 bg-surface-elevated border border-line"
          >
            <dt className="text-[11px] font-semibold text-fg-muted">
              {item.label}
            </dt>
            <dd className="font-display text-xl font-bold mt-0.5" style={{ color: item.color }}>
              {item.value}
            </dd>
          </div>
        ))}
      </dl>

      {facts.overEstimateTasks?.length > 0 && (
        <div className="mt-4">
          <p className="text-[11px] font-bold uppercase tracking-widest mb-1.5 text-fg-muted">
            {lang === 'vi' ? 'Vượt ước tính' : 'Over estimate'}
          </p>
          <ul className="space-y-1">
            {facts.overEstimateTasks.map((task) => (
              <li
                key={task.taskId}
                className="text-[12px] flex items-center gap-1.5 text-fg-secondary"
              >
                <Clock size={11} className="text-warning" />
                {task.title}: {formatMinutes(task.estimatedMinutes, lang)} →{' '}
                <strong className="text-warning">
                  {formatMinutes(task.actualMinutes, lang)}
                </strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

/* ── Where the student is in the reflection flow ───────────────────────── */
function StepIndicator({ step, lang }) {
  const steps = [
    { key: 'questions', vi: 'Trả lời', en: 'Answer' },
    { key: 'memory', vi: 'Xem ghi nhớ', en: 'Review memory' },
    { key: 'done', vi: 'Áp cho tuần sau', en: 'Apply next week' },
  ];
  const activeIndex = steps.findIndex((item) => item.key === step);

  return (
    <ol className="flex flex-wrap items-center gap-2 mt-3" aria-label={lang === 'vi' ? 'Tiến trình phản tư' : 'Reflection progress'}>
      {steps.map((item, index) => {
        const state = index < activeIndex ? 'done' : index === activeIndex ? 'current' : 'todo';
        return (
          <li key={item.key} className="flex items-center gap-2">
            <span
              aria-current={state === 'current' ? 'step' : undefined}
              className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors ${
                state === 'current'
                  ? 'border-reflect text-reflect bg-surface-elevated'
                  : state === 'done'
                    ? 'border-line text-success bg-surface-elevated'
                    : 'border-line text-fg-muted bg-transparent'
              }`}
            >
              {state === 'done' ? (
                <CheckCircle2 size={11} aria-hidden="true" />
              ) : (
                <span className="mono">{index + 1}</span>
              )}
              {lang === 'vi' ? item.vi : item.en}
            </span>
            {index < steps.length - 1 && (
              <span className="w-4 h-px bg-line" aria-hidden="true" />
            )}
          </li>
        );
      })}
    </ol>
  );
}

/* ── Step 4: before/after proof that reflection changed the plan ───────── */
function BeforeAfterPanel({ nextPlan, previousPlan, changes, insight, lang }) {
  if (!nextPlan) return null;
  return (
    <section
      className="card p-5"
      aria-label={lang === 'vi' ? 'Kế hoạch tuần sau' : 'Next week plan'}
      style={{ borderLeft: '3px solid var(--reflect)' }}
    >
      <h2 className="text-[15px] font-bold font-display mb-1 text-fg">
        {lang === 'vi' ? 'Kế hoạch tuần sau đã đổi vì phản tư của bạn' : 'Next week changed because of your reflection'}
      </h2>
      <p className="text-[12px] mb-4 text-fg-muted">
        {lang === 'vi'
          ? 'Chỉ những điều chỉnh bạn đã xác nhận mới được áp dụng.'
          : 'Only the adjustments you confirmed were applied.'}
      </p>

      {insight && (
        <div className="flex items-start gap-2 rounded-[var(--radius-sm)] p-3 mb-4 bg-accent-soft border border-line">
          <Sparkles size={14} className="shrink-0 mt-0.5 text-accent-text-safe" />
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1 text-accent-text-safe">
              {lang === 'vi' ? 'Gợi ý từ Trợ lý Cursus' : "Curi's suggestion"}
            </p>
            <p className="text-[13px] leading-relaxed text-fg">{insight}</p>
          </div>
        </div>
      )}

      {changes?.length > 0 && (
        <ul className="space-y-2 mb-4">
          {changes.map((change, index) => (
            <li
              key={`${change.adjustment}-${change.taskKey ?? index}`}
              className="rounded-[var(--radius-sm)] p-3 bg-surface-elevated border border-line"
            >
              <div className="flex flex-wrap items-center gap-2 text-[13px]">
                <span className="mono px-2 py-0.5 rounded bg-danger-soft text-danger">
                  {lang === 'vi' ? 'Trước' : 'Before'}: {String(change.before)}
                </span>
                <ArrowRight size={13} className="text-fg-muted" />
                <span className="mono px-2 py-0.5 rounded bg-success-soft text-success">
                  {lang === 'vi' ? 'Sau' : 'After'}: {String(change.after)}
                </span>
              </div>
              <p className="text-[12px] mt-1.5 text-fg-secondary">
                {change.reason}
              </p>
            </li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest mb-2 text-fg-muted">
            {lang === 'vi' ? 'Tuần trước' : 'Previous week'}
            {previousPlan && ` · ${formatMinutes(previousPlan.plannedMinutes, lang)}`}
          </p>
          <ul className="space-y-1">
            {(previousPlan?.tasks ?? []).map((task) => (
              <li key={task.id} className="text-[12px] text-fg-muted">
                {task.title} · {formatMinutes(task.estimatedMinutes, lang)}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest mb-2 text-reflect">
            {lang === 'vi' ? 'Tuần sau' : 'Next week'} · {formatMinutes(nextPlan.plannedMinutes, lang)}
          </p>
          <ul className="space-y-1">
            {nextPlan.tasks.map((task) => (
              <li
                key={task.id}
                className="text-[12px]"
                style={{
                  color: task.derivedFrom ? 'var(--reflect)' : 'var(--text-secondary)',
                  fontWeight: task.derivedFrom ? 600 : 400,
                }}
              >
                {task.title} · {formatMinutes(task.estimatedMinutes, lang)}
                {task.derivedFrom && (
                  <span className="ml-1 text-[10px]">
                    ({lang === 'vi' ? 'tách nhỏ' : 'split'})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {nextPlan.weekStart && (
        <div className="mt-5 -mx-5 -mb-5 border-t border-line">
          <Timetable initialView="week" initialAnchor={nextPlan.weekStart} previewPlanId={nextPlan.id} />
        </div>
      )}
    </section>
  );
}

/* ── Main ─────────────────────────────────────────────────────────────── */
export default function StudentReflection() {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const {
    currentPlan,
    nextPlan,
    reflections,
    loading: stateLoading,
    mutating,
    submitReflection,
    buildNextWeekPlan,
  } = useGate2();

  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  // Per-question response: { answer?, reasonCode?, selectedCodes?, items? }
  const [responses, setResponses] = useState({});
  const [memory, setMemory] = useState('');
  const [memoryEdited, setMemoryEdited] = useState(false);
  const [shareWithAdvisor, setShareWithAdvisor] = useState(false);
  const [step, setStep] = useState('questions'); // questions | memory | done
  const [actionError, setActionError] = useState(null);
  const [generated, setGenerated] = useState(null);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await getReflectionPreview({ planId: currentPlan?.id ?? null, lang });
      setPreview(data);
      if (data.existing) {
        setMemory(data.existing.summary ?? '');
        const restored = {};
        (data.existing.answers ?? []).forEach((item) => {
          restored[item.questionId] = item;
        });
        setResponses(restored);
        if (data.existing.studentConfirmed) setStep('done');
      }
    } catch (err) {
      setLoadError(err);
    } finally {
      setLoading(false);
    }
  }, [currentPlan?.id, lang]);

  useEffect(() => {
    if (stateLoading) return;
    loadPreview();
  }, [loadPreview, stateLoading]);

  const setResponse = (questionId, patch) =>
    setResponses((prev) => ({ ...prev, [questionId]: { ...prev[questionId], ...patch } }));

  const buildAnswerPayload = () =>
    (preview?.questions ?? [])
      .map((question) => {
        const response = responses[question.id] || {};
        return {
          questionId: question.id,
          answer: response.answer || null,
          selectedCodes: response.selectedCodes || [],
        };
      })
      .filter((item) => item.answer || item.selectedCodes.length);

  const goToMemory = async () => {
    setActionError(null);
    try {
      const draft = await previewReflectionSummary({
        planId: preview.planId,
        answers: buildAnswerPayload(),
        adjustments: [],
        lang,
      });
      // Do not clobber text the student has already edited by hand.
      if (!memoryEdited) setMemory(draft.summary);
      setStep('memory');
    } catch (err) {
      setActionError(err);
    }
  };

  const confirm = async () => {
    setActionError(null);
    try {
      await submitReflection({
        planId: preview.planId,
        answers: buildAnswerPayload(),
        adjustments: [],
        summary: memory,
        studentConfirmed: true,
        shareWithAdvisor,
        lang,
      });
      setStep('done');
    } catch (err) {
      setActionError(err);
    }
  };

  const makeNextPlan = async () => {
    setActionError(null);
    try {
      const result = await buildNextWeekPlan({ planId: preview.planId });
      setGenerated(result);
    } catch (err) {
      setActionError(err);
    }
  };

  if (stateLoading || loading) {
    return (
      <div className="flex flex-col gap-6 p-4 md:p-6">
        <Skeleton className="h-32 w-full rounded-[var(--radius-md)]" />
        <SkeletonRows count={3} rowClassName="h-24 rounded-[var(--radius-md)]" />
      </div>
    );
  }

  if (loadError) {
    const noPlan = loadError.status === 404;
    return (
      <div className="p-4 md:p-6">
        <ErrorState
          title={
            noPlan
              ? lang === 'vi'
                ? 'Chưa có kế hoạch để phản tư'
                : 'No plan to reflect on'
              : lang === 'vi'
                ? 'Không tải được dữ liệu phản tư'
                : 'Could not load reflection'
          }
          description={
            noPlan
              ? lang === 'vi'
                ? 'Hãy lập và xác nhận kế hoạch tuần trước, rồi quay lại đây.'
                : 'Create and confirm a weekly plan first, then come back.'
              : lang === 'vi'
                ? 'Kiểm tra kết nối rồi thử lại.'
                : 'Check your connection and retry.'
          }
          onRetry={noPlan ? () => navigate('/student/planner') : loadPreview}
          retryLabel={
            noPlan
              ? lang === 'vi'
                ? 'Mở Planner'
                : 'Open planner'
              : lang === 'vi'
                ? 'Thử lại'
                : 'Retry'
          }
        />
      </div>
    );
  }

  const activeNextPlan = generated ?? (nextPlan ? { ...nextPlan, previousPlan: currentPlan } : null);

  return (
    <div className="flex flex-col lg:flex-row gap-6 p-4 md:p-6 animate-fade-up w-full max-w-[1440px] mx-auto">
      <div className="flex-[3] min-w-0 flex flex-col gap-5">
        <header>
          <h1 className="font-display text-2xl font-bold text-fg">
            {lang === 'vi' ? `Tự đánh giá tuần ${preview.weekNumber}` : `Week ${preview.weekNumber} self-assessment`}
          </h1>
          <p className="text-[13px] mt-1 text-fg-secondary">
            {lang === 'vi'
              ? 'Nhìn lại dữ liệu thật, chọn điều chỉnh cụ thể, rồi để kế hoạch tuần sau phản ánh đúng điều đó.'
              : 'Look at the real data, pick concrete adjustments, then let next week reflect them.'}
          </p>
          <StepIndicator step={step} lang={lang} />
        </header>

        <EvidenceSummary facts={preview.facts} bandLabel={preview.bandLabel} lang={lang} />

        {actionError && (
          <div
            role="alert"
            className="rounded-[var(--radius-sm)] p-3.5 text-[13px] flex items-start gap-2 bg-danger-soft text-danger"
          >
            <AlertTriangle size={14} className="shrink-0 mt-0.5" />
            <span>{actionError.message}</span>
          </div>
        )}

        {step === 'questions' && (
          <section className="card p-5" aria-label={lang === 'vi' ? 'Câu hỏi phản tư' : 'Reflection questions'}>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-3 text-fg-muted">
              {lang === 'vi' ? '6 câu hỏi cố định mỗi tuần' : 'The same 6 questions every week'}
            </p>

            <div className="space-y-6">
              {preview.questions.map((question) => {
                const response = responses[question.id] || {};
                return (
                  <div key={question.id}>
                    <p className="block text-[14px] font-semibold mb-2 text-fg">
                      {question.prompt}
                    </p>

                    {question.type === 'single_choice' && (
                      <div className="flex flex-wrap gap-1.5">
                        {question.choices.map((choice) => {
                          const active = response.selectedCodes?.[0] === choice.code;
                          return (
                            <button
                              key={choice.code}
                              type="button"
                              aria-pressed={active}
                              onClick={() => setResponse(question.id, { selectedCodes: [choice.code] })}
                              className={`text-[12px] px-3.5 min-h-10 inline-flex items-center rounded-full border cursor-pointer transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                                active
                                  ? 'border-accent bg-accent-soft text-accent-text-safe'
                                  : 'border-line bg-surface-elevated text-fg-secondary hover:border-accent hover:text-accent-text-safe'
                              }`}
                            >
                              {active && <CheckCircle2 size={11} className="inline mr-1 -mt-0.5" />}
                              {choice.label}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {question.type === 'text' && (
                      <textarea
                        id={`answer-${question.id}`}
                        rows={2}
                        className="textarea text-[13px] w-full"
                        placeholder={question.placeholder}
                        value={response.answer ?? ''}
                        onChange={(event) => setResponse(question.id, { answer: event.target.value })}
                      />
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between gap-3 mt-6 flex-wrap">
              <p className="text-[11px] text-fg-muted">
                {lang === 'vi'
                  ? 'Có thể bỏ qua bước này — kế hoạch sau vẫn chạy, chỉ ít cá nhân hoá hơn.'
                  : 'You can skip this — next week still works, just less personalised.'}
              </p>
              <button
                type="button"
                className="btn btn-accent text-[13px] px-4 min-h-10 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
                onClick={goToMemory}
                disabled={mutating}
              >
                <Eye size={14} /> {lang === 'vi' ? 'Xem trước bản ghi nhớ' : 'Preview memory'}
              </button>
            </div>
          </section>
        )}

        {step === 'memory' && (
          <section className="card p-5" aria-label={lang === 'vi' ? 'Bản ghi nhớ' : 'Memory preview'}>
            <div className="flex items-center gap-2 mb-1">
              <Pencil size={15} className="text-reflect" />
              <h2 className="text-[15px] font-bold font-display text-fg">
                {lang === 'vi' ? 'Bản ghi nhớ trước khi lưu' : 'Memory preview'}
              </h2>
            </div>
            <p className="text-[12px] mb-3 text-fg-muted">
              {lang === 'vi'
                ? 'Đây là bản nháp do hệ thống soạn từ dữ liệu của bạn. Sửa hoặc xoá tuỳ ý — chỉ bản bạn xác nhận mới được lưu.'
                : 'A draft written from your own data. Edit or delete freely — only what you confirm is stored.'}
            </p>
            <textarea
              rows={6}
              className="textarea text-[13px] w-full"
              value={memory}
              maxLength={4000}
              onChange={(event) => {
                setMemory(event.target.value);
                setMemoryEdited(true);
              }}
              aria-label={lang === 'vi' ? 'Nội dung ghi nhớ' : 'Memory content'}
            />

            <label className="flex items-start gap-2 mt-4 text-[12px] cursor-pointer text-fg-secondary">
              <input
                type="checkbox"
                className="mt-0.5 accent-[var(--accent)]"
                checked={shareWithAdvisor}
                onChange={(event) => setShareWithAdvisor(event.target.checked)}
              />
              <span>
                <Lock size={11} className="inline mr-1 -mt-0.5 text-fg-muted" />
                {lang === 'vi'
                  ? 'Chia sẻ bản tóm tắt này với cố vấn. Mặc định KHÔNG chia sẻ — giảng viên chỉ thấy chỉ số hành vi học tập.'
                  : 'Share this summary with my advisor. Off by default — lecturers only see behavioural metrics.'}
              </span>
            </label>

            <div className="flex items-center justify-between gap-3 mt-5 flex-wrap">
              <button
                type="button"
                className="btn-ghost text-[13px] px-3 min-h-10 inline-flex items-center rounded-lg cursor-pointer text-fg-secondary hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                onClick={() => setStep('questions')}
              >
                ← {lang === 'vi' ? 'Quay lại' : 'Back'}
              </button>
              <button
                type="button"
                className="btn btn-accent text-[13px] px-4 min-h-10 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
                onClick={confirm}
                disabled={mutating || !memory.trim()}
              >
                <ClipboardCheck size={14} />
                {mutating
                  ? lang === 'vi'
                    ? 'Đang lưu…'
                    : 'Saving…'
                  : lang === 'vi'
                    ? 'Xác nhận & dùng cho tuần sau'
                    : 'Confirm & use next week'}
              </button>
            </div>
          </section>
        )}

        {step === 'done' && (
          <>
            <section
              className="card p-5"
              style={{ borderLeft: '3px solid var(--success)' }}
              aria-label={lang === 'vi' ? 'Đã lưu tự đánh giá' : 'Self-assessment saved'}
              role="status"
            >
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 size={17} className="text-success" />
                <h2 className="text-[15px] font-bold font-display text-fg">
                  {lang === 'vi' ? 'Đã lưu tự đánh giá' : 'Self-assessment saved'}
                </h2>
              </div>
              <p className="text-[13px] leading-relaxed text-fg-secondary">
                {memory || reflections[0]?.summary}
              </p>

              <div className="flex items-center justify-between gap-3 mt-5 flex-wrap">
                <button
                  type="button"
                  className="btn-ghost text-[13px] px-3 min-h-10 rounded-lg cursor-pointer flex items-center gap-1.5 text-fg-secondary hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  onClick={() => {
                    setStep('questions');
                    setGenerated(null);
                  }}
                >
                  <RotateCcw size={13} /> {lang === 'vi' ? 'Sửa lại phản tư' : 'Edit reflection'}
                </button>
                <button
                  type="button"
                  className="btn btn-accent text-[13px] px-4 min-h-10 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  onClick={makeNextPlan}
                  disabled={mutating}
                >
                  <Wand2 size={14} />
                  {mutating
                    ? lang === 'vi'
                      ? 'Đang tạo…'
                      : 'Generating…'
                    : lang === 'vi'
                      ? 'Tạo kế hoạch tuần sau'
                      : 'Generate next week'}
                </button>
              </div>
            </section>

            {activeNextPlan && (
              <BeforeAfterPanel
                nextPlan={activeNextPlan}
                previousPlan={activeNextPlan.previousPlan ?? currentPlan}
                changes={activeNextPlan.reflectionChanges}
                insight={activeNextPlan.reflectionInsight}
                lang={lang}
              />
            )}
          </>
        )}
      </div>

      {/* History */}
      <aside className="flex-[2] min-w-0 flex flex-col gap-3">
        <div className="flex items-center gap-2 border-b pb-2 border-line">
          <History size={14} className="text-fg-muted" />
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-fg-muted">
            {lang === 'vi' ? 'Lịch sử phản tư' : 'Reflection history'}
          </h2>
        </div>
        {reflections.length === 0 ? (
          <div className="card p-6 text-center">
            <Sparkles size={22} className="mx-auto mb-2 text-fg-muted" />
            <p className="text-[12px] text-fg-muted">
              {lang === 'vi'
                ? 'Chưa có phản tư nào được lưu.'
                : 'No reflections saved yet.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {reflections.map((item) => (
              <article key={item.id} className="card p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-[12px] font-bold text-fg">
                    {lang === 'vi' ? `Tuần ${item.weekNumber}` : `Week ${item.weekNumber}`}
                  </span>
                  {item.studentConfirmed && (
                    <span className="badge text-[9px] bg-success-soft text-success">
                      {lang === 'vi' ? 'Đã xác nhận' : 'Confirmed'}
                    </span>
                  )}
                </div>
                <p className="text-[12px] leading-relaxed text-fg-secondary">
                  {item.summary}
                </p>
                {item.adjustmentLabels?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {item.adjustmentLabels.map((label) => (
                      <span
                        key={label}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-accent-soft text-accent-text-safe"
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mono text-[10px] mt-2.5 text-fg-muted">
                  {new Date(item.generatedAt).toLocaleDateString(lang === 'vi' ? 'vi-VN' : 'en-US')}
                </p>
              </article>
            ))}
          </div>
        )}
      </aside>
    </div>
  );
}
