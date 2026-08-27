import React, { useState } from 'react';
import type { Assignment, CourseDetail as CourseDetailData, Identity } from '../types';
import { ApiError, updateDueDate } from '../lib/api';
import { useLanguage } from '../context/LanguageContext';

export function CourseDetail({
  course,
  identity,
  onCourseUpdate,
}: {
  course: CourseDetailData;
  identity: Identity;
  onCourseUpdate: (course: CourseDetailData) => void;
}) {
  const { t } = useLanguage();
  const isAdmin = identity.role === 'ADMIN';

  return (
    <div className="max-w-5xl mx-auto px-5 py-8 space-y-5">
      {/* Global Breadcrumbs (App.tsx) already has an "Assignment & Deadline"
          crumb pointing back to the course list -- no duplicate back-link. */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">
          {course.code} — {course.name}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          {course.semester} &middot; {course.credit} {t('courseDetail.creditsUnit')} &middot; {course.assignments.length} {t('courseDetail.assignmentsUnit')}
        </p>
      </div>

      <div className="card overflow-hidden">
        <table className="data-table">
          <thead>
            <tr>
              <Th>{t('courseDetail.tableAssignment')}</Th>
              <Th>{t('courseDetail.tableDueDate')}</Th>
              <Th>{t('courseDetail.tableScore')}</Th>
              <Th>{t('courseDetail.tableUpdatedAt')}</Th>
              {isAdmin && <Th>{t('courseDetail.tableEditDeadline')}</Th>}
            </tr>
          </thead>
          <tbody>
            {course.assignments.map((a) => (
              <AssignmentRow
                key={a.id}
                courseCode={course.code}
                assignment={a}
                isAdmin={isAdmin}
                onSaved={onCourseUpdate}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left font-bold uppercase tracking-wide text-slate-500">
      {children}
    </th>
  );
}

function AssignmentRow({
  courseCode,
  assignment,
  isAdmin,
  onSaved,
}: {
  courseCode: string;
  assignment: Assignment;
  isAdmin: boolean;
  onSaved: (course: CourseDetailData) => void;
}) {
  const { t } = useLanguage();
  const [dueAt, setDueAt] = useState(assignment.dueAt.slice(0, 10));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    const confirmed = window.confirm(
      `${t('courseDetail.confirmChangePrefix')} '${assignment.name}' ${t('courseDetail.confirmChangeMiddle')} ${assignment.dueAt.slice(0, 10)} ${t('courseDetail.confirmChangeSuffix')} ${dueAt}?`,
    );
    if (!confirmed) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateDueDate(courseCode, assignment.id, dueAt);
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('courseDetail.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="group">
      <td>
        <div className="font-bold text-slate-900">{assignment.name}</div>
        {assignment.description && (
          <div className="text-xs text-slate-500 mt-0.5">{assignment.description}</div>
        )}
      </td>
      <td className="mono">
        {assignment.dueAt.slice(0, 10)}{' '}
        <span className={assignment.isPastDue ? 'badge badge-warning' : 'badge badge-success'}>
          {assignment.isPastDue ? t('courseDetail.pastDue') : t('courseDetail.upcoming')}
        </span>
      </td>
      <td className="mono">{assignment.pointsPossible}</td>
      <td className="mono text-slate-500">
        {assignment.updatedAt.slice(0, 16).replace('T', ' ')}
      </td>
      {isAdmin && (
        <td>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
              aria-label={`${t('courseDetail.dueDateAriaLabelPrefix')} ${assignment.name}`}
              disabled={saving}
              className="border border-slate-300 rounded-md px-2 py-1 text-xs outline-none focus:border-blue-500"
            />
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-semibold px-3 py-1.5 rounded-md"
            >
              {saving ? t('courseDetail.savingBtn') : t('courseDetail.saveBtn')}
            </button>
          </div>
          {error && <div className="text-[11px] text-red-600 mt-1">{error}</div>}
        </td>
      )}
    </tr>
  );
}
