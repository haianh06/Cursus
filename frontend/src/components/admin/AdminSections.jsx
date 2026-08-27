import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Plus, Trash2, Users, X } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import ConfirmDialog from '../shared/ConfirmDialog';
import AdminAsyncRegion from './AdminAsyncRegion';
import { focusFirstInDialog, trapModalFocus } from './modalFocus';
import {
  addAdminSectionStudent,
  createAdminSection,
  deleteAdminSection,
  getAdminSectionCourses,
  getAdminSectionRoster,
  getAdminSections,
  listAdminPeople,
  removeAdminSectionStudent,
  updateAdminSection,
  userFacingApiError,
} from '../../lib/api';

/** Task 9 -- Admin's "Lớp học" screen. Closes the loop opened by the Work
 * Queue's UNASSIGNED_SECTION item (adminWorkQueueLinks.js): sections the
 * student semester wizard creates with no instructor land here so an admin
 * can assign one, and this is also where an admin manages any section's
 * roster and deletes empty sections.
 *
 * Backend: src/api/admin_sections.py (Tasks 6/7) + GET .../sections/courses
 * (added alongside this component -- see AdminSections' task report for why
 * GET /admin/courses, the only course list that already existed, couldn't
 * supply the real Course.id `POST /admin/sections` needs). */
export default function AdminSections() {
  const { t, lang } = useLanguage();
  const [sections, setSections] = useState(null);
  const [courses, setCourses] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [rosterSection, setRosterSection] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null); // { target: section }
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [confirmError, setConfirmError] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([
      getAdminSectionCourses(),
      getAdminSections(),
      listAdminPeople({ role: 'INSTRUCTOR' }),
    ])
      .then(([coursesRes, sectionsRes, instructorsRes]) => {
        setCourses(coursesRes.items || []);
        setSections(sectionsRes.items || []);
        setInstructors(instructorsRes.items || []);
      })
      .catch((err) => {
        setError({ ...userFacingApiError(err, lang), status: err?.status, code: err?.code });
      })
      .finally(() => setLoading(false));
  }, [lang]);

  useEffect(() => {
    load();
  }, [load]);

  function handleAssign(section, instructorId) {
    setBusyId(section.id);
    updateAdminSection(section.id, { instructorId: instructorId || null })
      .then((updated) => {
        setSections((rows) => rows.map((row) => (row.id === section.id ? updated : row)));
      })
      .catch((err) => setError({ ...userFacingApiError(err, lang), status: err?.status, code: err?.code }))
      .finally(() => setBusyId(''));
  }

  function requestDelete(section) {
    setConfirmError('');
    setConfirmAction({ target: section });
  }

  function executeDelete() {
    if (!confirmAction) return;
    setConfirmBusy(true);
    setConfirmError('');
    deleteAdminSection(confirmAction.target.id)
      .then(() => {
        setSections((rows) => rows.filter((row) => row.id !== confirmAction.target.id));
        setConfirmAction(null);
      })
      .catch((err) => {
        setConfirmError(
          err?.status === 409 ? t('admin.sectionsDeleteInUse') : userFacingApiError(err, lang).message,
        );
      })
      .finally(() => setConfirmBusy(false));
  }

  return (
    <div className="flex flex-col gap-6 text-left">
      <h2 className="sr-only">{t('admin.sectionsTitle')}</h2>

      <div className="flex flex-wrap items-center justify-end gap-3">
        <button
          type="button"
          className="btn btn-accent text-xs px-4 py-2 cursor-pointer"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus size={14} /> {t('admin.sectionsCreate')}
        </button>
      </div>

      <AdminAsyncRegion
        loading={loading}
        error={error}
        empty={!loading && !error && (sections || []).length === 0}
        emptyMessage={t('admin.sectionsEmpty')}
        onRetry={load}
      >
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">{t('admin.sectionsColCourse')}</th>
                <th scope="col">{t('admin.sectionsColSection')}</th>
                <th scope="col">{t('admin.sectionsColTerm')}</th>
                <th scope="col">{t('admin.sectionsColInstructor')}</th>
                <th scope="col">{t('admin.sectionsColEnrolled')}</th>
                <th scope="col">{t('admin.sectionsColActions')}</th>
              </tr>
            </thead>
            <tbody>
              {(sections || []).map((section) => (
                <tr key={section.id}>
                  <td className="text-fg">
                    {section.courseCode}
                    <p className="text-[10px] text-fg-muted">{section.courseName}</p>
                  </td>
                  <td className="text-fg-secondary">{section.sectionCode}</td>
                  <td className="text-fg-secondary">{section.term}</td>
                  <td>
                    <div className="flex flex-col gap-1.5">
                      {section.instructorId ? (
                        <span className="text-fg-secondary">{section.instructorName}</span>
                      ) : (
                        <span className="badge badge-warning text-[9px] font-bold w-fit">
                          {t('admin.sectionsUnassigned')}
                        </span>
                      )}
                      <label className="sr-only" htmlFor={`assign-${section.id}`}>
                        {t('admin.sectionsAssign')}
                      </label>
                      <select
                        id={`assign-${section.id}`}
                        className="input text-[11px] py-1 min-h-8"
                        value={section.instructorId || ''}
                        disabled={busyId === section.id}
                        onChange={(event) => handleAssign(section, event.target.value)}
                      >
                        <option value="">{t('admin.sectionsAssignPlaceholder')}</option>
                        {instructors.map((instructor) => (
                          <option key={instructor.id} value={instructor.id}>
                            {instructor.full_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </td>
                  <td className="mono text-fg">{section.enrolledCount}</td>
                  <td>
                    <div className="flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 min-h-[28px] font-bold text-accent-text-safe cursor-pointer hover:underline outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                        onClick={() => setRosterSection(section)}
                      >
                        <Users size={12} /> {t('admin.sectionsRoster')}
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 min-h-[28px] font-bold text-danger cursor-pointer hover:underline disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                        disabled={busyId === section.id}
                        onClick={() => requestDelete(section)}
                      >
                        <Trash2 size={12} /> {t('admin.sectionsDeleteBtn')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AdminAsyncRegion>

      {showCreateModal && (
        <CreateSectionModal
          courses={courses}
          instructors={instructors}
          onClose={() => setShowCreateModal(false)}
          onCreated={(created) => {
            setSections((rows) => [...(rows || []), created]);
            setShowCreateModal(false);
          }}
        />
      )}

      {rosterSection && (
        <SectionRosterModal
          section={rosterSection}
          onClose={(changed) => {
            setRosterSection(null);
            if (changed) load();
          }}
        />
      )}

      <ConfirmDialog
        open={!!confirmAction}
        title={t('admin.sectionsDeleteTitle')}
        message={t('admin.sectionsDeleteConfirm')}
        confirmLabel={t('admin.sectionsDeleteBtn')}
        cancelLabel={t('admin.cancelBtn')}
        danger
        busy={confirmBusy}
        lang={lang}
        onConfirm={executeDelete}
        onCancel={() => {
          setConfirmAction(null);
          setConfirmError('');
        }}
      >
        {confirmError && (
          <p className="flex items-center gap-2 text-xs text-danger" role="alert">
            <AlertCircle size={14} className="shrink-0" />
            {confirmError}
          </p>
        )}
      </ConfirmDialog>
    </div>
  );
}

function useModalFocusTrap(onClose) {
  const panelRef = useRef(null);
  const restoreRef = useRef(null);

  useEffect(() => {
    restoreRef.current = document.activeElement;
    focusFirstInDialog(panelRef.current);
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      trapModalFocus(event, panelRef.current);
    }
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      if (restoreRef.current instanceof HTMLElement) restoreRef.current.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return panelRef;
}

function CreateSectionModal({ courses, instructors, onClose, onCreated }) {
  const { t, lang } = useLanguage();
  const [courseId, setCourseId] = useState('');
  const [sectionCode, setSectionCode] = useState('');
  const [term, setTerm] = useState('');
  const [instructorId, setInstructorId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const panelRef = useModalFocusTrap(onClose);

  function submit(event) {
    event.preventDefault();
    if (!courseId || !sectionCode.trim() || !term.trim()) return;
    setBusy(true);
    setError('');
    createAdminSection({
      courseId,
      sectionCode: sectionCode.trim(),
      term: term.trim(),
      instructorId: instructorId || null,
    })
      .then((created) => onCreated(created))
      .catch((err) => setError(userFacingApiError(err, lang).message))
      .finally(() => setBusy(false));
  }

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-section-modal-title"
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-md rounded-2xl border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-line">
          <h2 id="create-section-modal-title" className="font-display text-sm font-bold text-fg">
            {t('admin.sectionsModalTitle')}
          </h2>
          <button
            type="button"
            className="btn-ghost w-10 h-10 inline-flex items-center justify-center rounded-lg cursor-pointer text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={onClose}
            aria-label={t('admin.cancelBtn')}
          >
            <X size={15} />
          </button>
        </div>

        <form onSubmit={submit} className="p-5 space-y-4 text-left">
          {error && (
            <p className="flex items-center gap-2 text-xs text-danger" role="alert">
              <AlertCircle size={14} className="shrink-0" />
              {error}
            </p>
          )}
          <div>
            <label htmlFor="section-course" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {t('admin.sectionsModalCourseLabel')}
            </label>
            <select
              id="section-course"
              required
              className="input text-[13px] w-full"
              value={courseId}
              onChange={(event) => setCourseId(event.target.value)}
            >
              <option value="">{t('admin.sectionsModalCourseSelect')}</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.code} — {course.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="section-code" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {t('admin.sectionsModalSectionCodeLabel')}
            </label>
            <input
              id="section-code"
              type="text"
              required
              maxLength={32}
              className="input text-[13px] w-full"
              value={sectionCode}
              onChange={(event) => setSectionCode(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="section-term" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {t('admin.sectionsModalTermLabel')}
            </label>
            <input
              id="section-term"
              type="text"
              required
              maxLength={32}
              className="input text-[13px] w-full"
              value={term}
              onChange={(event) => setTerm(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="section-instructor" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {t('admin.sectionsModalInstructorLabel')}
            </label>
            <select
              id="section-instructor"
              className="input text-[13px] w-full"
              value={instructorId}
              onChange={(event) => setInstructorId(event.target.value)}
            >
              <option value="">{t('admin.sectionsAssignPlaceholder')}</option>
              {instructors.map((instructor) => (
                <option key={instructor.id} value={instructor.id}>
                  {instructor.full_name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              className="btn btn-outline text-[13px] px-4 min-h-10 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
              onClick={onClose}
            >
              {t('admin.cancelBtn')}
            </button>
            <button
              type="submit"
              className="btn btn-accent text-[13px] px-4 min-h-10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent"
              disabled={busy || !courseId || !sectionCode.trim() || !term.trim()}
            >
              {busy ? t('admin.sectionsModalSubmittingBtn') : t('admin.sectionsModalSubmitBtn')}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

function SectionRosterModal({ section, onClose }) {
  const { t, lang } = useLanguage();
  const [roster, setRoster] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [candidates, setCandidates] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');
  const [removeTarget, setRemoveTarget] = useState(null);
  const [removeBusy, setRemoveBusy] = useState(false);
  const [removeError, setRemoveError] = useState('');
  const [changed, setChanged] = useState(false);
  const panelRef = useModalFocusTrap(() => onClose(changed));

  const loadRoster = useCallback(() => {
    setLoading(true);
    setError(null);
    return getAdminSectionRoster(section.id)
      .then((res) => setRoster(res.items || []))
      .catch((err) => setError({ ...userFacingApiError(err, lang), status: err?.status, code: err?.code }))
      .finally(() => setLoading(false));
  }, [section.id, lang]);

  useEffect(() => {
    loadRoster();
  }, [loadRoster]);

  const searchStudents = useCallback(() => {
    listAdminPeople({ role: 'STUDENT', search })
      .then((res) => setCandidates(res.items || []))
      .catch(() => setCandidates([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  useEffect(() => {
    searchStudents();
    // Only on mount -- further searches are explicit (button/Enter), not on
    // every keystroke, so this intentionally doesn't depend on `search`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const enrolledIds = new Set((roster || []).map((row) => row.studentId));
  const availableCandidates = candidates.filter((candidate) => !enrolledIds.has(candidate.id));

  function handleAdd(event) {
    event.preventDefault();
    if (!selectedStudentId) return;
    setAdding(true);
    setAddError('');
    addAdminSectionStudent(section.id, selectedStudentId)
      .then(() => {
        setSelectedStudentId('');
        setChanged(true);
        return loadRoster();
      })
      .catch((err) => setAddError(userFacingApiError(err, lang).message))
      .finally(() => setAdding(false));
  }

  function confirmRemove() {
    if (!removeTarget) return;
    setRemoveBusy(true);
    setRemoveError('');
    removeAdminSectionStudent(section.id, removeTarget.studentId)
      .then(() => {
        setRemoveTarget(null);
        setChanged(true);
        return loadRoster();
      })
      .catch((err) => setRemoveError(userFacingApiError(err, lang).message))
      .finally(() => setRemoveBusy(false));
  }

  return (
    <>
      <div
        className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm"
        onClick={() => onClose(changed)}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="roster-modal-title"
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-line">
          <h2 id="roster-modal-title" className="font-display text-sm font-bold text-fg">
            {t('admin.sectionsRosterTitle')} — {section.courseCode} {section.sectionCode}
          </h2>
          <button
            type="button"
            className="btn-ghost w-10 h-10 inline-flex items-center justify-center rounded-lg cursor-pointer text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={() => onClose(changed)}
            aria-label={t('admin.sectionsCloseBtn')}
          >
            <X size={15} />
          </button>
        </div>

        <div className="p-5 space-y-4 text-left">
          <form onSubmit={handleAdd} className="space-y-2">
            <label htmlFor="roster-search" className="text-[11px] font-bold uppercase tracking-widest block text-fg-muted">
              {t('admin.sectionsRosterAddLabel')}
            </label>
            <div className="flex flex-wrap gap-2">
              <input
                id="roster-search"
                type="search"
                className="input text-[13px] flex-1 min-w-[10rem]"
                placeholder={t('admin.sectionsRosterAddSearchPlaceholder')}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    searchStudents();
                  }
                }}
              />
              <button type="button" className="btn btn-outline text-[13px] px-3" onClick={searchStudents}>
                {t('admin.peopleSearchAction')}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                aria-label={t('admin.sectionsRosterAddSelectPlaceholder')}
                className="input text-[13px] flex-1 min-w-[10rem]"
                value={selectedStudentId}
                onChange={(event) => setSelectedStudentId(event.target.value)}
              >
                <option value="">{t('admin.sectionsRosterAddSelectPlaceholder')}</option>
                {availableCandidates.map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.full_name} — {candidate.email}
                  </option>
                ))}
              </select>
              <button
                type="submit"
                className="btn btn-accent text-[13px] px-4 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!selectedStudentId || adding}
              >
                {t('admin.sectionsRosterAddBtn')}
              </button>
            </div>
            {addError && (
              <p className="flex items-center gap-2 text-xs text-danger" role="alert">
                <AlertCircle size={14} className="shrink-0" />
                {addError}
              </p>
            )}
          </form>

          <AdminAsyncRegion
            loading={loading}
            error={error}
            empty={!loading && !error && (roster || []).length === 0}
            emptyMessage={t('admin.sectionsRosterEmpty')}
            onRetry={loadRoster}
          >
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">{t('admin.sectionsRosterColName')}</th>
                    <th scope="col">{t('admin.sectionsRosterColEmail')}</th>
                    <th scope="col">{t('admin.sectionsRosterColActions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(roster || []).map((row) => (
                    <tr key={row.studentId}>
                      <td className="text-fg">{row.fullName}</td>
                      <td className="text-fg-secondary">{row.email}</td>
                      <td>
                        <button
                          type="button"
                          className="font-bold text-danger cursor-pointer hover:underline outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                          onClick={() => {
                            setRemoveError('');
                            setRemoveTarget(row);
                          }}
                        >
                          {t('admin.sectionsRosterRemoveBtn')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </AdminAsyncRegion>
        </div>
      </div>

      <ConfirmDialog
        open={!!removeTarget}
        title={t('admin.sectionsRosterRemoveTitle')}
        message={t('admin.sectionsRosterRemoveConfirm')}
        confirmLabel={t('admin.sectionsRosterRemoveBtn')}
        cancelLabel={t('admin.cancelBtn')}
        danger
        busy={removeBusy}
        lang={lang}
        onConfirm={confirmRemove}
        onCancel={() => {
          setRemoveTarget(null);
          setRemoveError('');
        }}
      >
        {removeError && (
          <p className="flex items-center gap-2 text-xs text-danger" role="alert">
            <AlertCircle size={14} className="shrink-0" />
            {removeError}
          </p>
        )}
      </ConfirmDialog>
    </>
  );
}
