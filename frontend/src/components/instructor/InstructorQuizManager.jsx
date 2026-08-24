import React, { useCallback, useEffect, useState } from 'react';
import { BookOpen, Check, ChevronDown, ChevronUp, Eye, Loader2, Plus, Sparkles, Trash2, X } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  addQuizQuestion,
  createQuiz,
  deleteQuiz,
  deleteQuizQuestion,
  generateQuizQuestions,
  getInstructorQuiz,
  getQuizProgress,
  gradeQuizSubmission,
  listInstructorQuizClasses,
  listInstructorQuizzes,
  reorderQuizQuestions,
  setQuizPublished,
  updateQuiz,
  updateQuizQuestion,
  userFacingApiError,
} from '../../lib/api';

const GENERATE_COUNT_OPTIONS = [5, 10, 15, 20];

const QUESTION_TYPES = [
  { id: 'MULTIPLE_CHOICE', labelKey: 'instructor.quizTypeMultipleChoice' },
  { id: 'TRUE_FALSE', labelKey: 'instructor.quizTypeTrueFalse' },
  { id: 'SHORT_ANSWER', labelKey: 'instructor.quizTypeShortAnswer' },
];

const OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

const EMPTY_QUESTION_FORM = {
  question_text: '',
  question_type: 'MULTIPLE_CHOICE',
  options: ['', ''],
  correct_answer: '',
  points: 1,
};

function toDatetimeLocal(iso) {
  if (!iso) return '';
  return iso.slice(0, 16);
}

function QuestionForm({ initial, onSave, onCancel, t, saving }) {
  const [form, setForm] = useState(initial || EMPTY_QUESTION_FORM);

  const setField = (patch) => setForm((prev) => ({ ...prev, ...patch }));

  const setOption = (index, value) => {
    setForm((prev) => {
      const options = [...prev.options];
      options[index] = value;
      return { ...prev, options };
    });
  };

  const addOption = () => setField({ options: [...form.options, ''] });
  const removeOption = (index) =>
    setField({ options: form.options.filter((_, i) => i !== index) });

  const submit = () => {
    const payload = {
      question_text: form.question_text,
      question_type: form.question_type,
      points: Number(form.points) || 0,
      options: form.question_type === 'MULTIPLE_CHOICE' ? form.options.filter((o) => o.trim()) : [],
      correct_answer:
        form.question_type === 'TRUE_FALSE' ? (form.correct_answer || 'true') : form.correct_answer,
    };
    onSave(payload);
  };

  return (
    <div className="rounded-lg border border-line p-4 flex flex-col gap-3 bg-surface">
      <label className="block">
        <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizQuestionTypeLabel')}</span>
        <select
          className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
          value={form.question_type}
          onChange={(event) =>
            setField({
              question_type: event.target.value,
              correct_answer: '',
              options: event.target.value === 'MULTIPLE_CHOICE' ? ['', ''] : [],
            })
          }
        >
          {QUESTION_TYPES.map((qt) => (
            <option key={qt.id} value={qt.id}>{t(qt.labelKey)}</option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizQuestionTextLabel')}</span>
        <textarea
          className="input text-sm w-full min-h-[64px] mt-1.5"
          value={form.question_text}
          onChange={(event) => setField({ question_text: event.target.value })}
        />
      </label>

      {form.question_type === 'MULTIPLE_CHOICE' && (
        <div>
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizOptionsLabel')}</span>
          <div className="flex flex-col gap-2 mt-1.5">
            {form.options.map((option, index) => (
              <div key={index} className="flex items-center gap-2">
                <input
                  type="radio"
                  name="correct-option"
                  checked={form.correct_answer === option && option.trim() !== ''}
                  onChange={() => setField({ correct_answer: option })}
                  aria-label={t('instructor.quizCorrectAnswerLabel')}
                />
                <span className="font-mono-code font-bold text-xs text-fg-secondary w-4 shrink-0">
                  {OPTION_LETTERS[index] || index + 1}.
                </span>
                <input
                  className="input text-sm flex-1"
                  placeholder={t('instructor.quizOptionPlaceholder', { n: index + 1 })}
                  value={option}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (form.correct_answer === option) setField({ correct_answer: value });
                    setOption(index, value);
                  }}
                />
                {form.options.length > 2 && (
                  <button
                    type="button"
                    className="text-xs font-semibold text-[color:var(--danger)]"
                    onClick={() => removeOption(index)}
                  >
                    {t('instructor.quizRemoveOptionBtn')}
                  </button>
                )}
              </div>
            ))}
          </div>
          <button type="button" className="btn btn-outline text-xs px-3 py-1.5 mt-2" onClick={addOption}>
            <Plus size={12} /> {t('instructor.quizAddOptionBtn')}
          </button>
        </div>
      )}

      {form.question_type === 'TRUE_FALSE' && (
        <label className="block max-w-xs">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizCorrectAnswerLabel')}</span>
          <select
            className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={form.correct_answer || 'true'}
            onChange={(event) => setField({ correct_answer: event.target.value })}
          >
            <option value="true">{t('studentQuizzes.trueLabel')}</option>
            <option value="false">{t('studentQuizzes.falseLabel')}</option>
          </select>
        </label>
      )}

      {form.question_type === 'SHORT_ANSWER' && (
        <label className="block">
          <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizCorrectAnswerLabel')}</span>
          <p className="text-[11px] text-fg-muted mb-1">{t('instructor.quizCorrectAnswerHint')}</p>
          <textarea
            className="input text-sm w-full min-h-[48px]"
            value={form.correct_answer}
            onChange={(event) => setField({ correct_answer: event.target.value })}
          />
        </label>
      )}

      <label className="block max-w-[10rem]">
        <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizPointsLabel')}</span>
        <input
          type="number"
          min="0"
          step="0.5"
          className="input text-sm w-full mt-1.5"
          value={form.points}
          onChange={(event) => setField({ points: event.target.value })}
        />
      </label>

      <div className="flex gap-2">
        <button
          type="button"
          className="btn btn-orange text-xs px-4 py-2"
          disabled={saving || !form.question_text.trim()}
          onClick={submit}
        >
          {saving ? <Loader2 size={12} className="animate-spin" /> : null}
          {t('instructor.quizSaveQuestionBtn')}
        </button>
        <button type="button" className="btn btn-outline text-xs px-4 py-2" onClick={onCancel}>
          {t('instructor.quizCancelBtn')}
        </button>
      </div>
    </div>
  );
}

function QuizPreviewModal({ quiz, onClose, t }) {
  const [answers, setAnswers] = useState({});
  const setAnswer = (questionId, value) => setAnswers((prev) => ({ ...prev, [questionId]: value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div aria-hidden="true" onClick={onClose} className="absolute inset-0 bg-black/50" />
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl"
        style={{ backgroundColor: 'var(--bg-card)', color: 'var(--text-primary)' }}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 px-5 py-3.5 border-b bg-accent-soft" style={{ borderColor: 'var(--border-ui)' }}>
          <span className="inline-flex items-center gap-2 text-xs font-black text-fg uppercase tracking-wide">
            <Eye className="w-4 h-4 text-accent" />
            {t('instructor.quizPreviewBadge')}
          </span>
          <button type="button" onClick={onClose} aria-label={t('instructor.quizCancelBtn')} className="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 flex flex-col gap-4">
          <div>
            <h2 className="font-display text-lg font-bold text-fg">{quiz.title}</h2>
            {quiz.description && <p className="text-xs text-fg-muted mt-1">{quiz.description}</p>}
            <p className="text-[11px] text-fg-muted mt-1 font-mono-code">
              {t('studentQuizzes.timeLimitLabel', { n: quiz.timeLimitMinutes })}
            </p>
          </div>

          {quiz.questions.length === 0 ? (
            <p className="text-xs text-fg-muted">{t('instructor.quizEmptyQuestions')}</p>
          ) : (
            <div className="flex flex-col gap-4">
              {quiz.questions.map((question, index) => (
                <div key={question.id} className="rounded-lg border p-4" style={{ borderColor: 'var(--border-ui)' }}>
                  <p className="text-[10px] font-mono text-fg-muted mb-1">
                    {index + 1}. {t('instructor.quizMaxPoints', { n: question.points })}
                  </p>
                  <p className="text-sm font-semibold text-fg mb-3">{question.questionText}</p>
                  {question.questionType === 'MULTIPLE_CHOICE' && (
                    <div className="flex flex-col gap-2">
                      {question.options.map((option, optionIndex) => {
                        const isCorrect = option === question.correctAnswer;
                        return (
                          <button
                            key={option}
                            type="button"
                            className="text-left rounded-md border px-3 py-2 text-sm flex items-center justify-between gap-2"
                            style={{
                              borderColor: answers[question.id] === option ? 'var(--accent)' : 'var(--border-ui)',
                              background: answers[question.id] === option ? 'var(--accent-soft)' : 'var(--surface)',
                            }}
                            onClick={() => setAnswer(question.id, option)}
                          >
                            <span className="flex items-start gap-2">
                              <span className="font-mono-code font-bold shrink-0">{OPTION_LETTERS[optionIndex] || optionIndex + 1}.</span>
                              <span>{option}</span>
                            </span>
                            {isCorrect && <Check size={14} className="text-success-ink dark:text-emerald-400 shrink-0" />}
                          </button>
                        );
                      })}
                    </div>
                  )}
                  {question.questionType === 'TRUE_FALSE' && (
                    <div className="flex gap-2">
                      {question.options.map((option) => {
                        const isCorrect = option === question.correctAnswer;
                        return (
                          <button
                            key={option}
                            type="button"
                            className="rounded-md border px-4 py-2 text-sm inline-flex items-center gap-1.5"
                            style={{
                              borderColor: answers[question.id] === option ? 'var(--accent)' : 'var(--border-ui)',
                              background: answers[question.id] === option ? 'var(--accent-soft)' : 'var(--surface)',
                            }}
                            onClick={() => setAnswer(question.id, option)}
                          >
                            {option === 'True' ? t('studentQuizzes.trueLabel') : t('studentQuizzes.falseLabel')}
                            {isCorrect && <Check size={14} className="text-success-ink dark:text-emerald-400 shrink-0" />}
                          </button>
                        );
                      })}
                    </div>
                  )}
                  {question.questionType === 'SHORT_ANSWER' && (
                    <textarea
                      className="input text-sm w-full min-h-[72px]"
                      placeholder={t('studentQuizzes.shortAnswerPlaceholder')}
                      value={answers[question.id] || ''}
                      onChange={(event) => setAnswer(question.id, event.target.value)}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          <button
            type="button"
            className="px-4 py-2 rounded-xl text-xs font-black bg-accent hover:bg-accent-hover text-white shadow-xs transition-all cursor-pointer self-start"
            disabled
          >
            {t('studentQuizzes.submitBtn')}
          </button>
          <p className="text-[11px] text-fg-muted -mt-2">{t('instructor.quizPreviewHint')}</p>
        </div>
      </div>
    </div>
  );
}

function QuizBuilder({ quiz, onChange, onBack, onOpenProgress, t, lang, setError }) {
  const [meta, setMeta] = useState({
    title: quiz.title,
    description: quiz.description,
    time_limit_minutes: quiz.timeLimitMinutes,
    due_date: toDatetimeLocal(quiz.dueDate),
    opens_at: toDatetimeLocal(quiz.opensAt),
  });
  const [savingMeta, setSavingMeta] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [addingNew, setAddingNew] = useState(false);
  const [busy, setBusy] = useState(false);
  const [genCount, setGenCount] = useState(10);
  const [generating, setGenerating] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const updated = await getInstructorQuiz(quiz.id);
      onChange(updated);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    }
  }, [quiz.id, onChange, lang, t, setError]);

  const saveMeta = async () => {
    setSavingMeta(true);
    setError('');
    try {
      const updated = await updateQuiz(quiz.id, {
        title: meta.title,
        description: meta.description,
        time_limit_minutes: Number(meta.time_limit_minutes) || 1,
        due_date: meta.due_date || null,
        opens_at: meta.opens_at || null,
      });
      onChange(updated);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    } finally {
      setSavingMeta(false);
    }
  };

  const togglePublish = async () => {
    setBusy(true);
    setError('');
    try {
      const updated = await setQuizPublished(quiz.id, !quiz.isPublished);
      onChange(updated);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    } finally {
      setBusy(false);
    }
  };

  const removeQuiz = async () => {
    if (!window.confirm(t('instructor.quizDeleteConfirm'))) return;
    setBusy(true);
    setError('');
    try {
      await deleteQuiz(quiz.id);
      onBack();
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
      setBusy(false);
    }
  };

  const saveQuestion = async (payload) => {
    setBusy(true);
    setError('');
    try {
      if (editingId) {
        const updated = await updateQuizQuestion(quiz.id, editingId, payload);
        onChange(updated);
      } else {
        const updated = await addQuizQuestion(quiz.id, payload);
        onChange(updated);
      }
      setEditingId(null);
      setAddingNew(false);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    } finally {
      setBusy(false);
    }
  };

  const removeQuestion = async (questionId) => {
    setBusy(true);
    setError('');
    try {
      await deleteQuizQuestion(quiz.id, questionId);
      await refresh();
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    } finally {
      setBusy(false);
    }
  };

  const moveQuestion = async (index, direction) => {
    const ids = quiz.questions.map((q) => q.id);
    const target = index + direction;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    setBusy(true);
    setError('');
    try {
      const updated = await reorderQuizQuestions(quiz.id, ids);
      onChange(updated);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    } finally {
      setBusy(false);
    }
  };

  const runGenerate = async () => {
    setGenerating(true);
    setError('');
    try {
      const updated = await generateQuizQuestions(quiz.id, genCount);
      onChange(updated);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    } finally {
      setGenerating(false);
    }
  };

  const editingQuestion = editingId ? quiz.questions.find((q) => q.id === editingId) : null;

  return (
    <div className="flex flex-col gap-4">
      <button type="button" className="text-xs font-black text-accent hover:text-accent-hover self-start cursor-pointer" onClick={onBack}>
        {t('instructor.quizBackToList')}
      </button>

      <div className="rounded-2xl border border-line bg-surface-elevated p-4 flex flex-col gap-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="block">
            <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormTitle')}</span>
            <input
              className="input text-sm w-full mt-1.5"
              value={meta.title}
              onChange={(event) => setMeta((prev) => ({ ...prev, title: event.target.value }))}
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormTimeLimit')}</span>
            <input
              type="number"
              min="1"
              className="input text-sm w-full mt-1.5"
              value={meta.time_limit_minutes}
              onChange={(event) => setMeta((prev) => ({ ...prev, time_limit_minutes: event.target.value }))}
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormDescription')}</span>
            <textarea
              className="input text-sm w-full mt-1.5 min-h-[56px]"
              value={meta.description}
              onChange={(event) => setMeta((prev) => ({ ...prev, description: event.target.value }))}
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormOpensAt')}</span>
            <input
              type="datetime-local"
              className="input text-sm w-full mt-1.5"
              value={meta.opens_at}
              onChange={(event) => setMeta((prev) => ({ ...prev, opens_at: event.target.value }))}
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormDueDate')}</span>
            <input
              type="datetime-local"
              className="input text-sm w-full mt-1.5"
              value={meta.due_date}
              onChange={(event) => setMeta((prev) => ({ ...prev, due_date: event.target.value }))}
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="px-3 py-1.5 rounded-xl text-xs font-black border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer disabled:opacity-60"
            disabled={savingMeta}
            onClick={saveMeta}
          >
            {t('instructor.quizSaveMetaBtn')}
          </button>
          <button
            type="button"
            className={`px-3 py-1.5 rounded-xl text-xs font-black shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait ${
              quiz.isPublished
                ? 'border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                : 'bg-accent hover:bg-accent-hover text-white'
            }`}
            disabled={busy}
            onClick={togglePublish}
          >
            {quiz.isPublished ? t('instructor.quizUnpublishBtn') : t('instructor.quizPublishBtn')}
          </button>
          <button
            type="button"
            className="px-3 py-1.5 rounded-xl text-xs font-black border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer"
            onClick={onOpenProgress}
          >
            {t('instructor.quizProgressBtn')}
          </button>
          <button
            type="button"
            className="px-3 py-1.5 rounded-xl text-xs font-black border border-accent/40 text-accent hover:bg-accent-soft transition-all cursor-pointer inline-flex items-center gap-1.5"
            onClick={() => setPreviewing(true)}
          >
            <Eye size={12} /> {t('instructor.quizPreviewBtn')}
          </button>
          <button
            type="button"
            className="px-3 py-1.5 rounded-xl text-xs font-black border border-red-300 dark:border-red-800/60 text-danger-ink hover:bg-danger-soft dark:hover:bg-red-950/30 transition-all cursor-pointer disabled:opacity-60 inline-flex items-center gap-1"
            disabled={busy}
            onClick={removeQuiz}
          >
            <Trash2 size={12} /> {t('instructor.quizDeleteBtn')}
          </button>
        </div>
      </div>

      {previewing && <QuizPreviewModal quiz={quiz} onClose={() => setPreviewing(false)} t={t} />}

      <div className="rounded-2xl border border-line p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between border-b border-line pb-2">
          <h3 className="text-sm font-black text-fg font-serif-heading">
            {t('instructor.quizQuestionsTitle')} · {t('instructor.quizMaxPoints', { n: quiz.maxPoints })}
          </h3>
        </div>

        <div className="rounded-xl border border-accent/30 bg-accent-soft p-3.5 flex flex-col gap-2.5">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent shrink-0" />
            <p className="text-xs font-black text-fg">{t('instructor.quizGenerateTitle')}</p>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-400 font-medium -mt-1">{t('instructor.quizGenerateHint')}</p>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">{t('instructor.quizGenerateCountLabel')}</span>
              {GENERATE_COUNT_OPTIONS.map((n) => (
                <button
                  key={n}
                  type="button"
                  disabled={generating}
                  onClick={() => setGenCount(n)}
                  className={`w-8 h-8 rounded-lg text-xs font-black transition-all cursor-pointer disabled:opacity-60 ${
                    genCount === n
                      ? 'bg-accent text-white shadow-xs'
                      : 'bg-white dark:bg-[#1C1A16] border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
            <button
              type="button"
              className="px-3.5 py-1.5 rounded-xl text-xs font-black bg-accent hover:bg-accent-hover text-white shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait inline-flex items-center gap-1.5"
              disabled={generating}
              onClick={runGenerate}
            >
              {generating ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
              {generating ? t('instructor.quizGenerating') : t('instructor.quizGenerateBtn')}
            </button>
          </div>
        </div>

        {quiz.questions.length === 0 && !addingNew && (
          <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
            {t('instructor.quizEmptyQuestions')}
          </div>
        )}

        <div className="flex flex-col gap-3">
          {quiz.questions.map((question, index) =>
            editingId === question.id ? (
              <QuestionForm
                key={question.id}
                initial={{
                  question_text: question.questionText,
                  question_type: question.questionType,
                  options: question.questionType === 'MULTIPLE_CHOICE' ? question.options : ['', ''],
                  correct_answer: question.questionType === 'TRUE_FALSE'
                    ? question.correctAnswer.toLowerCase()
                    : question.correctAnswer,
                  points: question.points,
                }}
                onSave={saveQuestion}
                onCancel={() => setEditingId(null)}
                t={t}
                saving={busy}
              />
            ) : (
              <div key={question.id} className="rounded-xl border border-line p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-black uppercase tracking-wide text-accent font-mono-code">
                      {t(QUESTION_TYPES.find((qt) => qt.id === question.questionType)?.labelKey || '')} ·{' '}
                      {t('instructor.quizMaxPoints', { n: question.points })}
                    </p>
                    <p className="text-sm text-fg mt-1">{question.questionText}</p>
                    {question.questionType === 'MULTIPLE_CHOICE' && (
                      <ul className="mt-1.5 text-xs text-fg-secondary space-y-0.5">
                        {question.options.map((opt, optIndex) => (
                          <li key={opt} className={`flex gap-1.5 ${opt === question.correctAnswer ? 'font-bold text-emerald-600 dark:text-emerald-400' : ''}`}>
                            <span className="font-mono-code shrink-0">{OPTION_LETTERS[optIndex] || optIndex + 1}.</span>
                            <span>{opt}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {question.questionType === 'TRUE_FALSE' && (
                      <p className="mt-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        {question.correctAnswer === 'True' ? t('studentQuizzes.trueLabel') : t('studentQuizzes.falseLabel')}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <div className="flex gap-1">
                      <button
                        type="button"
                        aria-label={t('instructor.quizMoveUp')}
                        disabled={index === 0 || busy}
                        className="btn-ghost p-1 disabled:opacity-30"
                        onClick={() => moveQuestion(index, -1)}
                      >
                        <ChevronUp size={14} />
                      </button>
                      <button
                        type="button"
                        aria-label={t('instructor.quizMoveDown')}
                        disabled={index === quiz.questions.length - 1 || busy}
                        className="btn-ghost p-1 disabled:opacity-30"
                        onClick={() => moveQuestion(index, 1)}
                      >
                        <ChevronDown size={14} />
                      </button>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="text-[11px] font-black text-accent hover:text-accent-hover cursor-pointer"
                        onClick={() => { setEditingId(question.id); setAddingNew(false); }}
                      >
                        {t('instructor.quizEditBtn')}
                      </button>
                      <button
                        type="button"
                        className="text-[11px] font-black text-danger-ink hover:text-red-800 dark:hover:text-red-300 cursor-pointer"
                        onClick={() => removeQuestion(question.id)}
                      >
                        {t('instructor.quizDeleteQuestionBtn')}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ),
          )}
        </div>

        {addingNew ? (
          <QuestionForm onSave={saveQuestion} onCancel={() => setAddingNew(false)} t={t} saving={busy} />
        ) : (
          <button
            type="button"
            className="px-3 py-1.5 rounded-xl text-xs font-black border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer self-start inline-flex items-center gap-1.5"
            onClick={() => { setAddingNew(true); setEditingId(null); }}
          >
            <Plus size={12} /> {t('instructor.quizAddQuestionBtn')}
          </button>
        )}
      </div>
    </div>
  );
}

function QuizProgress({ quizId, onBack, t, lang, setError }) {
  const [data, setData] = useState(null);
  const [gradingId, setGradingId] = useState(null);
  const [scoreDrafts, setScoreDrafts] = useState({});
  const [feedbackDraft, setFeedbackDraft] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const result = await getQuizProgress(quizId);
      setData(result);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    }
  }, [quizId, lang, t, setError]);

  useEffect(() => {
    load();
  }, [load]);

  if (!data) return <p className="text-xs text-fg-muted">{t('states.loadingTitle')}</p>;

  const shortAnswerQuestions = data.quiz.questions.filter((q) => q.questionType === 'SHORT_ANSWER');

  const startGrading = (row) => {
    setGradingId(row.submissionId);
    const drafts = {};
    shortAnswerQuestions.forEach((q) => {
      const existing = row.answers.find((a) => a.id === q.id);
      drafts[q.id] = existing?.pointsAwarded ?? '';
    });
    setScoreDrafts(drafts);
    setFeedbackDraft('');
  };

  const saveGrade = async (submissionId) => {
    setBusy(true);
    setError('');
    try {
      const scores = {};
      Object.entries(scoreDrafts).forEach(([qid, value]) => {
        if (value !== '') scores[qid] = Number(value);
      });
      const result = await gradeQuizSubmission(quizId, submissionId, { scores, feedback: feedbackDraft || null });
      setData(result);
      setGradingId(null);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <button type="button" className="text-xs font-black text-accent hover:text-accent-hover self-start cursor-pointer" onClick={onBack}>
        {t('instructor.quizBackToList')}
      </button>
      <div className="flex items-center justify-between flex-wrap gap-2 border-b border-line pb-3">
        <h3 className="text-sm font-black text-fg font-serif-heading">
          {t('instructor.quizProgressTitle')} — {data.quiz.title}
        </h3>
        <span className="font-mono-code text-xs text-accent font-black">
          {t('instructor.quizSubmittedCount', { submitted: data.submittedCount, total: data.totalStudents })}
        </span>
      </div>

      {data.roster.length === 0 ? (
        <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
          {t('instructor.quizRosterEmpty')}
        </div>
      ) : (
        <ul className="divide-y divide-line border border-line rounded-2xl max-h-[32rem] overflow-y-auto">
          {data.roster.map((row) => (
            <li key={row.studentId} className="px-3 py-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="text-sm font-black text-fg">{row.studentName}</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">{row.studentEmail}</p>
                </div>
                <div className="flex items-center gap-2">
                  {row.grade != null && (
                    <span className="font-mono-code text-xs font-black text-fg">
                      {t('instructor.quizGradeLabel')}: {row.grade}%
                    </span>
                  )}
                  <span
                    className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase font-mono-code ${
                      row.status === 'graded'
                        ? 'bg-success-soft text-success-ink dark:bg-emerald-950/40 dark:text-emerald-300'
                        : row.status === 'pending_review'
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                    }`}
                  >
                    {t(`instructor.quizStatus${row.status === 'not_started' ? 'NotStarted' : row.status === 'pending_review' ? 'PendingReview' : 'Graded'}`)}
                  </span>
                </div>
              </div>

              {row.answers.length > 0 && (
                <div className="mt-2 flex flex-col gap-1.5">
                  {row.answers.map((a) => (
                    <div key={a.id} className="text-[11px] text-fg-secondary flex items-center justify-between gap-2">
                      <span className="truncate">{a.questionText}</span>
                      <span
                        className={`shrink-0 font-bold ${
                          a.correct === true
                            ? 'text-success-ink dark:text-emerald-400'
                            : a.correct === false
                              ? 'text-danger-ink dark:text-red-400'
                              : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {a.correct === true
                          ? t('instructor.quizAnswerCorrect')
                          : a.correct === false
                            ? t('instructor.quizAnswerIncorrect')
                            : t('instructor.quizAnswerPending')}
                        {a.pointsAwarded != null ? ` (${a.pointsAwarded}/${a.points})` : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {row.status === 'pending_review' && (
                gradingId === row.submissionId ? (
                  <div className="mt-3 rounded-xl border border-line bg-surface-elevated p-3 flex flex-col gap-2">
                    {shortAnswerQuestions.map((q) => {
                      const answer = row.answers.find((a) => a.id === q.id);
                      return (
                        <div key={q.id} className="flex flex-col gap-1">
                          <p className="text-xs text-fg-secondary">{q.questionText}</p>
                          <p className="text-xs italic text-fg-muted">
                            {t('instructor.quizYourAnswerLabel')}: {answer?.myAnswer || '—'}
                          </p>
                          <input
                            type="number"
                            min="0"
                            max={q.points}
                            step="0.5"
                            className="input text-xs w-28"
                            placeholder={t('instructor.quizPointsLabel')}
                            value={scoreDrafts[q.id] ?? ''}
                            onChange={(event) =>
                              setScoreDrafts((prev) => ({ ...prev, [q.id]: event.target.value }))
                            }
                          />
                        </div>
                      );
                    })}
                    <textarea
                      className="input text-xs w-full min-h-[48px]"
                      placeholder={t('instructor.quizFeedbackLabel')}
                      value={feedbackDraft}
                      onChange={(event) => setFeedbackDraft(event.target.value)}
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="px-3 py-1.5 rounded-xl text-xs font-black bg-accent hover:bg-accent-hover text-white shadow-xs transition-all cursor-pointer disabled:opacity-60"
                        disabled={busy}
                        onClick={() => saveGrade(row.submissionId)}
                      >
                        {t('instructor.quizSaveGradeBtn')}
                      </button>
                      <button
                        type="button"
                        className="px-3 py-1.5 rounded-xl text-xs font-black border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer"
                        onClick={() => setGradingId(null)}
                      >
                        {t('instructor.quizCancelBtn')}
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="mt-2 text-xs font-black text-accent hover:text-accent-hover cursor-pointer"
                    onClick={() => startGrading(row)}
                  >
                    {t('instructor.quizGradeShortAnswerBtn')}
                  </button>
                )
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function InstructorQuizManager() {
  const { t, lang } = useLanguage();
  const [classes, setClasses] = useState([]);
  const [sectionId, setSectionId] = useState('');
  const [quizzes, setQuizzes] = useState([]);
  const [view, setView] = useState('list');
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({ title: '', description: '', time_limit_minutes: 15, due_date: '' });

  const loadClasses = useCallback(async () => {
    setError('');
    try {
      const payload = await listInstructorQuizClasses();
      const rows = payload?.classes || [];
      setClasses(rows);
      setSectionId((current) => (current && rows.some((c) => c.sectionId === current) ? current : rows[0]?.sectionId || ''));
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    }
  }, [lang, t]);

  useEffect(() => {
    loadClasses();
  }, [loadClasses]);

  const loadQuizzes = useCallback(async () => {
    if (!sectionId) return;
    setError('');
    try {
      const payload = await listInstructorQuizzes(sectionId);
      setQuizzes(payload?.quizzes || []);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    }
  }, [sectionId, lang, t]);

  useEffect(() => {
    loadQuizzes();
  }, [loadQuizzes]);

  const openQuiz = async (quizId, targetView = 'builder') => {
    setError('');
    try {
      const detail = await getInstructorQuiz(quizId);
      setActiveQuiz(detail);
      setView(targetView);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    }
  };

  const backToList = () => {
    setView('list');
    setActiveQuiz(null);
    loadQuizzes();
  };

  const submitCreate = async () => {
    if (!createForm.title.trim() || !sectionId) return;
    setError('');
    try {
      const created = await createQuiz({
        section_id: sectionId,
        title: createForm.title,
        description: createForm.description,
        time_limit_minutes: Number(createForm.time_limit_minutes) || 15,
        due_date: createForm.due_date || null,
      });
      setCreating(false);
      setCreateForm({ title: '', description: '', time_limit_minutes: 15, due_date: '' });
      setActiveQuiz(created);
      setView('builder');
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.quizError'));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="bg-surface-elevated border border-line rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-1 min-w-0">
          <h1 className="text-2xl font-black text-fg font-serif-heading">{t('instructor.quizTitle')}</h1>
          <p className="text-xs text-fg-muted font-medium">{t('instructor.quizHint')}</p>
        </div>
      </div>

      <div className="card p-6 space-y-4 text-left">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <h2 className="text-base font-black text-fg flex items-center gap-2 font-serif-heading">
            <BookOpen className="w-5 h-5 text-accent" />
            <span>{t('instructor.quizTitle')}</span>
          </h2>
        </div>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-xl flex items-start gap-2" role="alert">
            <span className="text-[11px] font-bold text-red-900 dark:text-red-300">{error}</span>
          </div>
        )}

        {view === 'list' && (
          <div className="flex flex-col gap-4">
            <label className="block max-w-sm">
              <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizClassLabel')}</span>
              <select
                className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
                value={sectionId}
                onChange={(event) => setSectionId(event.target.value)}
              >
                <option value="">{t('instructor.quizSelectClass')}</option>
                {classes.map((cls) => (
                  <option key={cls.sectionId} value={cls.sectionId}>
                    {cls.courseCode} · {cls.sectionCode} ({cls.studentCount})
                  </option>
                ))}
              </select>
            </label>

            {creating ? (
              <div className="rounded-2xl border border-line bg-surface-elevated p-4 flex flex-col gap-3 max-w-lg">
                <label className="block">
                  <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormTitle')}</span>
                  <input
                    className="input text-sm w-full mt-1.5"
                    value={createForm.title}
                    onChange={(event) => setCreateForm((prev) => ({ ...prev, title: event.target.value }))}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormDescription')}</span>
                  <textarea
                    className="input text-sm w-full mt-1.5 min-h-[56px]"
                    value={createForm.description}
                    onChange={(event) => setCreateForm((prev) => ({ ...prev, description: event.target.value }))}
                  />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block">
                    <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormTimeLimit')}</span>
                    <input
                      type="number"
                      min="1"
                      className="input text-sm w-full mt-1.5"
                      value={createForm.time_limit_minutes}
                      onChange={(event) => setCreateForm((prev) => ({ ...prev, time_limit_minutes: event.target.value }))}
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-fg-secondary">{t('instructor.quizFormDueDate')}</span>
                    <input
                      type="datetime-local"
                      className="input text-sm w-full mt-1.5"
                      value={createForm.due_date}
                      onChange={(event) => setCreateForm((prev) => ({ ...prev, due_date: event.target.value }))}
                    />
                  </label>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="px-4 py-2 rounded-xl bg-accent hover:bg-accent-hover text-white text-xs font-black shadow-xs transition-all cursor-pointer"
                    onClick={submitCreate}
                  >
                    {t('instructor.quizCreateBtn')}
                  </button>
                  <button
                    type="button"
                    className="px-4 py-2 rounded-xl text-xs font-black border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer"
                    onClick={() => setCreating(false)}
                  >
                    {t('instructor.quizCancelBtn')}
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-accent hover:bg-accent-hover text-white text-xs font-black shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait self-start inline-flex items-center gap-1.5"
                disabled={!sectionId}
                onClick={() => setCreating(true)}
              >
                <Plus size={12} /> {t('instructor.quizCreateBtn')}
              </button>
            )}

            {quizzes.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
                {t('instructor.quizListEmpty')}
              </div>
            ) : (
              <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {quizzes.map((quiz) => (
                  <li key={quiz.id}>
                    <button
                      type="button"
                      className="w-full text-left rounded-2xl border border-line p-3 hover:border-accent/60 transition-all hover:scale-[1.01] cursor-pointer"
                      onClick={() => openQuiz(quiz.id)}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <p className="text-sm font-black text-fg truncate">{quiz.title}</p>
                        <span
                          className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase font-mono-code shrink-0 ${
                            quiz.isPublished
                              ? 'bg-success-soft text-success-ink dark:bg-emerald-950/40 dark:text-emerald-300'
                              : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                          }`}
                        >
                          {quiz.isPublished ? t('instructor.quizStatusPublished') : t('instructor.quizStatusDraft')}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">{t('instructor.quizCardQuestions', { n: quiz.questionCount })}</p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {view === 'builder' && activeQuiz && (
          <QuizBuilder
            quiz={activeQuiz}
            onChange={setActiveQuiz}
            onBack={backToList}
            onOpenProgress={() => setView('progress')}
            t={t}
            lang={lang}
            setError={setError}
          />
        )}

        {view === 'progress' && activeQuiz && (
          <QuizProgress quizId={activeQuiz.id} onBack={() => openQuiz(activeQuiz.id, 'builder')} t={t} lang={lang} setError={setError} />
        )}
      </div>
    </div>
  );
}
