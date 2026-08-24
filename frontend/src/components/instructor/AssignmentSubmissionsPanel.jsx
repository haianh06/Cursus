import React, { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, FileCheck2 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  getAssignmentSubmissions,
  getInstructorDashboard,
  listInstructorAssignments,
  userFacingApiError,
} from '../../lib/api';

function formatDateTimeLabel(iso) {
  if (!iso) return '';
  return iso.replace('T', ' ').slice(0, 16);
}

/** A4 — ai da nop / chua nop cho 1 assignment cu the, thay vi chi co % hoan
 *  thanh gop ca lop (F4). Tu chon assignment (khong loc theo bo loc lop F9
 *  cua dashboard, vi GV can xem duoc assignment cua BAT KY lop nao minh day
 *  tu day, khong phu thuoc bo loc dang chon o tren). */
export default function AssignmentSubmissionsPanel() {
  const { t, lang } = useLanguage();
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState('');
  const [roster, setRoster] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedStudentId, setExpandedStudentId] = useState(null);

  const loadAssignments = useCallback(async () => {
    setError('');
    try {
      const [dash, list] = await Promise.all([
        getInstructorDashboard(),
        listInstructorAssignments(),
      ]);
      setCourses(dash?.raw?.courses || []);
      setAssignments(list);
      setSelectedAssignmentId((current) => {
        if (current && list.some((item) => item.id === current)) return current;
        return list[0]?.id || '';
      });
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.submissionsError'));
    }
  }, [lang, t]);

  useEffect(() => {
    loadAssignments();
  }, [loadAssignments]);

  useEffect(() => {
    setExpandedStudentId(null);
    if (!selectedAssignmentId) {
      setRoster(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError('');
    getAssignmentSubmissions(selectedAssignmentId)
      .then((data) => {
        if (!cancelled) setRoster(data);
      })
      .catch((err) => {
        if (!cancelled) setError(userFacingApiError(err, lang).message || t('instructor.submissionsError'));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedAssignmentId, lang, t]);

  const courseByCode = (courseId) => courses.find((c) => c.id === courseId);

  return (
    <div className="space-y-6 pb-12">
      <div className="cursus-hero-banner rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 text-white">
        <div className="space-y-1 min-w-0">
          <h1 className="text-2xl font-black text-white font-serif-heading">{t('instructor.submissionsTitle')}</h1>
          <p className="text-xs text-slate-200 font-medium">{t('instructor.submissionsHint')}</p>
        </div>
      </div>

      <div className="card p-6 space-y-4 text-left">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <h2 className="text-base font-black text-fg flex items-center gap-2 font-serif-heading">
            <FileCheck2 className="w-5 h-5 text-accent" />
            <span>{t('instructor.submissionsTitle')}</span>
          </h2>
        </div>

        {assignments.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
            {t('instructor.submissionsEmpty')}
          </div>
        ) : (
          <>
            <label className="block max-w-sm">
              <span className="text-xs font-semibold text-fg-secondary">{t('instructor.submissionsPickAssignment')}</span>
              <select
                className="mt-1.5 w-full h-10 rounded-lg border border-line bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
                value={selectedAssignmentId}
                onChange={(event) => setSelectedAssignmentId(event.target.value)}
              >
                {assignments.map((item) => {
                  const course = courseByCode(item.courseId);
                  return (
                    <option key={item.id} value={item.id}>
                      {(course?.code || item.courseId)} · {item.title}
                    </option>
                  );
                })}
              </select>
            </label>

            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-xl flex items-start gap-2" role="alert">
                <span className="text-[11px] font-bold text-red-900 dark:text-red-300">{error}</span>
              </div>
            )}

            {isLoading ? (
              <p className="text-xs text-fg-muted">{t('states.loadingTitle')}</p>
            ) : roster ? (
              roster.submissions.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
                  {t('instructor.submissionsNoStudents')}
                </div>
              ) : (
                <ul className="divide-y divide-line border border-line rounded-2xl max-h-[28rem] overflow-y-auto">
                  {roster.submissions.map((row) => {
                    const expanded = expandedStudentId === row.studentId;
                    return (
                      <li key={row.studentId}>
                        <button
                          type="button"
                          className="w-full px-3 py-2.5 flex items-center justify-between gap-3 text-left cursor-pointer disabled:cursor-default"
                          disabled={!row.submitted}
                          onClick={() => setExpandedStudentId(expanded ? null : row.studentId)}
                        >
                          <span className="text-sm text-fg font-medium inline-flex items-center gap-1.5">
                            {row.submitted && (expanded ? <ChevronUp size={13} className="text-slate-400 shrink-0" /> : <ChevronDown size={13} className="text-slate-400 shrink-0" />)}
                            {row.displayName}
                          </span>
                          {row.submitted ? (
                            <span className="inline-flex items-center gap-2">
                              {row.grade != null && (
                                <span className="font-mono-code text-xs font-black text-fg">{row.grade}%</span>
                              )}
                              <span
                                className={`px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase ${
                                  row.isLate
                                    ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                                    : 'bg-success-soft text-success-ink dark:bg-emerald-950/40 dark:text-emerald-300'
                                }`}
                              >
                                {row.isLate ? t('instructor.submissionLate') : t('instructor.submissionOnTime')}
                              </span>
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase bg-danger-soft text-danger-ink">
                              {t('instructor.submissionMissing')}
                            </span>
                          )}
                        </button>
                        {expanded && (
                          <div className="px-3 pb-3 -mt-1">
                            <div className="rounded-xl border border-line bg-surface-elevated p-3 space-y-2">
                              <p className="text-[10px] font-black uppercase tracking-wide text-slate-500 dark:text-slate-400">
                                {t('instructor.submissionDetailTitle')}
                              </p>
                              <p className="text-xs text-[#15181C] dark:text-slate-100 whitespace-pre-wrap">
                                {row.content?.text || t('instructor.submissionDetailEmpty')}
                              </p>
                              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500 dark:text-slate-400 font-mono-code pt-1 border-t border-line">
                                {row.submittedAt && <span>{t('instructor.submissionSubmittedAt')}: {formatDateTimeLabel(row.submittedAt)}</span>}
                                {row.gradingStatus && <span>{t('instructor.submissionGradingStatus')}: {row.gradingStatus}</span>}
                              </div>
                              {row.feedback && (
                                <p className="text-xs text-slate-600 dark:text-slate-400 italic">
                                  {t('instructor.submissionFeedbackLabel')}: {row.feedback}
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
