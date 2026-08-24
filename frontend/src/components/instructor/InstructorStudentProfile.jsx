import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Mail, AlertTriangle, ShieldAlert, StickyNote, Trash2,
  Eye, EyeOff, RefreshCw, Loader2,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  createStudentNote, deleteStudentNote, getStudentProfile, reviewAlert,
  userFacingApiError,
} from '../../lib/api';
import {
  riskLevelLabel, riskTypeLabel, isHighRisk, formatDetectedAt, blockReasonLabel,
} from '../../lib/riskLabels';
import RiskCaseDrawer from './RiskCaseDrawer';

/** A1 — ho so 360 cua 1 SV, mo tu link "Xem ho so" tren dashboard/guardrail.
 *  Chi gom lop/case thuoc ve GV dang xem (backend da loc), nen khong can loc
 *  gi them o day. */
export default function InstructorStudentProfile() {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const { t, lang } = useLanguage();

  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [noteDraft, setNoteDraft] = useState('');
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [noteError, setNoteError] = useState(null);
  const [deletingNoteId, setDeletingNoteId] = useState(null);

  const [expandedGuardrailId, setExpandedGuardrailId] = useState(null);
  const [openRiskId, setOpenRiskId] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [decisionErrors, setDecisionErrors] = useState({});
  const [sessionDecisions, setSessionDecisions] = useState({});

  const load = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await getStudentProfile(studentId);
      setProfile(data);
    } catch (err) {
      setLoadError(userFacingApiError(err, lang).message || t('instructor.profileLoadError'));
    } finally {
      setIsLoading(false);
    }
  }, [studentId, lang, t]);

  useEffect(() => {
    load();
  }, [load]);

  const submitNote = async () => {
    const content = noteDraft.trim();
    if (!content || isSavingNote) return;
    setIsSavingNote(true);
    setNoteError(null);
    try {
      await createStudentNote(studentId, content);
      setNoteDraft('');
      await load();
    } catch (err) {
      setNoteError(userFacingApiError(err, lang).message || t('instructor.noteSaveError'));
    } finally {
      setIsSavingNote(false);
    }
  };

  const removeNote = async (noteId) => {
    if (deletingNoteId) return;
    setDeletingNoteId(noteId);
    setNoteError(null);
    try {
      await deleteStudentNote(studentId, noteId);
      await load();
    } catch (err) {
      setNoteError(userFacingApiError(err, lang).message || t('instructor.noteDeleteError'));
    } finally {
      setDeletingNoteId(null);
    }
  };

  const anyDecisionPending = Boolean(pendingAction);
  const submitDecision = async (riskId, decision, note) => {
    if (!riskId || pendingAction) return;
    setDecisionErrors((prev) => {
      const next = { ...prev };
      delete next[riskId];
      return next;
    });
    setPendingAction({ riskId, decision });
    try {
      await reviewAlert(riskId, decision, note);
      setSessionDecisions((prev) => ({ ...prev, [riskId]: decision }));
      await load();
    } catch (err) {
      setDecisionErrors((prev) => ({ ...prev, [riskId]: err.message }));
    } finally {
      setPendingAction(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse p-6">
        <div className="h-20 bg-[#15181C] dark:bg-[#1C1A16] rounded-2xl border border-slate-700 dark:border-[#3A352C]" />
        <div className="h-40 bg-white dark:bg-[#1C1A16] rounded-2xl border border-slate-200 dark:border-[#3A352C]" />
      </div>
    );
  }

  if (loadError || !profile) {
    return (
      <div className="p-12 text-center space-y-4 max-w-lg mx-auto bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-2xl my-8 shadow-xl">
        <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400 mx-auto" />
        <h3 className="text-lg font-black text-red-900 dark:text-red-200 font-serif-heading">{t('states.errorTitle')}</h3>
        <p className="text-xs text-red-800 dark:text-red-300/90 font-medium">{loadError || t('states.errorDesc')}</p>
        <button
          onClick={load}
          className="px-4 py-2 bg-danger-ink hover:bg-[#7F2F2A] text-white text-xs font-bold rounded-xl inline-flex items-center gap-2 cursor-pointer shadow-md"
        >
          <RefreshCw className="w-4 h-4" /> {t('states.retryBtn')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-400 hover:text-accent cursor-pointer"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> {t('instructor.backBtn')}
      </button>

      {/* HEADER */}
      <div className="cursus-hero-banner rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 text-white">
        <div className="space-y-1 min-w-0">
          <h1 className="text-2xl font-black text-white font-serif-heading truncate">{profile.displayName}</h1>
          <p className="text-xs text-slate-200 font-medium flex items-center gap-1.5">
            <Mail className="w-3.5 h-3.5" /> {profile.email}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 justify-end">
          {profile.courses.map((course) => (
            <span
              key={course.sectionId}
              className="inline-flex items-center px-3 py-1 bg-white/10 border border-white/20 rounded-full text-xs font-extrabold text-accent backdrop-blur-md font-mono-code"
            >
              {course.code}
            </span>
          ))}
          {profile.courses.length === 0 && (
            <span className="text-xs text-slate-200">{t('instructor.profileNoCourses')}</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* COT 1: XU HUONG HOAN THANH + GHI CHU RIENG (A2 du lieu / A3) */}
        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <h2 className="text-base font-black text-fg font-serif-heading">
              {t('instructor.profileWeeklyTitle')}
            </h2>
            {profile.weeklyCompletionHistory.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('instructor.profileWeeklyEmpty')}</p>
            ) : (
              <div className="space-y-3">
                {profile.weeklyCompletionHistory.map((item) => (
                  <div key={item.week} className="space-y-1">
                    <div className="flex justify-between text-xs text-[#15181C] dark:text-slate-200 font-bold">
                      <span>W{item.week}</span>
                      <span className="font-mono-code">{item.rate}%</span>
                    </div>
                    <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-3 overflow-hidden border border-slate-300 dark:border-slate-700">
                      <div
                        className={`${item.rate >= 75 ? 'bg-success-ink' : 'bg-amber-500'} h-full transition-all duration-500`}
                        style={{ width: `${item.rate}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* C2 — TOM TAT PHAN TU (chi so, khong bao gio la van ban goc SV go —
              xem _serialize_reflection_summary o backend). An khi SV chua bat
              consent, thay vi hien khoi rong gay hieu nham la "chua co du lieu". */}
          {profile.reflectionSharingEnabled && profile.reflectionSummary.length > 0 && (
            <div className="card p-6 space-y-4">
              <h2 className="text-base font-black text-fg font-serif-heading">
                {t('instructor.reflectionSummaryTitle')}
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                {t('instructor.reflectionSummaryPrivacyNote')}
              </p>
              <div className="space-y-2 max-h-[16rem] overflow-y-auto pr-1">
                {profile.reflectionSummary.map((entry) => (
                  <div
                    key={entry.weekNumber}
                    className="p-3 rounded-xl border border-line flex items-center justify-between gap-3 text-xs"
                  >
                    <span className="font-black text-fg shrink-0">W{entry.weekNumber}</span>
                    <span className="text-slate-600 dark:text-slate-400 font-mono-code">
                      {entry.completionRate == null ? '—' : `${entry.completionRate}%`}
                    </span>
                    <span className="text-slate-600 dark:text-slate-400 font-mono-code">
                      {entry.hoursActual ?? '—'}/{entry.hoursPlanned ?? '—'}h
                    </span>
                    {entry.requestedHelp && (
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase bg-danger-soft dark:bg-red-950/60 text-danger-ink dark:text-red-300 shrink-0">
                        {t('instructor.reflectionRequestedHelp')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* A3 — SO GHI CHU RIENG */}
          <div className="card p-6 space-y-4">
            <h2 className="text-base font-black text-fg font-serif-heading flex items-center gap-2">
              <StickyNote className="w-4 h-4 text-accent" /> {t('instructor.notesTitle')}
            </h2>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{t('instructor.notesHint')}</p>

            <div className="space-y-2">
              <textarea
                className="textarea text-xs w-full min-h-[64px]"
                placeholder={t('instructor.notesPlaceholder')}
                value={noteDraft}
                onChange={(event) => setNoteDraft(event.target.value)}
                disabled={isSavingNote}
              />
              <button
                type="button"
                onClick={submitNote}
                disabled={isSavingNote || !noteDraft.trim()}
                className="btn btn-orange text-xs px-3 py-1.5 disabled:opacity-60 disabled:cursor-wait"
              >
                {isSavingNote ? <Loader2 size={12} className="animate-spin" /> : null}
                {t('instructor.addNoteBtn')}
              </button>
              {noteError && <p className="text-[11px] font-bold text-red-700 dark:text-red-400">{noteError}</p>}
            </div>

            {profile.notes.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('instructor.notesEmpty')}</p>
            ) : (
              <div className="space-y-2 max-h-[18rem] overflow-y-auto pr-1">
                {profile.notes.map((note) => (
                  <div
                    key={note.id}
                    className="p-3 rounded-xl bg-surface-elevated border border-line flex items-start justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <p className="text-xs text-[#15181C] dark:text-slate-100 font-medium whitespace-pre-wrap break-words">
                        {note.content}
                      </p>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono-code mt-1">
                        {formatDetectedAt(note.createdAt, lang)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeNote(note.id)}
                      disabled={deletingNoteId === note.id}
                      aria-label={t('instructor.deleteNoteBtn')}
                      className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-red-600 dark:hover:text-red-400 cursor-pointer shrink-0 disabled:opacity-50"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* COT 2: LICH SU RUI RO (F5) + GUARDRAIL */}
        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <h2 className="text-base font-black text-fg font-serif-heading flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-accent" /> {t('instructor.profileRiskHistoryTitle')}
            </h2>
            {profile.riskHistory.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('instructor.profileRiskHistoryEmpty')}</p>
            ) : (
              <div className="space-y-2 max-h-[22rem] overflow-y-auto pr-1">
                {profile.riskHistory.map((risk) => {
                  const high = isHighRisk(risk.riskLevel);
                  const levelLabel = riskLevelLabel(t, risk.riskLevel);
                  const typeLabel = riskTypeLabel(t, risk.riskType);
                  const resolved = risk.status === 'INTERVENTION_APPROVED';
                  return (
                    <button
                      key={risk.id}
                      type="button"
                      onClick={() => setOpenRiskId(risk.id)}
                      className="w-full text-left p-3 rounded-xl border border-line hover:border-accent/50 transition-colors cursor-pointer space-y-1"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          {levelLabel && (
                            <span className={`px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase ${
                              high ? 'bg-danger-soft text-danger-ink' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                            }`}>
                              {levelLabel}
                            </span>
                          )}
                          <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">{typeLabel}</span>
                        </div>
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono-code">
                          {formatDetectedAt(risk.generatedAt, lang)}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400">
                        {resolved ? t('instructor.resolvedBadge') : t('instructor.statusPending')}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="card p-6 space-y-4">
            <h2 className="text-base font-black text-fg font-serif-heading flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-danger-ink" /> {t('instructor.profileGuardrailHistoryTitle')}
            </h2>
            {profile.guardrailHistory.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('instructor.profileGuardrailHistoryEmpty')}</p>
            ) : (
              <div className="space-y-2 max-h-[22rem] overflow-y-auto pr-1">
                {profile.guardrailHistory.map((item) => {
                  const isExpanded = expandedGuardrailId === item.id;
                  return (
                    <div
                      key={item.id}
                      className="p-3 bg-surface-elevated border border-line rounded-xl space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2 text-xs">
                        <span className="inline-block px-2 py-0.5 rounded-md bg-danger-soft dark:bg-red-950/60 text-danger-ink dark:text-red-300 text-[10px] font-black font-mono-code uppercase">
                          {blockReasonLabel(t, item.blockReason)}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400 font-mono-code text-[10px]">
                          {formatDetectedAt(item.createdAt, lang)}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setExpandedGuardrailId(isExpanded ? null : item.id)}
                        aria-expanded={isExpanded}
                        className="text-[11px] font-black text-accent hover:text-accent-hover inline-flex items-center gap-1 cursor-pointer"
                      >
                        {isExpanded ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        {isExpanded ? t('guardrail.hideContent') : t('guardrail.showContent')}
                      </button>
                      {isExpanded && (
                        <div className="p-2.5 bg-white dark:bg-[#1C1A16] border border-line rounded-lg text-xs text-slate-800 dark:text-slate-200 italic">
                          "{item.question}"
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
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
