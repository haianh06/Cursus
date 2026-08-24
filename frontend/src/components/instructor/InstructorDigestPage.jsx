import React, { useCallback, useEffect, useState } from 'react';
import {
  Mail, AlertTriangle, ShieldAlert, Award, RefreshCw, Send, Eye, EyeOff, Loader2,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  blockReasonLabel, formatDetectedAt, isHighRisk, riskLevelLabel, riskTypeLabel,
} from '../../lib/riskLabels';
import { getInstructorDigest, sendInstructorDigestEmail, userFacingApiError } from '../../lib/api';

const DAY_OPTIONS = [7, 14, 30];

/** C1 — tom tat case moi phat sinh trong N ngay gan nhat, tinh on-demand
 *  (khong co scheduler/cron gui dinh ky tu dong — GV tu mo trang nay hoac tu
 *  bam gui email khi can). */
export default function InstructorDigestPage() {
  const { t, lang } = useLanguage();
  const [days, setDays] = useState(7);
  const [digest, setDigest] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [expandedGuardrailId, setExpandedGuardrailId] = useState(null);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [emailResult, setEmailResult] = useState(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      setDigest(await getInstructorDigest(days));
    } catch (err) {
      setLoadError(userFacingApiError(err, lang).message || t('instructor.digestLoadError'));
    } finally {
      setIsLoading(false);
    }
  }, [days, lang, t]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSendEmail = async () => {
    setIsSendingEmail(true);
    setEmailResult(null);
    try {
      const result = await sendInstructorDigestEmail(days);
      setEmailResult({ ok: true, to: result.to });
    } catch (err) {
      setEmailResult({ ok: false, message: userFacingApiError(err, lang).message });
    } finally {
      setIsSendingEmail(false);
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

  if (loadError || !digest) {
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

  const { summary, newRiskCases, newGuardrailCases, kudos } = digest;

  return (
    <div className="space-y-6 pb-12">
      <div className="bg-surface-elevated border border-line rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-1 min-w-0">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-surface border border-line rounded-full text-xs font-extrabold text-accent font-mono-code">
            <Mail className="w-3.5 h-3.5 text-accent" />
            <span>{t('instructor.digestSince', { date: digest.sinceDate })}</span>
          </div>
          <h1 className="text-2xl font-black text-fg font-serif-heading">{t('instructor.digestTitle')}</h1>
          <p className="text-xs text-fg-muted font-medium">{t('instructor.digestSubtitle')}</p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            className="bg-surface border border-line rounded-xl px-3 py-1.5 text-xs font-bold text-fg cursor-pointer"
          >
            {DAY_OPTIONS.map((d) => (
              <option key={d} value={d}>{t('instructor.digestDaysOption', { days: d })}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { key: 'risk', label: t('instructor.digestNewRisk'), value: summary.newRiskCount, danger: true },
          { key: 'guardrail', label: t('instructor.digestNewGuardrail'), value: summary.newGuardrailCount, danger: true },
          { key: 'kudos', label: t('instructor.digestKudosCount'), value: summary.kudosCount, danger: false },
        ].map((metric) => (
          <div key={metric.key} className="card p-5 space-y-1">
            <span className="text-xs font-black text-fg">{metric.label}</span>
            <div className={`text-3xl font-black font-mono-code ${metric.danger && metric.value > 0 ? 'text-danger-ink dark:text-red-400' : 'text-accent'}`}>
              {metric.value}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-1.5">
        <button
          type="button"
          onClick={handleSendEmail}
          disabled={isSendingEmail}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
        >
          {isSendingEmail ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          {isSendingEmail ? t('instructor.digestSending') : t('instructor.digestSendEmailBtn')}
        </button>
        {emailResult?.ok && (
          <p className="text-[11px] font-bold text-emerald-700 dark:text-emerald-400">
            {t('instructor.digestSendSuccess', { email: emailResult.to })}
          </p>
        )}
        {emailResult && !emailResult.ok && (
          <p className="text-[11px] font-bold text-red-700 dark:text-red-400">{emailResult.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="card p-6 space-y-4">
          <h2 className="text-base font-black text-fg font-serif-heading flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-accent" /> {t('instructor.digestNewRisk')}
          </h2>
          {newRiskCases.length === 0 ? (
            <p className="text-xs text-slate-500 dark:text-slate-400">{t('instructor.digestNoNewRisk')}</p>
          ) : (
            <div className="space-y-2 max-h-[26rem] overflow-y-auto pr-1">
              {newRiskCases.map((risk) => {
                const high = isHighRisk(risk.riskLevel);
                return (
                  <div key={risk.id} className="p-3 rounded-xl border border-line space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-black text-xs text-fg truncate">{risk.studentAlias}</span>
                      <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono-code shrink-0">
                        {formatDetectedAt(risk.generatedAt, lang)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-black font-mono-code uppercase ${
                        high ? 'bg-danger-soft text-danger-ink' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                      }`}>
                        {riskLevelLabel(t, risk.riskLevel)}
                      </span>
                      <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                        {riskTypeLabel(t, risk.riskType)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="card p-6 space-y-4">
          <h2 className="text-base font-black text-fg font-serif-heading flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-danger-ink" /> {t('instructor.digestNewGuardrail')}
          </h2>
          {newGuardrailCases.length === 0 ? (
            <p className="text-xs text-slate-500 dark:text-slate-400">{t('instructor.digestNoNewGuardrail')}</p>
          ) : (
            <div className="space-y-2 max-h-[26rem] overflow-y-auto pr-1">
              {newGuardrailCases.map((item) => {
                const isExpanded = expandedGuardrailId === item.id;
                return (
                  <div key={item.id} className="p-3 bg-surface-elevated border border-line rounded-xl space-y-2">
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-black text-fg truncate">{item.studentAlias}</span>
                      <span className="text-slate-500 dark:text-slate-400 font-mono-code text-[10px] shrink-0">
                        {formatDetectedAt(item.createdAt, lang)}
                      </span>
                    </div>
                    <span className="inline-block px-2 py-0.5 rounded-md bg-danger-soft dark:bg-red-950/60 text-danger-ink dark:text-red-300 text-[10px] font-black font-mono-code uppercase">
                      {blockReasonLabel(t, item.blockReason)}
                    </span>
                    <button
                      type="button"
                      onClick={() => setExpandedGuardrailId(isExpanded ? null : item.id)}
                      className="text-[11px] font-black text-accent hover:text-accent-hover inline-flex items-center gap-1 cursor-pointer block"
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

      {kudos.length > 0 && (
        <div className="card p-5 space-y-3 border-l-4 border-l-success-ink">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-success-ink dark:text-emerald-400" />
            <h2 className="text-sm font-black text-fg font-serif-heading">
              {t('instructor.kudosTitle')}
            </h2>
          </div>
          <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
            {kudos.map((item) => (
              <span
                key={item.studentId}
                title={item.note}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-success-soft dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-700/60 text-xs font-bold text-emerald-900 dark:text-[#A7D4B0]"
              >
                <Award className="w-3.5 h-3.5 shrink-0" />
                {item.displayName}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
