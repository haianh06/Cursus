import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Clock,
  Info,
  Sparkles,
  Target,
  Wand2,
} from 'lucide-react';
import { useGate2 } from '../../context/Gate2Context';
import { useLanguage } from '../../context/LanguageContext';
import { getStudentCourses } from '../../lib/api';
import Skeleton, { SkeletonRows } from '../shared/Skeleton';
import EmptyState from '../shared/EmptyState';
import ErrorState from '../shared/ErrorState';
import ProvenanceBadge from '../shared/ProvenanceBadge';
import SourceDrawer, { CitationChip } from '../shared/SourceDrawer';
import Timetable from './Timetable';

const WEEKDAYS_VI = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'];
const WEEKDAYS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const DEFAULT_AVAILABILITY = [60, 0, 120, 0, 60, 180, 60];

function formatMinutes(minutes, lang) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest}${lang === 'vi' ? ' phút' : 'm'}`;
  if (rest === 0) return `${hours}${lang === 'vi' ? ' giờ' : 'h'}`;
  return `${hours}h${rest.toString().padStart(2, '0')}`;
}

/** Total estimate vs. declared free time — the Shovel-style "you don't have
 *  enough hours" warning the blueprint asks for (§10, §3.1). */
function CapacityMeter({ planned, capacity, lang }) {
  const pct = capacity > 0 ? Math.min(200, Math.round((planned / capacity) * 100)) : 0;
  const over = capacity > 0 && planned > capacity;
  const barColor = over ? 'var(--danger)' : pct > 85 ? 'var(--warning)' : 'var(--do)';

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5 gap-2 flex-wrap">
        <span className="text-[12px] font-semibold text-fg-secondary">
          {lang === "vi"
            ? 'Tổng dự kiến so với giờ rảnh lúc tạo kế hoạch này'
            : 'Planned vs. available (at the time this plan was created)'}
        </span>
        <span className="mono text-[12px] font-bold" style={{ color: barColor }}>
          {formatMinutes(planned, lang)} / {formatMinutes(capacity, lang)}
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={lang === 'vi' ? 'Mức sử dụng quỹ thời gian' : 'Capacity usage'}
        title={`${pct}%`}
        className="w-full h-2 rounded-full overflow-hidden bg-line"
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(100, pct)}%`, background: barColor }}
        />
      </div>
      {over && (
        <p className="flex items-start gap-1.5 text-[12px] mt-2 rounded-lg p-2.5 text-danger bg-danger-soft">
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          <span>
            {lang === 'vi'
              ? `Kế hoạch vượt quỹ thời gian ${formatMinutes(planned - capacity, lang)}. Hãy dời hoặc bỏ bớt một việc trước khi xác nhận.`
              : `Plan exceeds your free time by ${formatMinutes(planned - capacity, lang)}.`}
          </span>
        </p>
      )}
    </div>
  );
}

function TaskDraftRow({ task, onOpenCitation, lang }) {
  return (
    <li className="p-3.5 rounded-xl border border-line bg-surface-card transition-colors duration-200 hover:border-line-strong">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <p className="text-[14px] font-semibold leading-snug text-fg">
            {task.title}
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            <span className="flex items-center gap-1 text-[12px] text-fg-muted">
              <CalendarClock size={11} /> {task.scheduledDate}
            </span>
            <span className="flex items-center gap-1 text-[12px] text-fg-muted">
              <Clock size={11} /> {formatMinutes(task.estimatedMinutes, lang)}
            </span>
            <ProvenanceBadge provenance={task.estimateProvenance} lang={lang} size="xs" />
            {task.deliverable && (
              <ProvenanceBadge
                sourceType="simulated"
                lang={lang}
                size="xs"
                label={task.deliverable}
                title={
                  lang === 'vi'
                    ? 'Hạng mục nộp là dữ liệu minh họa, không phải yêu cầu trích từ syllabus.'
                    : 'Deliverable is sample data, not a syllabus-sourced requirement.'
                }
              />
            )}
          </div>
        </div>
        <span
          className="badge text-[10px] shrink-0"
          style={{
            background: task.priority === 'HIGH' ? 'var(--danger-soft)' : 'var(--bg-elevated)',
            color: task.priority === 'HIGH' ? 'var(--danger)' : 'var(--text-muted)',
          }}
        >
          {task.priority}
        </span>
      </div>

      {task.suggestionReason && (
        <p className="text-[12px] italic mt-2 leading-relaxed text-fg-muted">
          <span className="not-italic font-semibold text-ai-insight">
            {lang === 'vi' ? 'Vì sao Trợ lý Cursus đề xuất: ' : 'Why Cursus Assistant suggests this: '}
          </span>
          {task.suggestionReason}
        </p>
      )}

      {task.sourceFact && (
        <p className="text-[12px] mt-1.5 leading-relaxed text-fg-secondary">
          <ProvenanceBadge sourceType="official_document" lang={lang} size="xs" /> {task.sourceFact}
        </p>
      )}

      {task.sourceRefs?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {task.sourceRefs.map((ref) => (
            <CitationChip key={ref.chunkId} citation={ref} onOpen={onOpenCitation} lang={lang} />
          ))}
        </div>
      )}
    </li>
  );
}

export default function StudentPlanner() {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const {
    currentPlan,
    loading,
    error,
    mutating,
    reload,
    createPlan,
    confirmPlan,
  } = useGate2();

  const [courses, setCourses] = useState([]);
  const [goalText, setGoalText] = useState('');
  const [subjectCode, setSubjectCode] = useState('');
  const [availability, setAvailability] = useState(DEFAULT_AVAILABILITY);
  const [session, setSession] = useState('EVENING');
  const [generating, setGenerating] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [openCitation, setOpenCitation] = useState(null);
  const [confirmed, setConfirmed] = useState(false);

  const weekdays = lang === 'vi' ? WEEKDAYS_VI : WEEKDAYS_EN;
  const declaredMinutes = useMemo(
    () => availability.reduce((sum, value) => sum + value, 0),
    [availability],
  );

  const plan = currentPlan;
  const isDraft = plan?.status === 'DRAFT';

  useEffect(() => {
    let cancelled = false;
    getStudentCourses()
      .then((data) => {
        if (cancelled) return;
        const list = data || [];
        setCourses(list);
        setSubjectCode((prev) => prev || plan?.subjectCode || list[0]?.code || '');
      })
      .catch(() => {
        /* course select stays empty — generate button disables on !subjectCode */
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Prefill once from the plan — never overwrite what the student is typing.
  const [prefilled, setPrefilled] = useState(false);
  useEffect(() => {
    if (prefilled || !plan) return;
    setGoalText(plan.goalText || '');
    if (plan.subjectCode) setSubjectCode(plan.subjectCode);
    setPrefilled(true);
  }, [plan, prefilled]);

  const handleGenerate = async () => {
    setActionError(null);
    if (!goalText.trim()) {
      setActionError({ message: lang === 'vi' ? 'Nhập mục tiêu tuần này để lập kế hoạch.' : 'Enter this week’s goal to generate a plan.' });
      return;
    }
    if (!subjectCode) {
      setActionError({ message: lang === 'vi' ? 'Chưa chọn môn học để lập kế hoạch.' : 'Choose a course to generate a plan.' });
      return;
    }
    setGenerating(true);
    try {
      await createPlan({
        goalText,
        subjectCode,
        availableHours: declaredMinutes / 60,
        preferredSessions: [session],
        availability: availability
          .map((minutes, index) => ({ index, minutes }))
          .filter((slot) => slot.minutes > 0)
          .map((slot) => ({
            date: addDays(plan?.weekStart, slot.index),
            availableMinutes: slot.minutes,
          }))
          .filter((slot) => Boolean(slot.date)),
      });
    } catch (err) {
      setActionError(err);
    } finally {
      setGenerating(false);
    }
  };

  const handleConfirm = async () => {
    setActionError(null);
    try {
      await confirmPlan(plan.id);
      setConfirmed(true);
    } catch (err) {
      setActionError(err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-4 md:p-6">
        <Skeleton className="h-28 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
        <SkeletonRows count={4} rowClassName="h-20 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 md:p-6">
        <ErrorState
          title={lang === 'vi' ? 'Không tải được dữ liệu kế hoạch' : 'Could not load your plan'}
          description={lang === 'vi' ? 'Kiểm tra kết nối rồi thử lại.' : 'Check your connection and retry.'}
          onRetry={reload}
          retryLabel={lang === 'vi' ? 'Thử lại' : 'Retry'}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 animate-fade-up w-full max-w-[1440px]">
      <header>
        <h1 className="font-display text-2xl font-bold text-fg">
          {lang === 'vi' ? 'Lập kế hoạch tuần' : 'Weekly planner'}
        </h1>
        <p className="text-[13px] mt-1 text-fg-secondary">
          {lang === 'vi'
            ? 'Trợ lý Cursus đề xuất, bạn sửa và xác nhận. Kế hoạch chưa xác nhận thì chưa có hiệu lực.'
            : 'Cursus Assistant proposes, you edit and confirm. Nothing takes effect until you confirm.'}
        </p>
      </header>

      {/* Goal — free-text goal + course, the a46db63 contract */}
      <section aria-label={lang === 'vi' ? 'Mục tiêu' : 'Goal'} className="card p-5">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-accent-soft text-accent">
            <Target size={18} />
          </div>
          <div className="min-w-0 flex-1 space-y-3">
            <div>
              <label htmlFor="plan-goal" className="block text-[11px] font-semibold mb-1 text-fg-secondary">
                {lang === 'vi' ? 'Mục tiêu tuần này' : 'This week’s goal'}
              </label>
              <input
                id="plan-goal"
                type="text"
                maxLength={500}
                className="input text-[13px] w-full h-11"
                placeholder={
                  lang === 'vi'
                    ? 'VD: Hoàn thành phần 1 đồ án SSA101'
                    : 'e.g. Finish SSA101 project part 1'
                }
                value={goalText}
                onChange={(event) => setGoalText(event.target.value)}
              />
            </div>
            <div>
              <label htmlFor="plan-subject" className="block text-[11px] font-semibold mb-1 text-fg-secondary">
                {lang === 'vi' ? 'Môn học' : 'Course'}
              </label>
              <select
                id="plan-subject"
                className="input text-[13px] h-11 w-full"
                value={subjectCode}
                onChange={(event) => setSubjectCode(event.target.value)}
              >
                {courses.length === 0 && <option value="">—</option>}
                {courses.map((course) => (
                  <option key={course.code} value={course.code}>
                    {course.code} — {course.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* Availability */}
      <section aria-label={lang === 'vi' ? 'Lịch rảnh' : 'Availability'} className="card p-5">
        <h2 className="text-[15px] font-bold font-display mb-1 text-fg">
          {lang === 'vi' ? 'Bạn rảnh bao nhiêu?' : 'How much time do you have?'}
        </h2>
        <p className="text-[12px] mb-4 flex items-center gap-1.5 text-fg-muted">
          <ProvenanceBadge sourceType="user_entered" lang={lang} size="xs" />
          {lang === 'vi'
            ? 'Số phút bạn khai báo cho từng ngày.'
            : 'Minutes you declare for each day.'}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {weekdays.map((day, index) => (
            <div key={day}>
              <label
                htmlFor={`avail-${index}`}
                className="block text-[11px] font-semibold mb-1 text-fg-secondary"
              >
                {day}
              </label>
              <input
                id={`avail-${index}`}
                type="number"
                min={0}
                max={720}
                step={15}
                className="input text-[13px] w-full h-10"
                value={availability[index]}
                onChange={(event) => {
                  const value = Math.max(0, Math.min(720, Number(event.target.value) || 0));
                  setAvailability((prev) => prev.map((item, i) => (i === index ? value : item)));
                }}
              />
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-end justify-between gap-3 mt-4">
          <div>
            <label
              htmlFor="preferred-session"
              className="block text-[11px] font-semibold mb-1 text-fg-secondary"
            >
              {lang === 'vi' ? 'Khung giờ ưu tiên' : 'Preferred session'}
            </label>
            <select
              id="preferred-session"
              className="input text-[13px] h-10"
              style={{ minWidth: '150px' }}
              value={session}
              onChange={(event) => setSession(event.target.value)}
            >
              <option value="MORNING">{lang === 'vi' ? 'Buổi sáng' : 'Morning'}</option>
              <option value="AFTERNOON">{lang === 'vi' ? 'Buổi chiều' : 'Afternoon'}</option>
              <option value="EVENING">{lang === 'vi' ? 'Buổi tối' : 'Evening'}</option>
            </select>
          </div>
          <p className="mono text-[13px] font-bold text-accent-text-safe">
            {lang === 'vi' ? 'Tổng rảnh vừa khai báo' : 'Total free just declared'}: {formatMinutes(declaredMinutes, lang)}
            <span className="block font-normal text-[11px] text-fg-muted mt-0.5">
              {lang === 'vi'
                ? 'Chỉ áp dụng khi bạn bấm "Tạo lại kế hoạch" — chưa ảnh hưởng kế hoạch đã xác nhận bên dưới.'
                : 'Only applies once you click "Regenerate plan" — the confirmed plan below is unaffected until then.'}
            </span>
          </p>
          <button
            type="button"
            className="btn btn-accent text-[13px] px-4 min-h-11 flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
            style={{ minWidth: '210px' }}
            onClick={handleGenerate}
            disabled={!goalText.trim() || !subjectCode || generating || mutating}
          >
            <Wand2 size={14} />
            {generating
              ? lang === 'vi'
                ? 'Đang tạo…'
                : 'Generating…'
              : plan
                ? lang === 'vi'
                  ? 'Tạo lại kế hoạch'
                  : 'Regenerate plan'
                : lang === 'vi'
                  ? 'Tạo kế hoạch nháp'
                  : 'Generate draft plan'}
          </button>
        </div>
      </section>

      {/* Timetable (real class schedule + self-study blocks) on the left,
          the AI draft plan / task list on the right — same 3:2 split as the
          Overview dashboard, so the calendar and the day-by-day plan it
          drives read as one screen instead of stacked, disconnected cards. */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
        <div className="lg:col-span-3">
          <section aria-label={lang === 'vi' ? 'Thời khoá biểu' : 'Timetable'}>
            <Timetable initialView="week" />
          </section>
        </div>

        <div className="lg:col-span-2 flex flex-col gap-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] overflow-y-auto pr-0.5">
          {actionError && (
            <div
              className="rounded-xl p-3.5 text-[13px] flex items-start gap-2 bg-danger-soft text-danger"
              role="alert"
            >
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />
              <span>{actionError.message}</span>
            </div>
          )}

          {generating ? (
            <section className="card p-5">
              <Skeleton className="h-5 w-40 rounded mb-4" />
              <SkeletonRows count={5} rowClassName="h-20 rounded-xl" />
            </section>
          ) : !plan ? (
            <section className="card" aria-label={lang === 'vi' ? 'Chưa có kế hoạch' : 'No plan yet'}>
              <EmptyState
                icon={<Sparkles size={28} className="text-fg-muted" />}
                title={lang === 'vi' ? 'Chưa có kế hoạch cho tuần này' : 'No plan for this week yet'}
                description={
                  lang === 'vi'
                    ? 'Khai báo lịch rảnh ở trên rồi bấm “Tạo kế hoạch nháp”.'
                    : 'Declare your availability above, then generate a draft.'
                }
              />
            </section>
          ) : (
            <section aria-label={lang === 'vi' ? 'Kế hoạch nháp' : 'Draft plan'} className="card p-5">
              <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
                <h2 className="text-[15px] font-bold font-display text-fg">
                  {lang === 'vi' ? 'Kế hoạch đề xuất' : 'Proposed plan'}{' '}
                  <span className="font-normal text-[12px] text-fg-muted">
                    · {plan.tasks.length} {lang === 'vi' ? 'việc' : 'tasks'}
                  </span>
                </h2>
                <span
                  className="badge text-[10px]"
                  style={{
                    background: isDraft ? 'var(--gold-soft)' : 'var(--success-soft)',
                    color: isDraft ? 'var(--gold)' : 'var(--success)',
                  }}
                >
                  {isDraft
                    ? lang === 'vi'
                      ? 'Nháp — chưa xác nhận'
                      : 'Draft — not confirmed'
                    : lang === 'vi'
                      ? 'Đã xác nhận'
                      : 'Confirmed'}
                </span>
              </div>

              <div className="mb-4">
                <CapacityMeter planned={plan.plannedMinutes} capacity={plan.capacityMinutes} lang={lang} />
              </div>

              <ul className="space-y-2">
                {plan.tasks.map((task) => (
                  <TaskDraftRow key={task.id} task={task} onOpenCitation={setOpenCitation} lang={lang} />
                ))}
              </ul>

              {plan.assumptions?.length > 0 && (
                <ul className="mt-4 space-y-1">
                  {plan.assumptions.map((item) => (
                    <li key={item} className="text-[11px] flex gap-1.5 text-fg-muted">
                      <Info size={11} className="shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 mt-5">
                <p className="text-[12px] text-fg-muted">
                  {lang === 'vi'
                    ? 'Chưa vừa ý? Sửa lịch rảnh phía trên rồi tạo lại.'
                    : 'Not right? Adjust availability above and regenerate.'}
                </p>
                {isDraft ? (
                  <button
                    type="button"
                    className="btn btn-accent text-[14px] px-5 min-h-11 flex items-center gap-2 cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    onClick={handleConfirm}
                    disabled={mutating}
                  >
                    <CheckCircle2 size={15} />
                    {mutating
                      ? lang === 'vi'
                        ? 'Đang lưu…'
                        : 'Saving…'
                      : lang === 'vi'
                        ? 'Xác nhận kế hoạch'
                        : 'Confirm plan'}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-outline text-[14px] px-5 min-h-11 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    onClick={() => navigate('/student')}
                  >
                    {lang === 'vi' ? 'Tới Bảng điều khiển' : 'Go to dashboard'}
                  </button>
                )}
              </div>

              {confirmed && !isDraft && (
                <p
                  className="mt-3 text-[12px] rounded-lg p-2.5 flex items-center gap-1.5 bg-success-soft text-success"
                  role="status"
                >
                  <CheckCircle2 size={13} />
                  {lang === 'vi'
                    ? 'Đã xác nhận. Bảng điều khiển đã chuyển sang bước Thực hiện.'
                    : 'Confirmed. Your dashboard has moved to the Do step.'}
                </p>
              )}
            </section>
          )}
        </div>
      </div>

      <SourceDrawer citation={openCitation} onClose={() => setOpenCitation(null)} lang={lang} />
    </div>
  );
}

/** ISO date `weekStart + offset` days; falls back to this week's Monday. */
function addDays(weekStart, offset) {
  const base = weekStart ? new Date(weekStart) : startOfWeek(new Date());
  if (Number.isNaN(base.getTime())) return null;
  base.setDate(base.getDate() + offset);
  const year = base.getFullYear();
  const month = String(base.getMonth() + 1).padStart(2, '0');
  const day = String(base.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function startOfWeek(date) {
  const value = new Date(date);
  value.setHours(0, 0, 0, 0);
  const day = value.getDay();
  value.setDate(value.getDate() + (day === 0 ? -6 : 1 - day));
  return value;
}
