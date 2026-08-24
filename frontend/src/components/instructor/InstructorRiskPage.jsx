import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle, Lock, RefreshCw, Check, ShieldOff, Clock, FileText, Eye,
  UserCircle2,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  bulkReviewAlerts, getInstructorAlerts, getInstructorDashboard, reviewAlert,
} from '../../lib/api';
import RiskCaseDrawer from './RiskCaseDrawer';
import { riskLevelLabel, riskTypeLabel, isHighRisk, formatDetectedAt } from '../../lib/riskLabels';

/** Tach rieng tu InstructorHome.jsx (dashboard chi con so lieu thong ke +
 *  thong bao gon) — trang nay giu nguyen toan bo logic HITL (F5/B1/B2). */
export default function InstructorRiskPage() {
  const { t, lang } = useLanguage();

  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('ALL');
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [decisionErrors, setDecisionErrors] = useState({});
  const [pendingAction, setPendingAction] = useState(null);
  const [sessionDecisions, setSessionDecisions] = useState({});
  const [openRiskId, setOpenRiskId] = useState(null);
  const [selectedRiskIds, setSelectedRiskIds] = useState(() => new Set());
  const [bulkNote, setBulkNote] = useState('');
  const [isBulkSubmitting, setIsBulkSubmitting] = useState(null);
  const [bulkError, setBulkError] = useState(null);

  const load = async ({ silent = false } = {}) => {
    if (!silent) setIsLoading(true);
    setLoadError(null);
    setActionError(null);
    try {
      const [dashboard, alertData] = await Promise.all([
        getInstructorDashboard(selectedCourseId),
        getInstructorAlerts(selectedCourseId),
      ]);
      setCourses(dashboard.courses);
      setAlerts(Array.isArray(alertData) ? alertData : []);
    } catch (err) {
      if (silent) setActionError(err.message);
      else setLoadError(err.message);
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCourseId]);

  const viewState = isLoading ? 'loading' : loadError ? 'error' : 'success';

  const pendingAlertCount = alerts.filter(
    item => item.status !== 'INTERVENTION_APPROVED' && !sessionDecisions[item.id]
  ).length;

  const anyDecisionPending = Boolean(pendingAction);

  const submitDecision = async (riskId, decision, note) => {
    if (!riskId || pendingAction) return;
    setDecisionErrors(prev => {
      const next = { ...prev };
      delete next[riskId];
      return next;
    });
    setPendingAction({ riskId, decision });
    try {
      await reviewAlert(riskId, decision, note);
      setSessionDecisions(prev => ({ ...prev, [riskId]: decision }));
      await load({ silent: true });
    } catch (err) {
      setDecisionErrors(prev => ({ ...prev, [riskId]: err.message }));
    } finally {
      setPendingAction(null);
    }
  };

  const toggleRiskSelected = (riskId) => {
    setSelectedRiskIds(prev => {
      const next = new Set(prev);
      if (next.has(riskId)) next.delete(riskId);
      else next.add(riskId);
      return next;
    });
  };

  const submitBulkDecision = async (decision) => {
    if (selectedRiskIds.size === 0 || isBulkSubmitting || anyDecisionPending) return;
    setIsBulkSubmitting(decision);
    setBulkError(null);
    try {
      const result = await bulkReviewAlerts(Array.from(selectedRiskIds), decision, bulkNote || undefined);
      if (result.failedCount > 0) {
        setBulkError(t('instructor.bulkPartialFailure', { count: result.failedCount }));
      }
      setSelectedRiskIds(new Set());
      setBulkNote('');
      await load({ silent: true });
    } catch (err) {
      setBulkError(err.message);
    } finally {
      setIsBulkSubmitting(null);
    }
  };

  if (viewState === 'loading') {
    return (
      <div className="space-y-6 animate-pulse p-6">
        <div className="h-20 bg-[#15181C] dark:bg-[#1C1A16] rounded-2xl border border-slate-700 dark:border-[#3A352C]" />
        <div className="h-96 bg-white dark:bg-[#1C1A16] rounded-2xl border border-slate-200 dark:border-[#3A352C]" />
      </div>
    );
  }

  if (viewState === 'error') {
    return (
      <div className="p-12 text-center space-y-4 max-w-lg mx-auto bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-2xl my-8 shadow-xl">
        <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400 mx-auto" />
        <h3 className="text-lg font-black text-red-900 dark:text-red-200 font-serif-heading">{t('states.errorTitle')}</h3>
        <p className="text-xs text-red-800 dark:text-red-300/90 font-medium">{t('states.errorDesc')}</p>
        {loadError && (
          <p className="text-[11px] text-red-700 dark:text-red-400/90 font-mono-code break-words">{loadError}</p>
        )}
        <button
          onClick={() => load()}
          className="px-4 py-2 bg-danger-ink hover:bg-[#7F2F2A] text-white text-xs font-bold rounded-xl inline-flex items-center gap-2 cursor-pointer shadow-md"
        >
          <RefreshCw className="w-4 h-4" /> {t('states.retryBtn')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      <div className="cursus-hero-banner rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 text-white">
        <div className="space-y-1 min-w-0">
          <h1 className="text-2xl font-black text-white font-serif-heading">{t('instructor.atRiskStudents')}</h1>
          <p className="text-xs text-slate-200 font-medium">{t('instructor.pageSubtitle')}</p>
        </div>
        {courses.length > 1 && (
          <label className="flex items-center gap-2 text-xs font-bold text-white shrink-0">
            <span className="sr-only">{t('instructor.filterLabel')}</span>
            <select
              value={selectedCourseId}
              onChange={(event) => { setSelectedCourseId(event.target.value); setOpenRiskId(null); }}
              className="bg-white/10 border border-white/20 rounded-xl px-3 py-1.5 text-xs font-bold text-white backdrop-blur-md cursor-pointer [&>option]:text-[#15181C]"
            >
              <option value="ALL">{t('instructor.allCourses')}</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>{course.code}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <h2 className="text-base font-black text-fg flex items-center gap-2 font-serif-heading">
            <AlertTriangle className="w-5 h-5 text-accent" />
            <span>{t('instructor.atRiskStudents')}</span>
          </h2>
          <span className="text-xs text-amber-700 dark:text-amber-400 font-extrabold font-mono-code">
            {t('instructor.alertsPending', { count: pendingAlertCount })}
          </span>
        </div>

        {actionError && (
          <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-xl flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-px" />
            <span className="text-[11px] font-bold text-red-900 dark:text-red-300">{actionError}</span>
          </div>
        )}

        {selectedRiskIds.size > 0 && (
          <div className="p-3 rounded-xl border border-accent/40 bg-accent-soft space-y-2">
            <p className="text-xs font-black text-fg">
              {t('instructor.bulkSelectedCount', { count: selectedRiskIds.size })}
            </p>
            <textarea
              className="input text-xs w-full min-h-[52px]"
              placeholder={t('instructor.notePlaceholder')}
              value={bulkNote}
              onChange={(event) => setBulkNote(event.target.value)}
              disabled={Boolean(isBulkSubmitting)}
            />
            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => submitBulkDecision('APPROVE')}
                disabled={Boolean(isBulkSubmitting) || anyDecisionPending}
                className="px-3 py-1.5 rounded-xl text-xs font-black bg-accent hover:bg-accent-hover text-white shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
              >
                {isBulkSubmitting === 'APPROVE' ? t('instructor.sending') : t('instructor.bulkApproveBtn')}
              </button>
              <button
                type="button"
                onClick={() => submitBulkDecision('REJECT')}
                disabled={Boolean(isBulkSubmitting) || anyDecisionPending}
                className="px-3 py-1.5 rounded-xl text-xs font-black border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
              >
                {isBulkSubmitting === 'REJECT' ? t('instructor.sending') : t('instructor.bulkDismissBtn')}
              </button>
              <button
                type="button"
                onClick={() => { setSelectedRiskIds(new Set()); setBulkNote(''); }}
                disabled={Boolean(isBulkSubmitting)}
                className="text-xs font-bold text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer"
              >
                {t('instructor.bulkClearSelection')}
              </button>
            </div>
            {bulkError && (
              <p className="text-[11px] font-bold text-red-700 dark:text-red-400">{bulkError}</p>
            )}
          </div>
        )}

        {alerts.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
            {t('instructor.alertsEmpty')}
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-[11px] text-slate-600 dark:text-slate-400 font-medium flex items-start gap-1.5">
              <Lock className="w-3 h-3 shrink-0 mt-0.5" />
              <span>{t('instructor.noNotificationNote')}</span>
            </p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 max-h-[36rem] overflow-y-auto pr-1 content-start">
              {alerts.map(alertItem => {
                const riskId = alertItem.id;
                const decision = sessionDecisions[riskId];
                const resolved = alertItem.status === 'INTERVENTION_APPROVED' || Boolean(decision);
                const busyDecision = pendingAction?.riskId === riskId ? pendingAction.decision : null;
                const decisionError = decisionErrors[riskId];
                const isHigh = isHighRisk(alertItem.riskLevel);
                const levelLabel = riskLevelLabel(t, alertItem.riskLevel);
                const typeLabel = riskTypeLabel(t, alertItem.riskType);
                const detectedAt = formatDetectedAt(alertItem.generatedAt, lang);

                let cardTone = 'bg-amber-50 dark:bg-amber-950/40 border-amber-300 dark:border-amber-700/60 border-l-4 border-l-amber-500 shadow-xs';
                if (resolved && decision === 'APPROVE') {
                  cardTone = 'bg-success-soft dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-700/60 border-l-4 border-l-success-ink';
                } else if (resolved) {
                  cardTone = 'bg-slate-100 dark:bg-slate-900/50 border-slate-300 dark:border-slate-700 border-l-4 border-l-slate-400';
                } else if (isHigh) {
                  cardTone = 'bg-danger-soft dark:bg-red-950/30 border-red-300 dark:border-red-800/60 border-l-4 border-l-danger-ink shadow-xs';
                }

                return (
                  <div key={riskId} className={`p-3.5 rounded-2xl border transition-all space-y-1.5 flex flex-col ${cardTone}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2.5 min-w-0">
                        {!resolved && (
                          <input
                            type="checkbox"
                            aria-label={t('instructor.bulkSelectOne')}
                            checked={selectedRiskIds.has(riskId)}
                            onChange={() => toggleRiskSelected(riskId)}
                            className="mt-1 w-3.5 h-3.5 accent-[color:var(--accent)] cursor-pointer shrink-0"
                          />
                        )}
                        <div className="space-y-1 min-w-0">
                          <Link
                            to={`/instructor/students/${alertItem.studentId}`}
                            className="font-black text-sm text-fg flex items-center gap-1 truncate hover:text-accent transition-colors w-fit"
                          >
                            <UserCircle2 className="w-3.5 h-3.5 shrink-0 opacity-60" />
                            <span className="truncate">{alertItem.studentAlias}</span>
                          </Link>
                          <div className="flex flex-wrap items-center gap-2">
                            {typeLabel && (
                              <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">{typeLabel}</span>
                            )}
                            {!resolved && alertItem.isOverdue && (
                              <span className="px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase bg-danger-soft text-danger-ink">
                                {t('instructor.overdueBadge', { days: alertItem.daysOpen })}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Muc do rui ro luon o goc tren-phai cua the, khong deo theo do dai ten. */}
                      {levelLabel && (
                        <span className={`shrink-0 px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase ${isHigh
                            ? 'bg-danger-soft text-danger-ink'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                          }`}>
                          {levelLabel}
                        </span>
                      )}
                    </div>

                    {decisionError && (
                      <div className="p-2.5 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800/60 rounded-xl flex items-start gap-2" role="alert">
                        <AlertTriangle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0 mt-px" />
                        <span className="text-[11px] font-bold text-red-900 dark:text-red-200 break-words">{decisionError}</span>
                      </div>
                    )}

                    <p className="text-xs text-[#15181C] dark:text-slate-100 font-extrabold leading-snug line-clamp-2">
                      {t('instructor.reasonLabel')}: {typeLabel || alertItem.riskType}
                    </p>
                    <p className="text-xs text-slate-700 dark:text-slate-300 font-medium leading-snug line-clamp-2">
                      {t('instructor.actionLabel')}: {alertItem.recommendedIntervention}
                    </p>

                    {(alertItem.assignmentTitle || detectedAt) && (
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                        {alertItem.assignmentTitle && (
                          <span className="inline-flex items-center gap-1 min-w-0 max-w-full">
                            <FileText className="w-3 h-3 shrink-0" />
                            <span className="truncate">{alertItem.assignmentTitle}</span>
                          </span>
                        )}
                        {detectedAt && (
                          <span className="inline-flex items-center gap-1 font-mono-code shrink-0">
                            <Clock className="w-3 h-3 shrink-0" />
                            {detectedAt}
                          </span>
                        )}
                      </div>
                    )}
                    {/* Tinh trang xu ly (hoac 2 nut hanh dong khi chua xu ly) luon o
                        goc duoi-phai, chi rong bang noi dung — khong keo dai het the. */}
                    <div className="flex items-center justify-between gap-2 mt-auto pt-1">
                      <button
                        type="button"
                        onClick={() => setOpenRiskId(riskId)}
                        className="text-[11px] font-black text-accent hover:text-accent-hover inline-flex items-center gap-1 cursor-pointer shrink-0"
                      >
                        <Eye className="w-3 h-3" />
                        {t('instructor.detailBtn')}
                      </button>

                      {resolved ? (
                        <span className={`px-3 py-1 rounded-xl text-xs font-black flex items-center gap-1 shrink-0 ${decision === 'APPROVE'
                            ? 'bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 text-emerald-900 dark:text-[#A7D4B0]'
                            : 'bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200'
                          }`}>
                          {decision === 'REJECT' ? <ShieldOff className="w-3.5 h-3.5" /> : <Check className="w-3.5 h-3.5" />}
                          <span>
                            {decision === 'APPROVE' && t('instructor.intervenedBadge')}
                            {decision === 'REJECT' && t('instructor.dismissedBadge')}
                            {!decision && t('instructor.resolvedBadge')}
                          </span>
                        </span>
                      ) : (
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            onClick={() => submitDecision(riskId, 'APPROVE')}
                            disabled={anyDecisionPending}
                            className="px-3 py-1 rounded-xl text-xs font-black bg-accent hover:bg-accent-hover text-white shadow-xs transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                          >
                            {busyDecision === 'APPROVE' ? t('instructor.sending') : t('instructor.interveneBtn')}
                          </button>
                          <button
                            onClick={() => submitDecision(riskId, 'REJECT')}
                            disabled={anyDecisionPending}
                            className="px-3 py-1 rounded-xl text-xs font-black border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                          >
                            {busyDecision === 'REJECT' ? t('instructor.sending') : t('instructor.dismissBtn')}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <RiskCaseDrawer
        riskId={openRiskId}
        open={Boolean(openRiskId)}
        onClose={() => setOpenRiskId(null)}
        decision={openRiskId ? sessionDecisions[openRiskId] : undefined}
        onDecision={submitDecision}
        anyDecisionPending={anyDecisionPending}
        busyDecision={pendingAction?.riskId === openRiskId ? pendingAction.decision : null}
        decisionError={openRiskId ? decisionErrors[openRiskId] : null}
      />
    </div>
  );
}
