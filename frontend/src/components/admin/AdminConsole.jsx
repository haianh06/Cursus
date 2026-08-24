import React, { useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Database, Plus, Trash2, TrendingUp, AlertCircle, CheckCircle2, X, BookOpen, FileText } from 'lucide-react';
import { useCursus } from '../../context/CursusContext';
import { useLanguage } from '../../context/LanguageContext';
import AdminAcademicPanel from './AdminAcademicPanel';
import AdminAiPolicy from './AdminAiPolicy';
import AdminAnalytics from './AdminAnalytics';
import AdminAudit from './AdminAudit';
import AdminCourseCurriculumModal from './AdminCourseCurriculumModal';
import AdminCourseDocuments from './AdminCourseDocuments';
import AdminDataRequests from './AdminDataRequests';
import AdminMockLms from './AdminMockLms';
import AdminOverview from './AdminOverview';
import AdminPeopleExplorer from './AdminPeopleExplorer';
import AdminSettingsPanel from './AdminSettingsPanel';
import AdminUsers from './AdminUsers';

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

function Spinner() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className="spin shrink-0">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/>
    </svg>
  );
}

export default function AdminConsole({ user }) {
  const location = useLocation();
  const pathParts = location.pathname.split('/').filter(Boolean);
  const tab = pathParts[1] || 'courses';

  const { t, lang } = useLanguage();
  const { courses, addCourse, deleteCourse, kpi } = useCursus();
  const [showAdd, setShowAdd]   = useState(false);
  const [deleteTarget, setDel]  = useState(null);
  const [form, setForm] = useState({ subject_code:'', subject_name:'', semester: 'Fall 2026' });
  const [formError, setFormError] = useState(null);
  const [curriculumTarget, setCurriculumTarget] = useState(null); // { code, name } | null
  const [expandedCourse, setExpandedCourse] = useState(null); // subject_code | null

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

  // Same label strings the tab buttons already render — reused as the dynamic
  // <h1> so screen-reader/SEO heading matches the visually active section
  // instead of a single static title regardless of which tab is open.
  const TAB_HEADINGS = {
    overview: lang === 'vi' ? 'Tổng quan' : 'Overview',
    people: t('admin.navPeople'),
    courses: lang === 'vi' ? 'Chương trình học' : 'Curriculum',
    academic: lang === 'vi' ? 'Học kỳ & lịch thi' : 'Term & exams',
    policy: lang === 'vi' ? 'Chính sách AI' : 'AI Policy',
    mocklms: 'EduSync',
    users: t('admin.usersTabLabel'),
    datarequests: lang === 'vi' ? 'Yêu cầu dữ liệu' : 'Data Requests',
    audit: t('admin.auditTitle'),
    analytics: t('admin.analyticsTabLabel'),
    'org-settings': t('admin.settingsTitle'),
  };

  return (
    <div className="flex flex-col gap-6 p-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-4" style={{ borderColor: 'var(--border-ui)' }}>
        <div className="text-left">
          <h1 className="font-display text-xl font-bold text-fg">{TAB_HEADINGS[tab] ?? t('admin.pageTitle')}</h1>
          <p className="text-xs text-fg-muted mt-1 flex items-center gap-1">
            <Database size={11} className="text-accent"/>
            Academic Affairs • Vector Store Database
          </p>
        </div>
        {tab === 'courses' && (
          <button id="add-course-btn" className="btn btn-accent text-xs px-4 py-2 cursor-pointer" onClick={() => setShowAdd(v => !v)}>
            <Plus size={14}/> {t('admin.addCourseBtn')}
          </button>
        )}
      </div>

      <Routes>
        <Route path="overview" element={
          <div role="tabpanel" id="admin-panel-overview" aria-labelledby="admin-tab-overview">
            <AdminOverview />
          </div>
        } />
        <Route path="people" element={
          <div role="tabpanel" id="admin-panel-people" aria-labelledby="admin-tab-people">
            <AdminPeopleExplorer />
          </div>
        } />
        <Route path="academic" element={
          <div role="tabpanel" id="admin-panel-academic" aria-labelledby="admin-tab-academic">
            <AdminAcademicPanel />
          </div>
        } />
        <Route path="org-settings" element={
          <div role="tabpanel" id="admin-panel-org-settings" aria-labelledby="admin-tab-org-settings">
            <AdminSettingsPanel />
          </div>
        } />
        <Route path="policy" element={
          <div role="tabpanel" id="admin-panel-policy" aria-labelledby="admin-tab-policy">
            <AdminAiPolicy />
          </div>
        } />
        <Route path="mocklms" element={
          <div role="tabpanel" id="admin-panel-mocklms" aria-labelledby="admin-tab-mocklms">
            <AdminMockLms />
          </div>
        } />
        <Route path="users" element={
          <div role="tabpanel" id="admin-panel-users" aria-labelledby="admin-tab-users">
            <AdminUsers />
          </div>
        } />
        <Route path="datarequests" element={
          <div role="tabpanel" id="admin-panel-datarequests" aria-labelledby="admin-tab-datarequests">
            <AdminDataRequests />
          </div>
        } />
        <Route path="audit" element={
          <div role="tabpanel" id="admin-panel-audit" aria-labelledby="admin-tab-audit">
            <AdminAudit />
          </div>
        } />
        <Route path="analytics" element={
          <div role="tabpanel" id="admin-panel-analytics" aria-labelledby="admin-tab-analytics">
            <AdminAnalytics />
          </div>
        } />
        <Route path="courses" element={
          <div role="tabpanel" id="admin-panel-courses" aria-labelledby="admin-tab-courses">
      {/* KPI Section */}
      <div className="text-left">
        <div className="flex items-center gap-2 mb-3">
          {/* amber-500 ≈ the app's --gold token (#f59e0b in dark), and "gold" is
              already used for the brand's secondary/premium accent elsewhere
              in this file (badge-gold) — reused here for the KPI section icon. */}
          <TrendingUp size={15} className="text-gold" />
          <h2 className="text-sm font-bold text-fg">{t('admin.kpiTotalTitle')}</h2>
        </div>

        {kpi ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
              <div className="card p-5" style={{ borderTop: '3px solid var(--accent)' }}>
                <p className="mono text-[9px] font-bold uppercase tracking-widest text-fg-muted mb-2">
                  {t('admin.withCursus')}
                </p>
                <span className="mono text-4xl font-bold text-accent-text-safe">
                  {Math.round(kpi.with_cursus_overall * 100)}%
                </span>
                <p className="text-xs mt-1 text-success font-semibold">
                  ↑ +{Math.round((kpi.with_cursus_overall - kpi.baseline_overall) * 100)}pp {lang === 'vi' ? 'so với baseline' : 'vs baseline'}
                </p>
              </div>
              <div className="card p-5 opacity-75">
                <p className="mono text-[9px] font-bold uppercase tracking-widest text-fg-muted mb-2">
                  {t('admin.baseline')}
                </p>
                {/* slate-500 baseline number is de-emphasized relative to the accent
                    KPI number above, but still a headline figure — fg-secondary
                    (not fg-muted) matches that weight. */}
                <span className="mono text-4xl font-bold text-fg-secondary">
                  {Math.round(kpi.baseline_overall * 100)}%
                </span>
                <p className="text-xs mt-1 text-fg-muted font-semibold">{t('admin.noCursus')}</p>
              </div>
            </div>

            {/* METHOD NOTE — bắt buộc luôn hiện */}
            <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-accent-soft border border-accent/20">
              <AlertCircle size={14} className="shrink-0 mt-0.5 text-accent" />
              <p className="text-xs text-fg-secondary leading-relaxed">
                <strong className="text-accent-text-safe">{t('admin.methodNoteLabel')}: </strong>
                {kpi.method_note}
              </p>
            </div>
          </>
        ) : (
          <div className="card p-5 text-xs text-fg-muted">{lang === 'vi' ? 'Đang tải KPI…' : 'Loading KPI…'}</div>
        )}
      </div>

      {formError && (
        <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-danger-soft border border-danger/20 text-left">
          <AlertCircle size={14} className="shrink-0 mt-0.5 text-danger" />
          <p className="text-xs text-danger leading-relaxed">{formError}</p>
        </div>
      )}

      {/* Add form (inline) */}
      {showAdd && (
        <div className="card p-5 animate-scale-in text-left" style={{ borderTop: '3px solid var(--accent)' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-sm font-bold text-fg">{t('admin.addNewCourseTitle')}</h3>
            <button className="btn-ghost p-1 rounded-md cursor-pointer" onClick={() => setShowAdd(false)}><X size={15}/></button>
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
            <button className="btn btn-outline text-xs px-3.5 py-1.5 rounded-lg cursor-pointer" onClick={() => setShowAdd(false)}>{t('admin.cancelBtn')}</button>
            <button className="btn btn-accent text-xs px-4 py-2 rounded-lg cursor-pointer" disabled={!form.subject_code.trim() || !form.subject_name.trim()} onClick={handleAdd}>
              <CheckCircle2 size={13}/> {t('admin.saveCourseBtn')}
            </button>
          </div>
        </div>
      )}

      {/* Curriculum table */}
      <div className="text-left">
        <div className="flex items-center justify-between mb-3 select-none">
          <div className="flex items-center gap-2">
            <Database size={15} className="text-fg-muted" />
            <h2 className="text-sm font-bold text-fg">{t('admin.curriculumListTitle')}</h2>
          </div>
          <span className="mono text-xs text-fg-muted">{ingested}/{courses.length} {t('admin.coursesIngestedCount')}</span>
        </div>

        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  {[t('admin.colCode'), t('admin.colName'), t('admin.colSemester'), t('admin.colChunk'), t('admin.colStatus'), ''].map((h, i) => (
                    <th key={i} scope="col">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {courses.map((c) => {
                  const cfg = STATUS_CFG[c.ingest_status] || STATUS_CFG.not_ingested;
                  return (
                    <React.Fragment key={c.subject_code}>
                    <tr>
                      <td>
                        <span className="mono text-xs font-bold text-accent-text-safe">{c.subject_code}</span>
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
                        <span className={`badge ${cfg.cls} flex items-center gap-1.5 w-fit text-[9px] font-bold uppercase`}>
                          {cfg.spin && <Spinner/>}
                          <span>{t(cfg.labelKey)}</span>
                          {c.ingest_status === 'mock_only'
                            ? c.mock_chunk_count > 0 && <span className="mono ml-1">· {c.mock_chunk_count}</span>
                            : c.chunk_count > 0 && <span className="mono ml-1">· {c.chunk_count}</span>}
                        </span>
                        {c.ingest_status === 'mock_only' && (
                          <p className="mt-1 text-[10px] text-fg-muted max-w-[220px]">{t('admin.statusMockOnlyNote')}</p>
                        )}
                      </td>
                      <td className="text-right">
                        {deleteTarget === c.subject_code ? (
                          <div className="flex gap-1.5 justify-end">
                            <button className="btn-danger-outline py-1 px-2.5 rounded-lg text-[10px] font-bold cursor-pointer" onClick={() => handleDelete(c.subject_code)}>{t('admin.deleteBtn')}</button>
                            <button className="btn-ghost text-[10px] py-1 px-2.5 rounded-lg cursor-pointer font-bold" onClick={() => setDel(null)}>{t('admin.cancelBtn')}</button>
                          </div>
                        ) : (
                          <div className="flex gap-1 justify-end">
                            <button
                              className="btn-ghost p-1.5 rounded-md hover:text-accent cursor-pointer"
                              onClick={() => setExpandedCourse(expandedCourse === c.subject_code ? null : c.subject_code)}
                              title={lang === 'vi' ? 'Xem tài liệu' : 'View documents'}
                              aria-label={lang === 'vi' ? 'Xem tài liệu' : 'View documents'}
                            >
                              <FileText size={13} />
                            </button>
                            <button
                              className="btn-ghost p-1.5 rounded-md hover:text-accent cursor-pointer"
                              onClick={() => setCurriculumTarget({ code: c.subject_code, name: c.subject_name })}
                              title={lang === 'vi' ? 'Xem chi tiết chương trình (CLO/Session)' : 'View curriculum detail (CLO/Session)'}
                              aria-label={lang === 'vi' ? 'Xem chi tiết chương trình' : 'View curriculum detail'}
                            >
                              <BookOpen size={13}/>
                            </button>
                            <button className="btn-ghost p-1.5 rounded-md hover:text-danger cursor-pointer"
                              onClick={() => setDel(c.subject_code)}>
                              <Trash2 size={13}/>
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                    {expandedCourse === c.subject_code && (
                      <tr>
                        <td colSpan={6} className="p-0 border-b border-line">
                          <AdminCourseDocuments courseCode={c.subject_code} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      </div>
    } />
    <Route path="*" element={<Navigate to="/admin/courses" replace />} />
      </Routes>

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
