import React, { useCallback, useEffect, useState } from 'react';
import { ClipboardCheck, ChevronLeft, Clock, CheckCircle2 } from 'lucide-react';
import Skeleton from '../shared/Skeleton';
import EmptyState from '../shared/EmptyState';
import { listStudentQuizzes, getStudentQuiz, submitStudentQuiz } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

const OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

const STATUS_LABEL_KEY = {
  not_started: 'studentQuizzes.statusNotStarted',
  pending_review: 'studentQuizzes.statusPendingReview',
  graded: 'studentQuizzes.statusGraded',
};

function QuizList({ quizzes, onOpen, t }) {
  if (quizzes.length === 0) {
    return <EmptyState icon={<ClipboardCheck size={40} className="text-fg-muted" />} title={t('studentQuizzes.empty')} />;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {quizzes.map((quiz) => (
        <button
          key={quiz.id}
          type="button"
          onClick={() => onOpen(quiz.id)}
          className="card p-4 text-left cursor-pointer hover:border-accent transition-colors"
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-bold text-fg">{quiz.title}</p>
            <span
              className={`shrink-0 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                quiz.myStatus === 'not_started'
                  ? 'bg-accent-soft text-accent'
                  : 'bg-success-soft text-success'
              }`}
            >
              {t(STATUS_LABEL_KEY[quiz.myStatus] || 'studentQuizzes.statusNotStarted')}
            </span>
          </div>
          {quiz.courseCode && (
            <p className="mt-1 text-[11px] text-fg-muted mono">{quiz.courseCode} · {quiz.sectionCode}</p>
          )}
          <p className="mt-2 flex items-center gap-1.5 text-[11px] text-fg-muted">
            <Clock size={12} />
            {t('studentQuizzes.timeLimitLabel', { n: quiz.timeLimitMinutes })}
          </p>
          {quiz.myGrade != null && (
            <p className="mt-1 text-[11px] font-bold text-success">
              {t('studentQuizzes.gradeLabel', { n: Math.round(quiz.myGrade) })}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}

function QuizTaker({ quizId, onBack, t, lang }) {
  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(() => {
    setError('');
    setLoading(true);
    getStudentQuiz(quizId)
      .then((data) => {
        setQuiz(data);
        setAnswers({});
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [quizId]);

  useEffect(() => {
    load();
  }, [load]);

  function submit() {
    setSubmitting(true);
    setError('');
    submitStudentQuiz(quizId, answers)
      .then((data) => setQuiz(data))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false));
  }

  const alreadySubmitted = quiz && quiz.myStatus !== 'not_started';
  const allAnswered = quiz && quiz.questions.every((q) => answers[q.id]?.trim());

  return (
    <div className="flex flex-col gap-4">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex w-fit items-center gap-1.5 text-xs font-semibold text-fg-secondary hover:text-fg cursor-pointer"
      >
        <ChevronLeft size={14} />
        {t('studentQuizzes.backToList')}
      </button>

      {loading ? (
        <Skeleton className="h-64 w-full rounded-2xl" />
      ) : error ? (
        <p className="text-xs text-danger">{error}</p>
      ) : quiz ? (
        <div className="card p-5 flex flex-col gap-4">
          <div>
            <h2 className="font-display text-lg font-bold text-fg">{quiz.title}</h2>
            {quiz.description && <p className="text-xs text-fg-muted mt-1">{quiz.description}</p>}
            <p className="text-[11px] text-fg-muted mt-1 mono">
              {t('studentQuizzes.timeLimitLabel', { n: quiz.timeLimitMinutes })}
            </p>
          </div>

          {alreadySubmitted && (
            <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success-soft p-3 text-xs text-success font-semibold">
              <CheckCircle2 size={14} />
              {t('studentQuizzes.gradeLabel', { n: Math.round(quiz.myGrade ?? 0) })}
            </div>
          )}

          <div className="flex flex-col gap-4">
            {quiz.questions.map((question, index) => {
              return (
                <div key={question.id} className="rounded-lg border border-line p-4">
                  <p className="text-[10px] font-mono text-fg-muted mb-1">
                    {index + 1}. {t('studentQuizzes.pointsLabel', { n: question.points })}
                  </p>
                  <p className="text-sm font-semibold text-fg mb-3">{question.questionText}</p>
                  <div className="flex flex-col gap-2">
                    {(question.options || []).map((option, optionIndex) => {
                      const selected = answers[question.id] === option;
                      const isCorrectOption = alreadySubmitted && option === question.correctAnswer;
                      return (
                        <button
                          key={option}
                          type="button"
                          disabled={alreadySubmitted}
                          onClick={() => setAnswers((prev) => ({ ...prev, [question.id]: option }))}
                          className={`text-left rounded-md border px-3 py-2 text-sm flex items-center gap-2 disabled:cursor-default ${
                            isCorrectOption
                              ? 'border-success bg-success-soft text-success'
                              : selected
                                ? 'border-accent bg-accent-soft text-fg'
                                : 'border-line bg-surface-elevated text-fg-secondary'
                          }`}
                        >
                          <span className="mono font-bold shrink-0">{OPTION_LETTERS[optionIndex] || optionIndex + 1}.</span>
                          <span>{option}</span>
                        </button>
                      );
                    })}
                  </div>
                  {alreadySubmitted && question.correct != null && (
                    <p className={`mt-2 text-[11px] font-semibold ${question.correct ? 'text-success' : 'text-danger'}`}>
                      {question.correct
                        ? t('studentQuizzes.answerCorrect')
                        : t('studentQuizzes.answerIncorrect')}
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          {!alreadySubmitted && (
            <button
              type="button"
              disabled={!allAnswered || submitting}
              onClick={submit}
              className="btn btn-accent text-xs px-4 py-2 self-start disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? t('studentQuizzes.submitting') : t('studentQuizzes.submitBtn')}
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default function StudentQuizzes() {
  const { t, lang } = useLanguage();
  const [quizzes, setQuizzes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openQuizId, setOpenQuizId] = useState(null);

  const load = useCallback(() => {
    setError('');
    return listStudentQuizzes()
      .then(setQuizzes)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (openQuizId) {
    return (
      <div className="flex flex-col gap-4 p-6 animate-fade-up">
        <QuizTaker
          quizId={openQuizId}
          onBack={() => {
            setOpenQuizId(null);
            load();
          }}
          t={t}
          lang={lang}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-6 animate-fade-up">
      <div>
        <h1 className="font-display text-xl font-bold text-fg flex items-center gap-2">
          <ClipboardCheck size={20} className="text-accent" />
          {t('studentQuizzes.title')}
        </h1>
        <p className="text-xs text-fg-muted mt-1">{t('studentQuizzes.subtitle')}</p>
      </div>

      {loading ? (
        <Skeleton className="h-40 w-full rounded-2xl" />
      ) : error ? (
        <p className="text-xs text-danger">{error}</p>
      ) : (
        <QuizList quizzes={quizzes || []} onOpen={setOpenQuizId} t={t} />
      )}
    </div>
  );
}
