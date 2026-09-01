import React, { useMemo, useState } from 'react';
import { Database, Plus, Trash2, AlertCircle, CheckCircle2, Clock3, X, BookOpen, FileText, Search } from 'lucide-react';
import { useCursus } from '../../context/CursusContext';
import { useLanguage } from '../../context/LanguageContext';
import AdminCourseCurriculumModal from './AdminCourseCurriculumModal';
import AdminCourseDocuments from './AdminCourseDocuments';
import Button from '../shared/Button';

const STATUS_CFG = {
  ingested:     { labelKey: 'admin.statusIngested',    cls: 'badge-gold',    spin: false },
  processing:   { labelKey: 'admin.statusProcessing',  cls: 'badge-success', spin: true  },
  not_ingested: { labelKey: 'admin.statusNotIngested', cls: 'badge-neutral', spin: false },
  failed:       { labelKey: 'admin.statusFailed',       cls: 'badge-danger',  spin: false },
  // mục 16 data contract: fabricated content (student_mock_data_service.
  // COURSE_DOCUMENTS) must never render like real ingested syllabus content
  // — deliberately NOT badge-gold/badge-success, so it can't be mistaken
  // for "ĐÃ NẠP" at a glance.
  mock_only:    { labelKey: 'admin.statusMockOnly',    cls: 'badge-warning', spin: false },
};

const CURRICULUM_PAGE_SIZE = 10;

function Spinner() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className="spin shrink-0">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/>
    </svg>
  );
}

function CourseMetric({ icon: Icon, label, value, note, tone = 'accent' }) {
  const toneClasses = {
    accent: 'bg-accent-soft text-accent-text-safe',
    success: 'bg-success-soft text-success-text-safe',
    warning: 'bg-warning-soft text-warning-text-safe',
    neutral: 'bg-surface-elevated text-fg-secondary',
  };

  return (
    <article className="admin-stat-card">
      <div className={`admin-stat-icon ${toneClasses[tone] ?? toneClasses.neutral}`}>
        <Icon size={16} aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-fg-muted">{label}</p>
        <p className="mono mt-1 text-2xl font-bold leading-none text-fg">{value}</p>
        <p className="mt-1 truncate text-[10px] text-fg-muted">{note}</p>
      </div>
    </article>
  );
}

export default function AdminCurriculum() {
  const { t, lang } = useLanguage();
  const { courses, addCourse, deleteCourse } = useCursus();
  const [showAdd, setShowAdd]   = useState(false);
  const [deleteTarget, setDel]  = useState(null);
  const [form, setForm] = useState({ subject_code:'', subject_name:'', semester: 'Fall 2026' });
  const [formError, setFormError] = useState(null);
  const [curriculumTarget, setCurriculumTarget] = useState(null); // { code, name } | null
  const [expandedCourse, setExpandedCourse] = useState(null); // subject_code | null
  const [courseQuery, setCourseQuery] = useState('');
  const [courseSemester, setCourseSemester] = useState('');
  const [courseStatus, setCourseStatus] = useState('');
  const [coursePage, setCoursePage] = useState(1);
  const [selectedCourseCode, setSelectedCourseCode] = useState(null);

  function handleAdd() {
    if (!form.subject_code.trim() || !form.subject_name.trim()) return;
    setFormError(null);
    addCourse(form.subject_code, form.subject_name, form.semester)
      .then(() => {
        setForm({ subject_code: '', subject_name: '', semester: 'Fall 2026' });
        setShowAdd(false);
      })
      .catch((err) => setFormError(err?.message || String(err)));
  }

  function handleDelete(code) {
    deleteCourse(code)
      .catch((err) => setFormError(err?.message || String(err)))
      .finally(() => setDel(null));
  }

  const ingested = courses.filter(c => c.ingest_status === 'ingested').length;
  const processing = courses.filter(c => c.ingest_status === 'processing').length;
  const waiting = courses.filter(c => ['not_ingested', 'failed', 'mock_only'].includes(c.ingest_status)).length;
  const totalChunks = courses.reduce((sum, course) => sum + Number(course.chunk_count || 0), 0);

  const semesterOptions = useMemo(
    () => [...new Set(courses.map((course) => String(course.semester ?? '')).filter(Boolean))]
      .sort((left, right) => left.localeCompare(right, lang === 'vi' ? 'vi' : 'en', { numeric: true })),
    [courses, lang],
  );

  const filteredCourses = useMemo(() => {
    const normalizedQuery = courseQuery.trim().toLocaleLowerCase(lang === 'vi' ? 'vi-VN' : 'en-US');
    return courses.filter((course) => {
      const matchesQuery = !normalizedQuery || `${course.subject_code} ${course.subject_name}`
        .toLocaleLowerCase(lang === 'vi' ? 'vi-VN' : 'en-US')
        .includes(normalizedQuery);
      const matchesSemester = !courseSemester || String(course.semester ?? '') === courseSemester;
      const matchesStatus = !courseStatus || course.ingest_status === courseStatus;
      return matchesQuery && matchesSemester && matchesStatus;
    });
  }, [courseQuery, courseSemester, courseStatus, courses, lang]);

  const coursePageCount = Math.max(1, Math.ceil(filteredCourses.length / CURRICULUM_PAGE_SIZE));
  const currentCoursePage = Math.min(coursePage, coursePageCount);
  const visibleCourses = filteredCourses.slice(
    (currentCoursePage - 1) * CURRICULUM_PAGE_SIZE,
    currentCoursePage * CURRICULUM_PAGE_SIZE,
  );
  const selectedCourse = courses.find((course) => course.subject_code === selectedCourseCode)
    || visibleCourses[0]
    || null;

  function selectCourseFromSurface(event, code) {
    if (event.target.closest('button, a, input, select, textarea')) return;
    setSelectedCourseCode(code);
  }

  function selectCourseFromKeyboard(event, code) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    setSelectedCourseCode(code);
  }

  function renderCourseStatus(course) {
    const cfg = STATUS_CFG[course.ingest_status] || STATUS_CFG.not_ingested;
    return (
      <span className={`badge ${cfg.cls} flex w-fit items-center gap-1.5 text-[9px] font-bold uppercase`}>
        {cfg.spin && <Spinner />}
        <span>{t(cfg.labelKey)}</span>
        {course.ingest_status === 'mock_only'
          ? course.mock_chunk_count > 0 && <span className="mono ml-1">· {course.mock_chunk_count}</span>
          : course.chunk_count > 0 && <span className="mono ml-1">· {course.chunk_count}</span>}
      </span>
    );
  }

  function renderCourseActions(course) {
    if (deleteTarget === course.subject_code) {
      return (
        <div className="flex flex-wrap justify-end gap-1.5">
          <Button
            variant="danger"
            size="sm"
            className="text-[10px] font-bold"
            onClick={() => handleDelete(course.subject_code)}
          >
            {t('admin.deleteBtn')}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-[10px] font-bold"
            onClick={() => setDel(null)}
          >
            {t('admin.cancelBtn')}
          </Button>
        </div>
      );
    }

    return (
      <div className="flex justify-end gap-1">
        <button
          type="button"
          className="btn-ghost min-h-10 min-w-10 rounded-md p-2.5 hover:text-accent cursor-pointer"
          onClick={() => setExpandedCourse(expandedCourse === course.subject_code ? null : course.subject_code)}
          title={t('admin.viewDocuments')}
          aria-label={`${t('admin.viewDocuments')}: ${course.subject_code}`}
          aria-expanded={expandedCourse === course.subject_code}
        >
          <FileText size={15} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="btn-ghost min-h-10 min-w-10 rounded-md p-2.5 hover:text-accent cursor-pointer"
          onClick={() => setCurriculumTarget({ code: course.subject_code, name: course.subject_name })}
          title={t('admin.viewCurriculumDetail')}
          aria-label={`${t('admin.viewCurriculumDetail')}: ${course.subject_code}`}
        >
          <BookOpen size={15} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="btn-ghost min-h-10 min-w-10 rounded-md p-2.5 hover:text-danger cursor-pointer"
          onClick={() => setDel(course.subject_code)}
          aria-label={t('admin.deleteCourseNamed', { code: course.subject_code })}
        >
          <Trash2 size={15} aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex justify-end">
        <Button id="add-course-btn" onClick={() => setShowAdd((visible) => !visible)}>
          <Plus size={14} aria-hidden="true" /> {t('admin.addCourseBtn')}
        </Button>
      </div>
      <section className="mb-5 grid grid-cols-2 gap-3 text-left lg:grid-cols-4" aria-label={t('admin.curriculumStatsLabel')}>
        <CourseMetric
          icon={CheckCircle2}
          label={t('admin.curriculumStatIngested')}
          value={`${ingested}/${courses.length}`}
          note={t('admin.curriculumStatIngestedNote')}
          tone="success"
        />
        <CourseMetric
          icon={Clock3}
          label={t('admin.curriculumStatProcessing')}
          value={processing}
          note={t('admin.curriculumStatProcessingNote')}
          tone="warning"
        />
        <CourseMetric
          icon={Database}
          label={t('admin.curriculumStatWaiting')}
          value={waiting}
          note={t('admin.curriculumStatWaitingNote')}
          tone="neutral"
        />
        <CourseMetric
          icon={FileText}
          label={t('admin.curriculumStatChunks')}
          value={totalChunks.toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}
          note={t('admin.curriculumStatChunksNote')}
          tone="accent"
        />
      </section>

      {formError && (
        <div className="flex items-start gap-2.5 p-3.5 rounded-[var(--radius-md)] bg-danger-soft border border-danger/20 text-left">
          <AlertCircle size={14} className="shrink-0 mt-0.5 text-danger" />
          <p className="text-xs text-danger leading-relaxed">{formError}</p>
        </div>
      )}

      {/* Add form (inline) */}
      {showAdd && (
        <div className="card p-5 animate-scale-in text-left" style={{ borderTop: '3px solid var(--accent)' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-sm font-bold text-fg">{t('admin.addNewCourseTitle')}</h3>
            <button
              type="button"
              className="btn-ghost min-h-10 min-w-10 p-2.5 rounded-md cursor-pointer"
              onClick={() => setShowAdd(false)}
              aria-label={t('admin.cancelBtn')}
            >
              <X size={15} aria-hidden="true" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{t('admin.courseCodeLabel')}</label>
              {/* bg-white dark:bg-slate-950 dropped — .input already sets a
                  theme-aware background (bg-card in light, translucent dark
                  glass override in dark), so the hardcoded pair was redundant. */}
              <input className="input mono text-xs" placeholder="MAE202"
                value={form.subject_code} onChange={e => setForm(p => ({ ...p, subject_code: e.target.value.toUpperCase() }))}/>
            </div>
            <div>
              <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{t('admin.semesterLabel')}</label>
              <input className="input text-xs" value={form.semester}
                onChange={e => setForm(p => ({ ...p, semester: e.target.value }))}/>
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-xs font-semibold text-fg-secondary mb-1.5">{t('admin.courseNameLabel')}</label>
            <input className="input text-xs" placeholder="Mathematics A2"
              value={form.subject_name} onChange={e => setForm(p => ({ ...p, subject_name: e.target.value }))}/>
          </div>
          <div className="flex gap-2 justify-end">
            {/* bg-white dark:bg-transparent dropped — .btn-outline already sets
                bg-card / hover:bg-elevated via tokens. */}
            <Button variant="outline" onClick={() => setShowAdd(false)}>{t('admin.cancelBtn')}</Button>
            <Button disabled={!form.subject_code.trim() || !form.subject_name.trim()} onClick={handleAdd}>
              <CheckCircle2 size={13}/> {t('admin.saveCourseBtn')}
            </Button>
          </div>
        </div>
      )}

      {/* Curriculum table */}
      <div className="text-left">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 select-none">
          <div className="flex items-center gap-2">
            <Database size={15} className="text-fg-muted" aria-hidden="true" />
            <h2 className="text-sm font-bold text-fg">{t('admin.curriculumListTitle')}</h2>
          </div>
          <span className="mono text-xs text-fg-muted">{ingested}/{courses.length} {t('admin.coursesIngestedCount')}</span>
        </div>

        <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <label className="text-xs font-semibold text-fg-secondary">
            {t('admin.curriculumSearchLabel')}
            <span className="relative mt-1 block">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" aria-hidden="true" />
              <input
                type="search"
                className="input min-h-11 w-full text-xs"
                style={{ paddingLeft: '2.25rem' }}
                value={courseQuery}
                placeholder={t('admin.curriculumSearchPlaceholder')}
                onChange={(event) => {
                  setCourseQuery(event.target.value);
                  setCoursePage(1);
                }}
              />
            </span>
          </label>
          <label className="text-xs font-semibold text-fg-secondary">
            {t('admin.curriculumSemesterFilter')}
            <select
              className="input mt-1 min-h-11 w-full text-xs"
              value={courseSemester}
              onChange={(event) => {
                setCourseSemester(event.target.value);
                setCoursePage(1);
              }}
            >
              <option value="">{t('admin.curriculumAllSemesters')}</option>
              {semesterOptions.map((semester) => <option key={semester} value={semester}>{semester}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-fg-secondary">
            {t('admin.curriculumStatusFilter')}
            <select
              className="input mt-1 min-h-11 w-full text-xs"
              value={courseStatus}
              onChange={(event) => {
                setCourseStatus(event.target.value);
                setCoursePage(1);
              }}
            >
              <option value="">{t('admin.curriculumAllStatuses')}</option>
              {Object.entries(STATUS_CFG).map(([value, cfg]) => (
                <option key={value} value={value}>{t(cfg.labelKey)}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-fg-muted" aria-live="polite">
            {t('admin.curriculumResults', { shown: filteredCourses.length, total: courses.length })}
          </p>
          {courses.some((course) => course.ingest_status === 'mock_only') && (
            <p className="max-w-2xl text-[10px] leading-relaxed text-fg-muted">
              {t('admin.curriculumMockLegend')}
            </p>
          )}
        </div>

        <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0">
        <div className="card hidden overflow-hidden md:block">
          <div className="overflow-x-auto admin-scroll-x">
            <table className="data-table">
              <caption className="sr-only">{t('admin.curriculumListTitle')}</caption>
              <thead>
                <tr>
                  {[t('admin.colCode'), t('admin.colName'), t('admin.colSemester'), t('admin.colChunk'), t('admin.colStatus'), ''].map((h, i) => (
                    <th key={i} scope="col">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleCourses.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-xs text-fg-muted">
                      {t('admin.curriculumNoResults')}
                    </td>
                  </tr>
                ) : visibleCourses.map((c) => (
                    <React.Fragment key={c.subject_code}>
                    <tr
                      className={`${selectedCourse?.subject_code === c.subject_code ? 'admin-selected-row' : 'hover:bg-accent-soft/50'} cursor-pointer transition-colors`}
                      onClick={(event) => selectCourseFromSurface(event, c.subject_code)}
                      onKeyDown={(event) => selectCourseFromKeyboard(event, c.subject_code)}
                      tabIndex={0}
                      aria-label={`${c.subject_code} — ${c.subject_name}`}
                    >
                      <td>
                        <button
                          type="button"
                          className="mono text-xs font-bold text-accent-text-safe hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                          onClick={() => setSelectedCourseCode(c.subject_code)}
                        >
                          {c.subject_code}
                        </button>
                      </td>
                      <td className="font-semibold text-fg">{c.subject_name}</td>
                      <td>
                        <span className="mono text-xs text-fg-muted">{c.semester}</span>
                      </td>
                      <td>
                        <span className="mono text-xs font-bold text-fg">
                          {c.chunk_count > 0 ? c.chunk_count : '—'}
                        </span>
                      </td>
                      <td>
                        {renderCourseStatus(c)}
                      </td>
                      <td className="text-right">
                        {renderCourseActions(c)}
                      </td>
                    </tr>
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card divide-y divide-line overflow-hidden md:hidden">
          {visibleCourses.length === 0 ? (
            <p className="px-4 py-8 text-center text-xs text-fg-muted">{t('admin.curriculumNoResults')}</p>
          ) : visibleCourses.map((course) => (
            <article
              key={course.subject_code}
              className={`${selectedCourse?.subject_code === course.subject_code ? 'bg-accent-soft' : 'hover:bg-accent-soft/50'} cursor-pointer transition-colors`}
              onClick={(event) => selectCourseFromSurface(event, course.subject_code)}
              onKeyDown={(event) => selectCourseFromKeyboard(event, course.subject_code)}
              role="button"
              tabIndex={0}
              aria-label={`${course.subject_code} — ${course.subject_name}`}
            >
              <div className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <button type="button" className="mono text-xs font-bold text-accent-text-safe" onClick={() => setSelectedCourseCode(course.subject_code)}>{course.subject_code}</button>
                    <h3 className="mt-1 text-sm font-semibold leading-snug text-fg">{course.subject_name}</h3>
                  </div>
                  <div className="shrink-0">{renderCourseStatus(course)}</div>
                </div>
                <dl className="flex flex-wrap gap-x-5 gap-y-2 text-xs">
                  <div>
                    <dt className="text-[10px] uppercase tracking-wide text-fg-muted">{t('admin.colSemester')}</dt>
                    <dd className="mono mt-0.5 font-semibold text-fg-secondary">{course.semester}</dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase tracking-wide text-fg-muted">{t('admin.colChunk')}</dt>
                    <dd className="mono mt-0.5 font-semibold text-fg-secondary">{course.chunk_count > 0 ? course.chunk_count : '—'}</dd>
                  </div>
                </dl>
                {renderCourseActions(course)}
              </div>
            </article>
          ))}
        </div>

        {filteredCourses.length > 0 && (
          <div className="mt-3 flex items-center justify-between gap-3 text-xs">
            <Button
              variant="outline"
              size="sm"
              disabled={currentCoursePage <= 1}
              onClick={() => setCoursePage((page) => Math.max(1, page - 1))}
            >
              {t('admin.prevPage')}
            </Button>
            <span className="mono text-fg-muted">
              {t('admin.curriculumPageSummary', { page: currentCoursePage, pages: coursePageCount })}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentCoursePage >= coursePageCount}
              onClick={() => setCoursePage((page) => Math.min(coursePageCount, page + 1))}
            >
              {t('admin.nextPage')}
            </Button>
          </div>
        )}
        </div>

        <aside className="admin-detail-panel" aria-label={lang === 'vi' ? 'Chi tiết môn học' : 'Course details'}>
          {selectedCourse ? (
            <>
              <div className="flex items-start justify-between gap-3 border-b border-line pb-4">
                <div className="min-w-0">
                  <p className="mono text-sm font-bold text-accent">{selectedCourse.subject_code}</p>
                  <h3 className="mt-1 font-display text-base font-bold leading-snug text-fg">{selectedCourse.subject_name}</h3>
                </div>
                <div className="shrink-0">{renderCourseStatus(selectedCourse)}</div>
              </div>

              <dl className="grid grid-cols-2 gap-2 py-4 text-xs">
                <div className="rounded-md border border-line bg-surface-elevated p-3">
                  <dt className="text-[9px] font-bold uppercase tracking-wide text-fg-muted">{t('admin.colSemester')}</dt>
                  <dd className="mono mt-1 font-bold text-fg">{selectedCourse.semester}</dd>
                </div>
                <div className="rounded-md border border-line bg-surface-elevated p-3">
                  <dt className="text-[9px] font-bold uppercase tracking-wide text-fg-muted">{t('admin.colChunk')}</dt>
                  <dd className="mono mt-1 font-bold text-fg">{selectedCourse.chunk_count || selectedCourse.mock_chunk_count || 0}</dd>
                </div>
              </dl>

              <div className="border-t border-line pt-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-fg-muted">{lang === 'vi' ? 'Nguồn học liệu' : 'Learning sources'}</p>
                <div className="mt-3 space-y-2">
                  <div className="flex items-center justify-between rounded-md border border-line p-3 text-xs">
                    <span className="flex items-center gap-2 text-fg-secondary"><FileText size={14} className="text-accent" />{lang === 'vi' ? 'Tài liệu môn học' : 'Course documents'}</span>
                    <strong className="mono text-fg">{selectedCourse.document_count ?? (selectedCourse.chunk_count > 0 ? 1 : 0)}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-md border border-line p-3 text-xs">
                    <span className="flex items-center gap-2 text-fg-secondary"><Database size={14} className="text-accent" />Chunks</span>
                    <strong className="mono text-fg">{selectedCourse.chunk_count || selectedCourse.mock_chunk_count || 0}</strong>
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-2 border-t border-line pt-4">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => setExpandedCourse(expandedCourse === selectedCourse.subject_code ? null : selectedCourse.subject_code)}
                >
                  <FileText size={14} /> {t('admin.viewDocuments')}
                </Button>
                <Button
                  className="w-full"
                  onClick={() => setCurriculumTarget({ code: selectedCourse.subject_code, name: selectedCourse.subject_name })}
                >
                  <BookOpen size={14} /> {t('admin.viewCurriculumDetail')}
                </Button>
              </div>

              {expandedCourse === selectedCourse.subject_code && (
                <div className="mt-4 overflow-hidden rounded-md border border-line">
                  <AdminCourseDocuments courseCode={selectedCourse.subject_code} />
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-fg-muted">{t('admin.curriculumNoResults')}</p>
          )}
        </aside>
        </div>
      </div>

      {curriculumTarget && (
        <AdminCourseCurriculumModal
          code={curriculumTarget.code}
          courseName={curriculumTarget.name}
          onClose={() => setCurriculumTarget(null)}
        />
      )}
    </div>
  );
}
