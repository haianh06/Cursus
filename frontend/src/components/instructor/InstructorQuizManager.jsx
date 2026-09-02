import React, { useEffect, useMemo, useState } from 'react';
import {
  Plus, Check, Sparkles, Trash2, Send, Undo2,
  ChevronLeft, ChevronRight, Info, BookOpen, Clock, X,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { GvStickyHeader, GvPager, usePaged } from './GvChrome';
import {
  createQuiz, deleteQuiz, generateQuizQuestions, getInstructorQuiz,
  listInstructorQuizClasses, listInstructorQuizzes, setQuizPublished,
  userFacingApiError,
} from '../../lib/api';
import { formatDetectedAt } from '../../lib/riskLabels';
import ErrorState from '../shared/ErrorState';
import EmptyState from '../shared/EmptyState';

/**
 * Quan ly Quiz — bo cuc master-detail: danh sach ben trai, xem truoc MOT cau
 * hoi ben phai. Khong do ca 10-20 cau vao panel chi tiet cung luc.
 *
 * Ve cac tab trang thai: Quiz trong DB chi co `is_published` (bool) cong voi
 * `status` suy ra tu moc thoi gian (scheduled/open/closed) — khong co buoc
 * "cho duyet" nao trong backend. Nen o day dung 3 tab that:
 *   Nhap      = chua phat hanh
 *   Da phat hanh = da phat hanh va con han
 *   Luu tru   = da phat hanh va da dong
 * Them tab "Cho duyet" nhu anh mau se la mot trang thai khong ton tai o
 * backend, va nut "Duyet/Tu choi" se khong luu duoc gi. Hanh dong "Duyet"
 * trong anh mau tuong ung voi Phat hanh o day.
 *
 * Ngan hang cau hoi khong luu phan giai thich va nguon giao trinh cho tung
 * cau (QuizQuestion chi co question_text / options / correct_answer /
 * points / order_index), nen hai muc do trong anh mau chua hien duoc.
 */

const TABS = [
  { key: 'DRAFT', labelKey: 'qzTabDraft' },
  { key: 'PUBLISHED', labelKey: 'qzTabPublished' },
  { key: 'ARCHIVED', labelKey: 'qzTabArchived' },
];

function bucketOf(quiz) {
  if (!quiz.isPublished) return 'DRAFT';
  return quiz.status === 'closed' ? 'ARCHIVED' : 'PUBLISHED';
}

export default function InstructorQuizManager() {
  const { t, lang } = useLanguage();

  const [classes, setClasses] = useState([]);
  const [sectionId, setSectionId] = useState(null);
  const [quizzes, setQuizzes] = useState([]);
  const [tab, setTab] = useState('DRAFT');
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [detailTab, setDetailTab] = useState('PREVIEW');

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [busy, setBusy] = useState(null);
  const [notice, setNotice] = useState(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    let cancelled = false;
    listInstructorQuizClasses()
      .then((data) => {
        if (cancelled) return;
        const list = data.classes || [];
        setClasses(list);
        setSectionId((prev) => prev || list[0]?.sectionId || null);
      })
      .catch((err) => { if (!cancelled) setLoadError(userFacingApiError(err).message); });
    return () => { cancelled = true; };
  }, []);

  const loadQuizzes = async (keepSelection = false) => {
    if (!sectionId) { setIsLoading(false); return; }
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await listInstructorQuizzes(sectionId);
      const list = data.quizzes || data || [];
      setQuizzes(list);
      if (!keepSelection) setSelectedId(null);
    } catch (err) {
      setLoadError(userFacingApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadQuizzes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionId]);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return undefined; }
    let cancelled = false;
    setQuestionIndex(0);
    getInstructorQuiz(selectedId)
      .then((data) => { if (!cancelled) setDetail(data); })
      .catch((err) => { if (!cancelled) setNotice({ tone: 'error', text: userFacingApiError(err).message }); });
    return () => { cancelled = true; };
  }, [selectedId]);

  const counts = useMemo(() => {
    const acc = { DRAFT: 0, PUBLISHED: 0, ARCHIVED: 0 };
    quizzes.forEach((quiz) => { acc[bucketOf(quiz)] += 1; });
    return acc;
  }, [quizzes]);

  const visible = useMemo(
    () => quizzes.filter((quiz) => bucketOf(quiz) === tab),
    [quizzes, tab]
  );

  const quizPage = usePaged(visible, 8);

  const questions = detail?.questions || [];
  const question = questions[questionIndex] || null;

  const runAction = async (key, fn, successText) => {
    setBusy(key);
    setNotice(null);
    try {
      const result = await fn();
      if (successText) setNotice({ tone: 'ok', text: successText(result) });
      return result;
    } catch (err) {
      setNotice({ tone: 'error', text: userFacingApiError(err).message });
      return null;
    } finally {
      setBusy(null);
    }
  };

  const togglePublish = (quiz) => runAction('publish', async () => {
    await setQuizPublished(quiz.id, !quiz.isPublished);
    await loadQuizzes(true);
    const fresh = await getInstructorQuiz(quiz.id);
    setDetail(fresh);
  });

  const removeQuiz = (quiz) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(t('instructor.qzDeleteConfirm'))) return;
    runAction('delete', async () => {
      await deleteQuiz(quiz.id);
      setSelectedId(null);
      await loadQuizzes();
    });
  };

  const generate = (quiz) => runAction(
    'generate',
    async () => {
      const result = await generateQuizQuestions(quiz.id, 3);
      const fresh = await getInstructorQuiz(quiz.id);
      setDetail(fresh);
      await loadQuizzes(true);
      return result;
    },
    (result) => t('instructor.qzAiDone').replace(
      '{n}', String((result?.questions || result?.added || []).length || 3)
    )
  );

  const create = async (event) => {
    event.preventDefault();
    await runAction('create', async () => {
      const created = await createQuiz({
        section_id: sectionId,
        title: newTitle.trim(),
        description: '',
        time_limit_minutes: 15,
      });
      setIsCreateOpen(false);
      setNewTitle('');
      await loadQuizzes(true);
      if (created?.id) { setTab('DRAFT'); setSelectedId(created.id); }
    });
  };

  if (isLoading && !quizzes.length) {
    return (
      <div className="gv-ui p-7 space-y-4 animate-pulse">
        <div className="gv-panel" style={{ height: 92 }} />
        <div className="grid grid-cols-1 xl:grid-cols-[44fr_56fr] gap-4">
          <div className="gv-panel" style={{ height: 460 }} />
          <div className="gv-panel" style={{ height: 460 }} />
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="gv-ui p-7">
        <ErrorState
          title={t('states.errorTitle')}
          description={loadError}
          onRetry={() => loadQuizzes()}
          retryLabel={t('states.retryBtn')}
        />
      </div>
    );
  }

  return (
    <div className="gv-ui gv-page">
      <GvStickyHeader>
        <header className="gv-panel px-6 py-5 flex flex-col xl:flex-row xl:items-end gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="gv-page-title">{t('instructor.qzPageTitle')}</h1>
            <p className="gv-body-sm gv-muted mt-1.5">{t('instructor.qzPageSubtitle')}</p>
          </div>

          <label className="block shrink-0" style={{ width: 280 }}>
            <span className="gv-field-label">{t('instructor.dashClassField')}</span>
            <select className="gv-select" value={sectionId || ''}
              onChange={(e) => setSectionId(e.target.value)}>
              {classes.map((c) => (
                <option key={c.sectionId} value={c.sectionId}>
                  {c.courseCode} — {c.sectionCode}
                </option>
              ))}
            </select>
          </label>

          <button type="button" className="gv-btn gv-btn--teal gv-ctl shrink-0"
            onClick={() => setIsCreateOpen(true)}>
            <Plus size={16} /> {t('instructor.qzCreate')}
          </button>
        </header>

        {/* Tabs trang thai */}
        <div className="flex items-center gap-2 flex-wrap">
          {TABS.map((entry) => (
            <button
              key={entry.key}
              type="button"
              className={`gv-btn gv-ctl ${tab === entry.key ? 'gv-btn--teal-outline' : 'gv-btn--ghost'}`}
              onClick={() => { setTab(entry.key); setSelectedId(null); }}
            >
              {t(`instructor.${entry.labelKey}`)}
              <span className={`gv-badge gv-badge--${tab === entry.key ? 'teal' : 'neutral'}`}
                style={{ padding: '2px 8px' }}>
                {counts[entry.key]}
              </span>
            </button>
          ))}
        </div>
      </GvStickyHeader>

      <div className="gv-page__body">
        {notice && (
          <p className="gv-body-sm"
            style={{ color: notice.tone === 'ok' ? 'var(--gv-success)' : 'var(--gv-danger)' }}>
            {notice.text}
          </p>
        )}

        {isCreateOpen && (
          <form onSubmit={create} className="gv-filterbar">
            <label style={{ flex: '1 1 320px' }}>
              <span className="gv-field-label">{t('instructor.qzNewTitle')}</span>
              <input className="gv-select" style={{ cursor: 'text' }} value={newTitle}
                maxLength={160} required
                placeholder={t('instructor.qzNewTitlePlaceholder')}
                onChange={(e) => setNewTitle(e.target.value)} />
            </label>
            <button type="submit" className="gv-btn gv-btn--teal" disabled={busy === 'create'}>
              <Plus size={16} /> {t('instructor.qzCreate')}
            </button>
            <button type="button" className="gv-btn gv-btn--ghost" onClick={() => setIsCreateOpen(false)}
              aria-label={t('common.close')}>
              <X size={16} />
            </button>
          </form>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[44fr_56fr] items-start" style={{ gap: 16 }}>

          {/* --- Danh sach quiz --- */}
          <section className="gv-panel p-5 min-w-0">
            {visible.length === 0 ? (
              <EmptyState title={t('instructor.qzEmpty')} />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: 420 }}>
                  <thead>
                    <tr>
                      <th className="gv-th" style={{ width: 28 }} />
                      <th className="gv-th">{t('instructor.qzColName')}</th>
                      <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.qzColCount')}</th>
                      <th className="gv-th" style={{ textAlign: 'right' }}>{t('instructor.qzColDue')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {quizPage.slice.map((quiz) => {
                      const selected = selectedId === quiz.id;
                      return (
                        <tr key={quiz.id} className="gv-row cursor-pointer"
                          style={selected ? { background: 'var(--gv-teal-soft)' } : undefined}
                          onClick={() => setSelectedId(quiz.id)}>
                          <td className="gv-td">
                            <span style={{
                              display: 'inline-flex', width: 16, height: 16, borderRadius: 999,
                              border: `2px solid ${selected ? 'var(--gv-teal)' : 'var(--gv-border)'}`,
                              alignItems: 'center', justifyContent: 'center',
                            }}>
                              {selected && (
                                <span style={{
                                  width: 7, height: 7, borderRadius: 999, background: 'var(--gv-teal)',
                                }} />
                              )}
                            </span>
                          </td>
                          <td className="gv-td" style={{ paddingRight: 12 }}>
                            <span className="block" style={{
                              fontWeight: 600, maxWidth: 240,
                              display: '-webkit-box', WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical', overflow: 'hidden',
                            }}>
                              {quiz.title}
                            </span>
                            <span className="block gv-meta">{quiz.courseCode}</span>
                          </td>
                          <td className="gv-td" style={{ textAlign: 'right', fontWeight: 600 }}>
                            {quiz.questionCount}
                          </td>
                          <td className="gv-td gv-meta" style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                            {quiz.dueDate ? formatDetectedAt(quiz.dueDate, lang) : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <GvPager {...quizPage} onChange={quizPage.setPage}
              label={t('instructor.qzPageTitle')} />
          </section>

          {/* --- Xem truoc --- */}
          <section className="gv-panel p-6 min-w-0">
            {!detail ? (
              <p className="gv-body-sm gv-muted py-14 text-center">{t('instructor.qzPickOne')}</p>
            ) : (
              <>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <h2 className="gv-section-title">{detail.title}</h2>
                      <span className={`gv-badge gv-badge--${detail.isPublished ? 'teal' : 'neutral'}`}>
                        {t(`instructor.${detail.isPublished
                          ? (detail.status === 'closed' ? 'qzTabArchived' : 'qzTabPublished')
                          : 'qzTabDraft'}`)}
                      </span>
                    </div>
                    <p className="gv-meta mt-1.5 flex items-center flex-wrap" style={{ gap: 14 }}>
                      <span className="flex items-center gap-1.5">
                        <BookOpen size={13} /> {detail.questionCount} {t('instructor.qzQuestions')}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock size={13} /> {detail.timeLimitMinutes} {t('instructor.qzMinutes')}
                      </span>
                      <span>{detail.courseCode} · {detail.sectionCode}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 mt-4 mb-4">
                  {[['PREVIEW', 'qzTabPreview'], ['INFO', 'qzTabInfo']].map(([key, labelKey]) => (
                    <button key={key} type="button"
                      className={`gv-btn ${detailTab === key ? 'gv-btn--teal-outline' : 'gv-btn--ghost'}`}
                      style={{ padding: '7px 14px' }}
                      onClick={() => setDetailTab(key)}>
                      {t(`instructor.${labelKey}`)}
                    </button>
                  ))}
                </div>

                {detailTab === 'PREVIEW' ? (
                  questions.length === 0 ? (
                    <EmptyState title={t('instructor.qzNoQuestion')} />
                  ) : (
                    <div className="gv-card p-5">
                      <div className="flex items-center justify-between gap-3 mb-3">
                        <span className="flex items-center gap-2.5">
                          <span className="gv-body-sm" style={{ fontWeight: 700 }}>
                            {t('instructor.qzQuestion')} {questionIndex + 1}
                          </span>
                          <span className="gv-badge gv-badge--neutral">
                            {t('instructor.qzTypeMultiple')}
                          </span>
                        </span>
                        <span className="flex items-center gap-2">
                          <button type="button" className="gv-btn gv-btn--ghost" style={{ padding: 7 }}
                            disabled={questionIndex === 0}
                            onClick={() => setQuestionIndex((i) => Math.max(0, i - 1))}
                            aria-label={t('instructor.qzPrevQuestion')}>
                            <ChevronLeft size={15} />
                          </button>
                          <span className="gv-meta">{questionIndex + 1}/{questions.length}</span>
                          <button type="button" className="gv-btn gv-btn--ghost" style={{ padding: 7 }}
                            disabled={questionIndex >= questions.length - 1}
                            onClick={() => setQuestionIndex((i) => Math.min(questions.length - 1, i + 1))}
                            aria-label={t('instructor.qzNextQuestion')}>
                            <ChevronRight size={15} />
                          </button>
                        </span>
                      </div>

                      <p className="gv-body" style={{ fontWeight: 600 }}>{question.questionText}</p>

                      <ul className="flex flex-col mt-3" style={{ gap: 8 }}>
                        {Object.entries(question.options || {}).map(([key, text]) => {
                          const correct = String(question.correctAnswer).trim() === key;
                          return (
                            <li key={key}
                              className="flex items-center gap-2.5"
                              style={{
                                border: `1px solid ${correct ? 'var(--gv-teal)' : 'var(--gv-border)'}`,
                                background: correct ? 'var(--gv-teal-soft)' : 'var(--gv-card)',
                                borderRadius: 10, padding: '10px 12px', fontSize: 14,
                              }}>
                              <span style={{
                                width: 18, height: 18, borderRadius: 999, flex: '0 0 auto',
                                border: `2px solid ${correct ? 'var(--gv-teal)' : 'var(--gv-border)'}`,
                              }} />
                              <span className="flex-1">{key}. {text}</span>
                              {correct && <Check size={16} style={{ color: 'var(--gv-teal)' }} />}
                            </li>
                          );
                        })}
                      </ul>

                      <p className="gv-meta mt-3 flex items-start gap-1.5">
                        <Info size={13} className="mt-0.5 shrink-0" />
                        {t('instructor.qzNoExplanation')}
                      </p>
                    </div>
                  )
                ) : (
                  <div className="flex flex-col" style={{ gap: 10 }}>
                    {[
                      [t('instructor.qzInfoDescription'), detail.description || '—'],
                      [t('instructor.qzInfoTimeLimit'), `${detail.timeLimitMinutes} ${t('instructor.qzMinutes')}`],
                      [t('instructor.qzInfoMaxPoints'), detail.maxPoints],
                      [t('instructor.qzInfoOpensAt'), detail.opensAt ? formatDetectedAt(detail.opensAt, lang) : '—'],
                      [t('instructor.qzColDue'), detail.dueDate ? formatDetectedAt(detail.dueDate, lang) : '—'],
                      [t('instructor.qzInfoClass'), `${detail.courseCode} · ${detail.sectionCode}`],
                    ].map(([label, value]) => (
                      <div key={label} className="gv-stat flex items-center justify-between gap-3">
                        <span className="gv-body-sm gv-muted">{label}</span>
                        <span className="gv-body-sm" style={{ fontWeight: 600, textAlign: 'right' }}>{value}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Khoi AI — nen amber rieng de phan biet voi noi dung GV soan */}
                <div className="gv-note mt-4">
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <span className="flex items-center gap-2">
                      <Sparkles size={16} style={{ color: 'var(--gv-amber)' }} />
                      <span style={{ fontWeight: 700 }}>{t('instructor.qzAiTitle')}</span>
                    </span>
                    <button type="button" className="gv-btn gv-btn--ghost"
                      style={{ padding: '7px 12px' }}
                      disabled={busy === 'generate'}
                      onClick={() => generate(detail)}>
                      <Sparkles size={15} />
                      {busy === 'generate' ? t('instructor.qzAiGenerating') : t('instructor.qzAiGenerate')}
                    </button>
                  </div>
                  <p className="gv-body-sm gv-muted mt-2">{t('instructor.qzAiHint')}</p>
                </div>

                <div className="flex items-center gap-2 mt-4 flex-wrap">
                  <button type="button" className="gv-btn gv-btn--teal"
                    disabled={busy === 'publish'} onClick={() => togglePublish(detail)}>
                    {detail.isPublished
                      ? <><Undo2 size={16} /> {t('instructor.qzUnpublish')}</>
                      : <><Send size={16} /> {t('instructor.qzPublish')}</>}
                  </button>
                  <button type="button" className="gv-btn gv-btn--danger-outline"
                    style={{ marginLeft: 'auto' }}
                    disabled={busy === 'delete'} onClick={() => removeQuiz(detail)}>
                    <Trash2 size={16} /> {t('instructor.qzDelete')}
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
