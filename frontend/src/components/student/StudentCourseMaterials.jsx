import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, FileText, LoaderCircle } from 'lucide-react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { getStudentCourseDetail, getStudentCourseDocument, userFacingApiError } from '../../lib/api';

export default function StudentCourseMaterials() {
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const { courseId } = useParams();
  const [params] = useSearchParams();
  const [course, setCourse] = useState(null);
  const [selectedId, setSelectedId] = useState(params.get('doc') || '');
  const [content, setContent] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoadingList(true);
    setError('');
    getStudentCourseDetail(courseId)
      .then((payload) => {
        if (cancelled) return;
        setCourse(payload);
        const documents = payload?.documents || [];
        setSelectedId((current) => current || documents[0]?.id || '');
      })
      .catch((err) => {
        if (!cancelled) setError(userFacingApiError(err, lang).message || t('courseMaterials.loadError'));
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => { cancelled = true; };
  }, [courseId, lang, t]);

  const loadContent = useCallback(async (documentId) => {
    if (!documentId) return;
    setLoadingContent(true);
    setError('');
    try {
      setContent(await getStudentCourseDocument(courseId, documentId));
    } catch (err) {
      setContent(null);
      setError(userFacingApiError(err, lang).message || t('courseMaterials.loadError'));
    } finally {
      setLoadingContent(false);
    }
  }, [courseId, lang, t]);

  useEffect(() => {
    if (selectedId) loadContent(selectedId);
  }, [selectedId, loadContent]);

  const documents = course?.documents || [];

  return (
    <div className="flex max-w-5xl flex-col gap-6 p-6 animate-fade-up">
      <header className="flex flex-col gap-3 border-b border-line pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <FileText size={18} className="text-accent" aria-hidden="true" />
            <h1 className="font-display text-xl font-semibold text-fg">{t('courseMaterials.pageTitle')}</h1>
          </div>
          <p className="mono text-xs text-fg-muted">{course?.code || courseId}</p>
        </div>
        <button type="button" className="btn btn-outline gap-2 px-3 py-2 text-xs" onClick={() => navigate(-1)}>
          <ArrowLeft size={14} aria-hidden="true" />
          {t('courseMaterials.backBtn')}
        </button>
      </header>

      {error && (
        <div role="alert" className="rounded-lg border border-danger bg-danger-soft p-4 text-xs text-danger">
          {error}
        </div>
      )}

      {loadingList ? (
        <p className="inline-flex items-center gap-2 text-xs text-fg-muted">
          <LoaderCircle size={14} className="animate-spin" aria-hidden="true" />
          {t('courseMaterials.loading')}
        </p>
      ) : documents.length === 0 ? (
        <div className="card p-5 text-sm text-fg-muted">{t('courseMaterials.empty')}</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[minmax(220px,1fr)_2fr]">
          <ul className="flex flex-col gap-2" aria-label={t('courseMaterials.pageTitle')}>
            {documents.map((doc) => (
              <li key={doc.id}>
                <button
                  type="button"
                  className={`w-full rounded-lg border px-3 py-3 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ${doc.id === selectedId ? 'border-accent bg-accent-soft' : 'border-line bg-surface hover:border-accent'}`}
                  onClick={() => setSelectedId(doc.id)}
                >
                  <span className="block text-xs font-semibold text-fg">{doc.title}</span>
                  <span className="mono mt-1 block text-[10px] text-fg-muted">{doc.doc_type}</span>
                </button>
              </li>
            ))}
          </ul>
          <article className="card min-h-48 p-5" aria-live="polite">
            {loadingContent ? (
              <p className="inline-flex items-center gap-2 text-xs text-fg-muted">
                <LoaderCircle size={14} className="animate-spin" aria-hidden="true" />
                {t('courseMaterials.loading')}
              </p>
            ) : content ? (
              <div className="flex flex-col gap-3">
                <h2 className="font-display text-base font-semibold text-fg">{content.title}</h2>
                <p className="whitespace-pre-wrap text-sm leading-7 text-fg-secondary">{content.content}</p>
              </div>
            ) : (
              <p className="text-xs text-fg-muted">{t('courseMaterials.selectHint')}</p>
            )}
          </article>
        </div>
      )}
    </div>
  );
}
