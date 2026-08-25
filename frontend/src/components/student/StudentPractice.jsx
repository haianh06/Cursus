import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FlaskConical, RefreshCw, ChevronLeft, ChevronRight, CheckCircle2, XCircle, RotateCcw } from 'lucide-react';
import Skeleton from '../shared/Skeleton';
import EmptyState from '../shared/EmptyState';
import { getStudentCourses, getPracticeSet, requestPracticeSet, currentIsoWeekNumber } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Practice sets (MCQ + flashcards) for a course + week.
 *
 * The backend (`src/api/practice.py`) is read-only for students beyond the
 * generation request — there is no submission/attempt-persistence endpoint,
 * so quiz-taking state (selected answers, score, flipped cards) lives only
 * in this component and resets on reload. That is an intentional scope
 * decision, not an oversight: nothing server-side exists to persist it.
 */
function McqItem({ item, index, lang }) {
  const [selected, setSelected] = useState(null);
  const options = item.options || [];
  const isCorrect = selected != null && selected === item.correctKey;
  const answered = selected != null;

  return (
    <div className="card p-4 text-left">
      <p className="text-[11px] font-bold text-fg-muted mb-1">
        {lang === 'vi' ? 'Câu' : 'Question'} {index + 1}
      </p>
      <p className="text-sm font-semibold text-fg mb-3">{item.prompt}</p>
      <div className="space-y-2">
        {options.map((opt) => {
          const key = opt.key ?? opt.id ?? opt.value;
          const text = opt.text ?? opt.label ?? String(opt);
          const chosen = selected === key;
          const showCorrect = answered && key === item.correctKey;
          const showWrong = answered && chosen && key !== item.correctKey;
          return (
            <button
              key={key}
              type="button"
              disabled={answered}
              onClick={() => setSelected(key)}
              className={`w-full text-left text-[13px] px-3 py-2 rounded-lg border transition-colors cursor-pointer disabled:cursor-default ${
                showCorrect
                  ? 'border-success bg-success-soft text-success'
                  : showWrong
                    ? 'border-danger bg-danger-soft text-danger'
                    : chosen
                      ? 'border-accent bg-accent-soft text-fg'
                      : 'border-line bg-surface-elevated text-fg-secondary hover:border-accent'
              }`}
            >
              {text}
            </button>
          );
        })}
      </div>
      {answered && (
        <div className="mt-3 flex items-start gap-2 text-[12px]">
          {isCorrect ? (
            <CheckCircle2 size={14} className="text-success shrink-0 mt-0.5" />
          ) : (
            <XCircle size={14} className="text-danger shrink-0 mt-0.5" />
          )}
          <p className="text-fg-secondary leading-relaxed">
            {item.explanation || (lang === 'vi' ? 'Không có giải thích.' : 'No explanation provided.')}
          </p>
        </div>
      )}
      {item.sourceLabel && (
        <p className="mt-2 text-[10px] text-fg-muted">{item.sourceLabel}</p>
      )}
    </div>
  );
}

function FlashcardItem({ item, index, lang }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setFlipped((v) => !v)}
      className="card p-5 text-left w-full min-h-[140px] flex flex-col justify-between cursor-pointer hover:border-accent transition-colors"
    >
      <p className="text-[11px] font-bold text-fg-muted mb-2">
        {lang === 'vi' ? 'Thẻ' : 'Card'} {index + 1}
      </p>
      {!flipped ? (
        <p className="text-sm font-semibold text-fg">{item.prompt}</p>
      ) : (
        <div>
          <p className="text-sm font-semibold text-accent-text-safe mb-1">{item.answer}</p>
          {item.explanation && <p className="text-[12px] text-fg-secondary">{item.explanation}</p>}
        </div>
      )}
      <p className="mt-3 text-[10px] text-fg-muted flex items-center gap-1">
        <RotateCcw size={10} /> {lang === 'vi' ? 'Chạm để lật thẻ' : 'Tap to flip'}
      </p>
    </button>
  );
}

const STATUS_LABEL = {
  PENDING_REVIEW: { vi: 'Chờ giảng viên duyệt', en: 'Pending instructor review' },
  PUBLISHED: { vi: 'Đã xuất bản', en: 'Published' },
  REJECTED: { vi: 'Bị từ chối', en: 'Rejected' },
  DRAFT: { vi: 'Bản nháp', en: 'Draft' },
};

export default function StudentPractice() {
  const { lang } = useLanguage();
  const [courses, setCourses] = useState([]);
  const [courseCode, setCourseCode] = useState('');
  // Practice weeks only run 1-10 (see the Next-week button below, which
  // already clamps at 10) — the calendar's raw ISO week is often past that
  // by the time a student opens this page, so clamp the initial value too.
  const [weekNumber, setWeekNumber] = useState(() => Math.min(10, currentIsoWeekNumber()));
  const [practiceSet, setPracticeSet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingCourses(true);
    getStudentCourses()
      .then((list) => {
        if (cancelled) return;
        setCourses(list || []);
        if (list?.length) setCourseCode((prev) => prev || list[0].code);
      })
      .catch((err) => !cancelled && setError(err))
      .finally(() => !cancelled && setLoadingCourses(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const loadSet = useCallback(async () => {
    if (!courseCode) return;
    setLoading(true);
    setError(null);
    setPracticeSet(null);
    try {
      const data = await getPracticeSet({ courseCode, weekNumber });
      setPracticeSet(data);
    } catch (err) {
      if (err?.status !== 404) setError(err);
      setPracticeSet(null);
    } finally {
      setLoading(false);
    }
  }, [courseCode, weekNumber]);

  useEffect(() => {
    loadSet();
  }, [loadSet]);

  const handleRequest = async () => {
    if (!courseCode) return;
    setRequesting(true);
    setError(null);
    try {
      const data = await requestPracticeSet({ courseCode, weekNumber, language: lang === 'en' ? 'en' : 'vi' });
      setPracticeSet(data);
    } catch (err) {
      setError(err);
    } finally {
      setRequesting(false);
    }
  };

  const mcqItems = useMemo(
    () => (practiceSet?.items || []).filter((item) => item.kind === 'MCQ').sort((a, b) => a.sortOrder - b.sortOrder),
    [practiceSet],
  );
  const flashcards = useMemo(
    () => (practiceSet?.items || []).filter((item) => item.kind === 'FLASHCARD').sort((a, b) => a.sortOrder - b.sortOrder),
    [practiceSet],
  );

  const statusLabel = practiceSet ? STATUS_LABEL[practiceSet.status] : null;

  return (
    <div className="flex flex-col gap-6 p-6 animate-fade-up">
      <div className="flex items-center justify-between border-b pb-4 border-line">
        <div className="text-left">
          <h1 className="font-display text-xl font-bold text-fg flex items-center gap-2">
            <FlaskConical size={20} className="text-accent" />
            {lang === 'vi' ? 'Luyện tập' : 'Practice'}
          </h1>
          <p className="text-xs text-fg-muted mt-1">
            {lang === 'vi'
              ? 'Trắc nghiệm và flashcard theo môn học và tuần học.'
              : 'MCQ and flashcards by course and week.'}
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-semibold text-fg-secondary mb-1.5" htmlFor="practice-course">
            {lang === 'vi' ? 'Môn học' : 'Course'}
          </label>
          {loadingCourses ? (
            <Skeleton className="h-9 w-48 rounded-lg" />
          ) : (
            <select
              id="practice-course"
              className="input text-xs w-48"
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value)}
            >
              {courses.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code} — {c.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div>
          <label className="block text-xs font-semibold text-fg-secondary mb-1.5">
            {lang === 'vi' ? 'Tuần' : 'Week'}
          </label>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="btn-ghost p-1.5 rounded-lg cursor-pointer"
              onClick={() => setWeekNumber((w) => Math.max(1, w - 1))}
              aria-label={lang === 'vi' ? 'Tuần trước' : 'Previous week'}
            >
              <ChevronLeft size={14} />
            </button>
            <span className="mono text-xs font-bold w-10 text-center">{weekNumber}</span>
            <button
              type="button"
              className="btn-ghost p-1.5 rounded-lg cursor-pointer"
              onClick={() => setWeekNumber((w) => Math.min(10, w + 1))}
              aria-label={lang === 'vi' ? 'Tuần sau' : 'Next week'}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
        <button
          type="button"
          className="btn btn-accent text-xs px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          onClick={handleRequest}
          disabled={requesting || !courseCode}
        >
          <RefreshCw size={13} className={requesting ? 'animate-spin' : ''} />
          {practiceSet
            ? lang === 'vi' ? 'Tạo lại bộ luyện tập' : 'Regenerate practice set'
            : lang === 'vi' ? 'Yêu cầu bộ luyện tập' : 'Request practice set'}
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-danger-soft border border-danger/20 text-xs text-danger">
          {error.message}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-40 w-full rounded-2xl" />
        </div>
      ) : !practiceSet ? (
        <div className="card">
          <EmptyState
            icon={<FlaskConical size={28} className="text-fg-muted" />}
            title={lang === 'vi' ? 'Chưa có bộ luyện tập cho tuần này' : 'No practice set for this week yet'}
            description={
              lang === 'vi'
                ? 'Tạo trắc nghiệm và flashcard từ học liệu môn học đã chọn.'
                : 'Generate MCQs and flashcards from the selected course material.'
            }
            actionLabel={lang === 'vi' ? 'Yêu cầu bộ luyện tập' : 'Request practice set'}
            onAction={handleRequest}
          />
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 text-xs text-fg-muted">
            <span className="badge badge-neutral text-[9px] font-bold uppercase">
              {statusLabel ? statusLabel[lang] || statusLabel.vi : practiceSet.status}
            </span>
            <span>{practiceSet.itemCount} {lang === 'vi' ? 'câu' : 'items'}</span>
          </div>

          {mcqItems.length > 0 && (
            <div>
              <h2 className="text-sm font-bold text-fg mb-3">{lang === 'vi' ? 'Trắc nghiệm' : 'Multiple choice'}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {mcqItems.map((item, i) => (
                  <McqItem key={item.id} item={item} index={i} lang={lang} />
                ))}
              </div>
            </div>
          )}

          {flashcards.length > 0 && (
            <div>
              <h2 className="text-sm font-bold text-fg mb-3">{lang === 'vi' ? 'Flashcard' : 'Flashcards'}</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {flashcards.map((item, i) => (
                  <FlashcardItem key={item.id} item={item} index={i} lang={lang} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
