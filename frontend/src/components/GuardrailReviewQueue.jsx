import React, { useEffect, useMemo, useState } from 'react';
import {
  ShieldAlert, ShieldCheck, ShieldOff, AlertTriangle, RefreshCw, X, Info,
  MessageSquare, Lightbulb, UserCircle2, ChevronRight,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { getGuardrailReviewQueue, resolveGuardrailReview, userFacingApiError } from '../lib/api';
import { formatDetectedAt } from '../lib/riskLabels';
import { GvStickyHeader, GvPager, usePaged } from './instructor/GvChrome';

/** Ly do chan da biet tu src/services/core/guardrail_service.py. */
const KNOWN_BLOCK_REASONS = ['academic_integrity'];

function blockReasonLabel(t, reason) {
  if (!reason) return null;
  return KNOWN_BLOCK_REASONS.includes(reason) ? t(`guardrail.reason_${reason}`) : reason;
}

/**
 * Xet duyet Guardrail — man review & decision, nghiem tuc hon cac man khac.
 *
 * Nguyen tac bao mat giu nguyen tu ban cu: nguyen van cau hoi cua sinh vien
 * CHI hien sau khi giang vien chu dong mo case, khong bao gio hien tren
 * hang doi hay dashboard. Hang doi chi mang ten, lop, nhan phan loai va
 * thoi diem.
 *
 * Drawer co dung 5 muc theo spec. Muc 3 chi neu ten quy tac khop va dien
 * giai co dinh cua chinh sach — API cho giang vien khong tra ve diem tin cay
 * (`/admin/guardrail-rules` la endpoint cua admin), nen khong bia mot con so
 * "do tin cay" nhu trong anh mau.
 */
export default function GuardrailReviewQueue() {
  const { t, lang } = useLanguage();

  const [reviews, setReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [openId, setOpenId] = useState(null);
  const [decision, setDecision] = useState(null);
  const [note, setNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const load = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      setReviews(await getGuardrailReviewQueue() || []);
    } catch (err) {
      setLoadError(userFacingApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const pending = useMemo(
    () => reviews.filter((row) => (row.reviewStatus || 'PENDING') === 'PENDING'),
    [reviews]
  );
  const handled = useMemo(
    () => reviews.filter((row) => (row.reviewStatus || 'PENDING') !== 'PENDING'),
    [reviews]
  );
  const openCase = reviews.find((row) => row.id === openId) || null;

  // Hai hang doi phan trang doc lap: cot trai thuong dai hon cot phai, ep
  // chung dung mot trang se lam cot ngan nhay trang vo nghia.
  const pendingPage = usePaged(pending, 5);
  const handledPage = usePaged(handled, 5);

  const closeDrawer = () => {
    setOpenId(null);
    setDecision(null);
    setNote('');
    setSaveError(null);
  };

  const save = async () => {
    if (!decision) return;
    if (decision === 'UNBLOCK' && !note.trim()) {
      setSaveError(t('guardrail.noteMissing'));
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    try {
      await resolveGuardrailReview(openCase.id, decision, note.trim() || null);
      closeDrawer();
      await load();
    } catch (err) {
      setSaveError(userFacingApiError(err).message);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="gv-ui p-7 space-y-4 animate-pulse">
        <div className="gv-panel" style={{ height: 92 }} />
        <div className="gv-panel" style={{ height: 360 }} />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="gv-ui p-7">
        <div className="gv-panel p-8 text-center max-w-lg mx-auto space-y-4">
          <AlertTriangle size={40} style={{ color: 'var(--gv-danger)' }} className="mx-auto" />
          <h2 className="gv-section-title">{t('states.errorTitle')}</h2>
          <p className="gv-body-sm gv-muted">{loadError}</p>
          <button type="button" className="gv-btn gv-btn--teal mx-auto" onClick={load}>
            <RefreshCw size={16} /> {t('states.retryBtn')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="gv-ui gv-page">
      <GvStickyHeader>
        <header className="gv-panel px-6 py-5 flex flex-col xl:flex-row xl:items-end gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="gv-page-title">{t('guardrail.pageTitle')}</h1>
              <span className="gv-badge gv-badge--amber">
                {pending.length} {t('guardrail.pendingBadge')}
              </span>
            </div>
            <p className="gv-body-sm gv-muted mt-1.5">{t('guardrail.pageSubtitle')}</p>
          </div>
          <button type="button" className="gv-btn gv-btn--ghost gv-ctl shrink-0" onClick={load}>
            <RefreshCw size={16} /> {t('guardrail.refreshBtn')}
          </button>
        </header>
      </GvStickyHeader>

      <div className="gv-page__body">

        {/* Chia doi giong man Rui ro: cho xem xet | da xu ly */}
        <div className="grid grid-cols-1 xl:grid-cols-2 items-start" style={{ gap: 16 }}>
          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center gap-2.5 mb-4">
              <ShieldAlert size={19} style={{ color: 'var(--gv-danger)' }} />
              <h2 className="gv-section-title">{t('guardrail.queueTitle')}</h2>
              <span className="gv-badge gv-badge--amber">{pending.length}</span>
            </div>

            {pending.length === 0 ? (
              <p className="gv-body-sm gv-muted py-8 text-center">{t('guardrail.noPending')}</p>
            ) : (
              <ul className="flex flex-col" style={{ gap: 12 }}>
                {pendingPage.slice.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={`gv-case ${openId === item.id ? 'gv-case--selected' : ''}`}
                      onClick={() => { closeDrawer(); setOpenId(item.id); }}
                    >
                      <div className="flex items-start justify-between gap-3 w-full">
                        <span className="flex items-center gap-2.5 min-w-0">
                          <UserCircle2 size={28} style={{ color: 'var(--gv-text-2)', flex: '0 0 auto' }} />
                          <span className="min-w-0">
                            <span className="block gv-card-title truncate">{item.studentAlias}</span>
                            <span className="block gv-meta truncate">
                              {blockReasonLabel(t, item.blockReason)}
                            </span>
                          </span>
                        </span>
                        <span className="gv-meta shrink-0">{formatDetectedAt(item.createdAt, lang)}</span>
                      </div>
                      {/* Khong hien nguyen van cau hoi o hang doi. */}
                      <span className="gv-link">
                        {t('guardrail.openCase')} <ChevronRight size={15} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <GvPager {...pendingPage} onChange={pendingPage.setPage}
              label={t('guardrail.queueTitle')} />
          </section>

          <section className="gv-panel p-6 min-w-0">
            <div className="flex items-center gap-2.5 mb-4">
              <ShieldCheck size={19} style={{ color: 'var(--gv-teal)' }} />
              <h2 className="gv-section-title">{t('guardrail.recentTitle')}</h2>
              <span className="gv-badge gv-badge--neutral">{handled.length}</span>
            </div>
            {handled.length === 0 ? (
              <p className="gv-body-sm gv-muted py-8 text-center">{t('guardrail.noRecent')}</p>
            ) : (
              <ul className="flex flex-col" style={{ gap: 12 }}>
                {handledPage.slice.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={`gv-case gv-case--done ${openId === item.id ? 'gv-case--selected' : ''}`}
                      onClick={() => { closeDrawer(); setOpenId(item.id); }}
                    >
                      <div className="flex items-start justify-between gap-3 w-full">
                        <span className="flex items-center gap-2.5 min-w-0">
                          <UserCircle2 size={28} style={{ color: 'var(--gv-text-2)', flex: '0 0 auto' }} />
                          <span className="min-w-0">
                            <span className="block gv-card-title truncate">{item.studentAlias}</span>
                            <span className="block gv-meta truncate">
                              {blockReasonLabel(t, item.blockReason)}
                            </span>
                          </span>
                        </span>
                        <span className="gv-meta shrink-0">{formatDetectedAt(item.createdAt, lang)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-2 w-full">
                        <span className={`gv-badge gv-badge--${item.reviewStatus === 'UNBLOCKED' ? 'teal' : 'danger'}`}>
                          {item.reviewStatus === 'UNBLOCKED'
                            ? t('guardrail.unblockedState') : t('guardrail.keptState')}
                        </span>
                        <span className="gv-link">
                          {t('guardrail.openCase')} <ChevronRight size={15} />
                        </span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <GvPager {...handledPage} onChange={handledPage.setPage}
              label={t('guardrail.recentTitle')} />
          </section>
        </div>
      </div>

      {openCase && (
        <>
          <div className="gv-drawer__scrim" onClick={closeDrawer} aria-hidden="true" />
          <aside className="gv-drawer" role="dialog" aria-label={t('guardrail.pageTitle')}>
            <header className="gv-drawer__head flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="gv-section-title truncate">{openCase.studentAlias}</h2>
                <p className="gv-meta mt-1">
                  {blockReasonLabel(t, openCase.blockReason)} · {formatDetectedAt(openCase.createdAt, lang)}
                </p>
              </div>
              <button type="button" className="gv-btn gv-btn--ghost" style={{ padding: 8 }}
                onClick={closeDrawer} aria-label="Đóng">
                <X size={16} />
              </button>
            </header>

            <div className="gv-drawer__body flex flex-col" style={{ gap: 20 }}>
              {/* 1 */}
              <section>
                <p className="gv-sec-label">1. {t('guardrail.secQa')}</p>
                <p className="gv-body-sm" style={{ fontWeight: 600, color: 'var(--gv-teal-hover)' }}>
                  {t('guardrail.questionLabel')}
                </p>
                <p className="gv-quote mt-1.5">{openCase.question || '—'}</p>
                <p className="gv-body-sm mt-3" style={{ fontWeight: 600 }}>{t('guardrail.answerLabel')}</p>
                <p className="gv-stat mt-1.5 gv-body-sm">{openCase.blockedAnswer || '—'}</p>
              </section>

              {/* 2 */}
              <section>
                <p className="gv-sec-label">2. {t('guardrail.secReason')}</p>
                <p className="gv-body-sm flex items-start gap-2">
                  <ShieldOff size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--gv-danger)' }} />
                  {blockReasonLabel(t, openCase.blockReason)}
                </p>
              </section>

              {/* 3 */}
              <section>
                <p className="gv-sec-label">3. {t('guardrail.secPolicy')}</p>
                <div className="gv-stat">
                  <p className="gv-body-sm" style={{ fontWeight: 600 }}>
                    {blockReasonLabel(t, openCase.blockReason)}
                  </p>
                  <p className="gv-body-sm gv-muted mt-1">{t('guardrail.policyHint')}</p>
                </div>
              </section>

              {/* 4 */}
              <section>
                <p className="gv-sec-label">4. {t('guardrail.secSocratic')}</p>
                <div className="gv-note flex items-start gap-2.5">
                  <Lightbulb size={16} className="mt-0.5 shrink-0" style={{ color: 'var(--gv-amber)' }} />
                  <span>{openCase.blockedAnswer || '—'}</span>
                </div>
                <p className="gv-meta mt-2 flex items-start gap-1.5">
                  <Info size={13} className="mt-0.5 shrink-0" />
                  {t('guardrail.socraticHint')}
                </p>
              </section>

              {/* 5 */}
              <section>
                <p className="gv-sec-label">5. {t('guardrail.secDecision')}</p>
                {/* .gv-choice, khong phai .gv-btn: .gv-btn co white-space: nowrap
                    nen dong giai thich khong the xuong hang — the rong 269px
                    trong cot 178px va chu tran ra ngoai drawer. .gv-choice la
                    dang the co tieu de + dong mo ta, chu tu xuong hang.
                    aria-pressed thay cho class trang thai: day la mot cap nut
                    bat/tat, trinh doc man hinh can biet cai nao dang chon. */}
                <div className="grid grid-cols-1 sm:grid-cols-2 min-w-0" style={{ gap: 10 }}>
                  <button
                    type="button"
                    className="gv-choice gv-choice--keep"
                    aria-pressed={decision === 'KEEP'}
                    onClick={() => { setDecision('KEEP'); setSaveError(null); }}
                  >
                    <span className="gv-choice__title">
                      <ShieldOff size={15} className="shrink-0" aria-hidden="true" />
                      {t('guardrail.keepBtn')}
                    </span>
                    <span className="gv-choice__hint">{t('guardrail.keepHint')}</span>
                  </button>

                  <button
                    type="button"
                    className="gv-choice gv-choice--unblock"
                    aria-pressed={decision === 'UNBLOCK'}
                    onClick={() => { setDecision('UNBLOCK'); setSaveError(null); }}
                  >
                    <span className="gv-choice__title">
                      <ShieldCheck size={15} className="shrink-0" aria-hidden="true" />
                      {t('guardrail.unblockBtn')}
                    </span>
                    <span className="gv-choice__hint">{t('guardrail.unblockHint')}</span>
                  </button>
                </div>

                <label className="block mt-3">
                  <span className="gv-field-label">
                    {t('guardrail.noteLabel')}
                    {decision === 'UNBLOCK' && ` (${t('guardrail.noteRequired')})`}
                  </span>
                  <textarea
                    className="gv-textarea" rows={3} maxLength={500}
                    value={note} onChange={(event) => setNote(event.target.value)}
                    placeholder={t('guardrail.notePlaceholder')}
                  />
                  <span className="gv-meta block text-right mt-1">{note.length}/500</span>
                </label>

                <p className="gv-meta flex items-start gap-1.5">
                  <Info size={13} className="mt-0.5 shrink-0" /> {t('guardrail.humanDecides')}
                </p>
              </section>
            </div>

            <footer className="gv-drawer__foot">
              {saveError && <p className="gv-body-sm" style={{ color: 'var(--gv-danger)' }}>{saveError}</p>}
              <button
                type="button" className="gv-btn gv-btn--teal w-full"
                disabled={!decision || isSaving} onClick={save}
              >
                <MessageSquare size={16} />
                {isSaving ? t('guardrail.sending') : t('guardrail.saveDecision')}
              </button>
              <p className="gv-meta">{t('guardrail.auditNote')}</p>
            </footer>
          </aside>
        </>
      )}
    </div>
  );
}
