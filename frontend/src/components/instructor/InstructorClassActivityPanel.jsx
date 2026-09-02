import React, { useEffect, useMemo, useState } from 'react';
import {
  Plus, ChevronLeft, ChevronRight, X, Trash2,
  CalendarRange, Info,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { GvStickyHeader, GvPager, usePaged } from './GvChrome';
import {
  createClassActivity, deleteClassActivity, getInstructorDashboard,
  listClassActivities, userFacingApiError,
} from '../../lib/api';
import ErrorState from '../shared/ErrorState';
import EmptyState from '../shared/EmptyState';

/**
 * Hoat dong lop — giao dien lay LICH lam trung tam.
 *
 * Bo cuc: lich tuan (~57%) | danh sach su kien (~21%) | bang phu tro (~22%).
 *
 * Ve phan loai: backend chi nhan 4 kind (ACTIVITY_KINDS trong
 * class_activity_repository.py): ASSIGNMENT / PROGRESS_TEST / LAB / OTHER.
 * Anh mau ve 5 nhan (them "Nhac nho"); dung 5 o day se tao ra mot loai ma
 * chinh API tu choi khi luu, nen giu dung 4 loai that va gan 4 mau rieng.
 *
 * Bang phu tro ben phai trong anh mau la "Day vao ke hoach sinh vien" kem
 * vong tron dong bo. Hoat dong lop da tu dong hien trong ke hoach sinh vien
 * (GET /student/class-activities) — khong co buoc dong bo nao de bat/tat,
 * nen cho do hien khung thoi gian hoc ky ma API that su tra ve.
 */

const DAY_START = 8;
const DAY_END = 17;
const HOUR_PX = 56;

const KINDS = [
  { value: 'ASSIGNMENT', labelKey: 'actKindAssignment', color: 'var(--gv-amber)', soft: 'var(--gv-amber-soft)' },
  { value: 'PROGRESS_TEST', labelKey: 'actKindProgressTest', color: '#7C3AED', soft: '#EDE9FE' },
  { value: 'LAB', labelKey: 'actKindLab', color: '#2563EB', soft: '#DBEAFE' },
  { value: 'OTHER', labelKey: 'actKindOther', color: '#EA580C', soft: '#FFEDD5' },
];

const kindOf = (value) => KINDS.find((k) => k.value === value) || KINDS[3];

/** Thu 2 cua tuan chua `date` (tuan bat dau tu Thu 2). */
function mondayOf(date) {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  const weekday = (copy.getDay() + 6) % 7;
  copy.setDate(copy.getDate() - weekday);
  return copy;
}

const iso = (date) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

const ddmm = (date) => `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}`;

/** So tuan trong nam theo chuan ISO — dung cho nhan "Tuan N". */
function isoWeekNumber(date) {
  const copy = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = copy.getUTCDay() || 7;
  copy.setUTCDate(copy.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(copy.getUTCFullYear(), 0, 1));
  return Math.ceil(((copy - yearStart) / 86400e3 + 1) / 7);
}

function hourFraction(isoString, fallback) {
  if (!isoString) return fallback;
  const at = new Date(isoString);
  if (Number.isNaN(at.getTime())) return fallback;
  return at.getHours() + at.getMinutes() / 60;
}

export default function InstructorClassActivityPanel() {
  const { t, lang } = useLanguage();

  const [weekStart, setWeekStart] = useState(() => mondayOf(new Date()));
  const [activities, setActivities] = useState([]);
  const [windowInfo, setWindowInfo] = useState(null);
  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('ALL');

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formError, setFormError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [notice, setNotice] = useState(null);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => {
      const day = new Date(weekStart);
      day.setDate(day.getDate() + i);
      return day;
    }),
    [weekStart]
  );

  const [form, setForm] = useState({
    kind: 'ASSIGNMENT', title: '', date: iso(new Date()),
    start: '14:00', end: '15:00', courseId: '',
  });

  const load = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [data, dashboard] = await Promise.all([
        listClassActivities({ start: iso(days[0]), end: iso(days[6]) }),
        getInstructorDashboard('ALL').catch(() => ({ courses: [] })),
      ]);
      setActivities(data.activities || []);
      setWindowInfo(data.window || null);
      setCourses(dashboard.courses || []);
      setForm((prev) => ({
        ...prev,
        courseId: prev.courseId || (dashboard.courses?.[0]?.id ?? ''),
      }));
    } catch (err) {
      setLoadError(userFacingApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weekStart]);

  const visible = useMemo(
    () => activities.filter((a) => selectedCourseId === 'ALL' || a.course_id === selectedCourseId),
    [activities, selectedCourseId]
  );

  const byDay = useMemo(() => {
    const map = new Map(days.map((day) => [iso(day), []]));
    visible.forEach((activity) => {
      const bucket = map.get(activity.activity_date);
      if (bucket) bucket.push(activity);
    });
    return map;
  }, [visible, days]);

  const upcoming = useMemo(
    () => [...visible].sort((a, b) => a.activity_date.localeCompare(b.activity_date)),
    [visible]
  );
  // Truoc day danh sach bi .slice(0, 5) — 5 su kien dau, phan con lai khong
  // co cach nao xem. Phan trang thay cho viec cat cung: khong con an du lieu.
  const upcomingPage = usePaged(upcoming, 5);

  const shiftWeek = (delta) => {
    const next = new Date(weekStart);
    next.setDate(next.getDate() + delta * 7);
    setWeekStart(next);
  };

  const submit = async (event) => {
    event.preventDefault();
    setIsSaving(true);
    setFormError(null);
    setNotice(null);
    try {
      await createClassActivity({
        course_id: form.courseId,
        activity_date: form.date,
        kind: form.kind,
        title: form.title,
        opens_at: `${form.date}T${form.start}:00`,
        closes_at: `${form.date}T${form.end}:00`,
      });
      setIsFormOpen(false);
      setForm((prev) => ({ ...prev, title: '' }));
      await load();
    } catch (err) {
      setFormError(userFacingApiError(err).message);
    } finally {
      setIsSaving(false);
    }
  };

  const remove = async (activityId) => {
    setNotice(null);
    try {
      await deleteClassActivity(activityId);
      setNotice({ tone: 'ok', text: t('instructor.actDeleted') });
      await load();
    } catch (err) {
      setNotice({ tone: 'error', text: userFacingApiError(err).message });
    }
  };

  const statusLabel = (status) => ({
    scheduled: t('instructor.actStatusScheduled'),
    open: t('instructor.actStatusOpen'),
    closed: t('instructor.actStatusClosed'),
  }[status] || status);

  if (isLoading) {
    return (
      <div className="gv-ui p-7 space-y-4 animate-pulse">
        <div className="gv-panel" style={{ height: 88 }} />
        <div className="grid grid-cols-1 xl:grid-cols-[57fr_21fr_22fr] gap-4">
          <div className="gv-panel" style={{ height: 520 }} />
          <div className="gv-panel" style={{ height: 520 }} />
          <div className="gv-panel" style={{ height: 520 }} />
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="gv-ui p-7">
        <ErrorState
          title={t('states.errorTitle')}
          description={loadError}
          onRetry={load}
          retryLabel={t('states.retryBtn')}
        />
      </div>
    );
  }

  const hours = Array.from({ length: DAY_END - DAY_START + 1 }, (_, i) => DAY_START + i);
  const todayIso = iso(new Date());

  return (
    <div className="gv-ui gv-page">
      <GvStickyHeader>
        <header className="gv-panel px-6 py-4 flex flex-wrap items-end gap-3">
          {/* .gv-title-inline: tieu de dung cung hang voi cac control, nen
              duoc boc trong khung cao bang control (40px) de chu can giua
              theo control thay vi tut xuong duoi nhan cua select. */}
          <h1 className="gv-page-title gv-title-inline mr-2" style={{ flex: '0 0 auto' }}>
            {t('instructor.actPageTitle')}
          </h1>

          <label style={{ width: 250 }}>
            <span className="gv-field-label">{t('instructor.dashClassField')}</span>
            <select className="gv-select" value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}>
              <option value="ALL">{t('instructor.allCourses')}</option>
              {courses.map((c) => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
            </select>
          </label>

          <div style={{ flex: '0 0 auto' }}>
            <span className="gv-field-label">{t('instructor.actWeek')}</span>
            <div className="flex items-center gap-2" style={{ minHeight: 'var(--gv-h-ctl)' }}>
              <button type="button" className="gv-btn gv-btn--ghost gv-ctl gv-ctl--icon"
                onClick={() => shiftWeek(-1)} aria-label={t('instructor.actPrevWeek')}>
                <ChevronLeft size={16} />
              </button>
              <span className="gv-body-sm" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                {t('instructor.actWeek')} {isoWeekNumber(days[0])} ({ddmm(days[0])} – {ddmm(days[6])}/{days[6].getFullYear()})
              </span>
              <button type="button" className="gv-btn gv-btn--ghost gv-ctl gv-ctl--icon"
                onClick={() => shiftWeek(1)} aria-label={t('instructor.actNextWeek')}>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <button type="button" className="gv-btn gv-btn--teal gv-ctl" style={{ marginLeft: 'auto' }}
            onClick={() => { setIsFormOpen(true); setFormError(null); }}>
            <Plus size={16} /> {t('instructor.actCreate')}
          </button>
        </header>
      </GvStickyHeader>

      <div className="gv-page__body">

        {notice && (
          <p className="gv-body-sm"
            style={{ color: notice.tone === 'ok' ? 'var(--gv-success)' : 'var(--gv-danger)' }}>
            {notice.text}
          </p>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[57fr_21fr_22fr] items-start" style={{ gap: 16 }}>

          {/* --- Lich tuan --- */}
          <section className="gv-panel p-5 min-w-0">
            <div style={{ overflowX: 'auto' }}>
              <div style={{ minWidth: 640 }}>
                <div className="grid" style={{ gridTemplateColumns: '52px repeat(7, 1fr)' }}>
                  <span />
                  {days.map((day) => (
                    <div key={iso(day)} className="text-center pb-2"
                      style={{
                        borderBottom: '1px solid var(--gv-border)',
                        background: iso(day) === todayIso ? 'var(--gv-teal-soft)' : undefined,
                        borderRadius: iso(day) === todayIso ? '8px 8px 0 0' : undefined,
                      }}>
                      <p className="gv-body-sm" style={{ fontWeight: 600 }}>
                        {new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-US', { weekday: 'short' })
                          .format(day)}
                      </p>
                      <p className="gv-meta">{ddmm(day)}</p>
                    </div>
                  ))}
                </div>

                <div className="grid" style={{ gridTemplateColumns: '52px repeat(7, 1fr)' }}>
                  <div>
                    {hours.map((hour) => (
                      <div key={hour} className="gv-meta" style={{ height: HOUR_PX, paddingTop: 2 }}>
                        {String(hour).padStart(2, '0')}:00
                      </div>
                    ))}
                  </div>

                  {days.map((day) => (
                    <div key={iso(day)} style={{ position: 'relative', borderLeft: '1px solid var(--gv-border)' }}>
                      {hours.map((hour) => (
                        <div key={hour} style={{ height: HOUR_PX, borderTop: '1px solid var(--gv-border)' }} />
                      ))}

                      {(byDay.get(iso(day)) || []).map((activity) => {
                        const kind = kindOf(activity.kind);
                        const from = hourFraction(activity.opens_at, DAY_START);
                        const to = hourFraction(activity.closes_at, from + 1);
                        const top = Math.max(0, (from - DAY_START)) * HOUR_PX;
                        const height = Math.max(34, (Math.max(to, from + 0.5) - from) * HOUR_PX - 4);
                        // So dong tieu de duoc phep = so dong THUC SU vua o
                        // trong o. Truoc day clamp cung 2 dong: mot su kien
                        // dai 1 tieng cho o cao 52px, ma 2 dong can 58px, nen
                        // dong thu hai bi overflow: hidden cat cut ngang.
                        const titleLines = Math.max(1, Math.min(3,
                          Math.floor((height - 10 - 16) / 16.3)));
                        return (
                          <div
                            key={activity.id}
                            title={`${activity.title} — ${activity.course_code || ''}`}
                            style={{
                              position: 'absolute', left: 3, right: 3, top: top + 1, height,
                              background: kind.soft, borderLeft: `3px solid ${kind.color}`,
                              borderRadius: 8, padding: '5px 7px', overflow: 'hidden',
                            }}
                          >
                            <p style={{ fontSize: 12.5, fontWeight: 600, color: kind.color, lineHeight: 1.25 }}>
                              {activity.opens_at
                                ? new Date(activity.opens_at).toTimeString().slice(0, 5) : ''}
                            </p>
                            <p style={{
                              fontSize: 12.5, lineHeight: 1.3, color: 'var(--gv-text)',
                              display: '-webkit-box', WebkitLineClamp: titleLines,
                              WebkitBoxOrient: 'vertical', overflow: 'hidden',
                            }}>
                              {activity.title || t(`instructor.${kind.labelKey}`)}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 mt-4 pt-4"
              style={{ borderTop: '1px solid var(--gv-border)' }}>
              {KINDS.map((kind) => (
                <span key={kind.value} className="flex items-center gap-2 gv-meta">
                  <span style={{ width: 10, height: 10, borderRadius: 999, background: kind.color }} />
                  {t(`instructor.${kind.labelKey}`)}
                </span>
              ))}
            </div>
          </section>

          {/* --- Danh sach su kien --- */}
          <section className="gv-panel p-5 min-w-0">
            <h2 className="gv-section-title mb-4">{t('instructor.actEventList')}</h2>
            {upcoming.length === 0 ? (
              <EmptyState title={t('instructor.actNoEvent')} />
            ) : (
              <ul className="flex flex-col" style={{ gap: 12 }}>
                {upcomingPage.slice.map((activity) => {
                  const kind = kindOf(activity.kind);
                  const day = new Date(`${activity.activity_date}T00:00:00`);
                  return (
                    <li key={activity.id} className="gv-card p-3 flex items-start gap-3">
                      <span className="text-center shrink-0" style={{ width: 42 }}>
                        <span className="block gv-meta" style={{ textTransform: 'uppercase' }}>
                          {new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-US', { weekday: 'short' })
                            .format(day)}
                        </span>
                        <span className="block" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.1 }}>
                          {day.getDate()}
                        </span>
                        <span className="block gv-meta">{`T${day.getMonth() + 1}`}</span>
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2 flex-wrap">
                          <span className="gv-badge gv-badge--tight"
                            title={t(`instructor.${kind.labelKey}`)}
                            style={{ background: kind.soft, color: kind.color }}>
                            {t(`instructor.${kind.labelKey}`)}
                          </span>
                          <span className="gv-meta">{statusLabel(activity.status)}</span>
                        </span>
                        <span className="block gv-body-sm mt-1" style={{
                          fontWeight: 600,
                          display: '-webkit-box', WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical', overflow: 'hidden',
                        }}>
                          {activity.title || t(`instructor.${kind.labelKey}`)}
                        </span>
                        <span className="block gv-meta truncate">{activity.course_code}</span>
                      </span>
                      <button type="button" className="gv-btn gv-btn--ghost shrink-0"
                        style={{ padding: 7 }} onClick={() => remove(activity.id)}
                        aria-label={t('instructor.actDelete')}>
                        <Trash2 size={14} />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
            <GvPager {...upcomingPage} onChange={upcomingPage.setPage}
              label={t('instructor.actEventList')} />
          </section>

          {/* --- Bang phu tro --- */}
          <div className="flex flex-col min-w-0" style={{ gap: 16 }}>
            <section className="gv-panel p-5">
              <div className="flex items-center gap-2.5 mb-3">
                <CalendarRange size={18} style={{ color: 'var(--gv-teal)' }} />
                <h2 className="gv-card-title">{t('instructor.actWindowTitle')}</h2>
              </div>
              {windowInfo ? (
                <div className="flex flex-col" style={{ gap: 8 }}>
                  <div className="gv-stat">
                    <p className="gv-meta">{t('instructor.actWindowTerm')}</p>
                    <p className="gv-body-sm" style={{ fontWeight: 600 }}>{windowInfo.term_name}</p>
                  </div>
                  <div className="gv-stat">
                    <p className="gv-meta">{t('instructor.actWindowRange')}</p>
                    <p className="gv-body-sm" style={{ fontWeight: 600 }}>
                      {windowInfo.term_start} → {windowInfo.term_end}
                    </p>
                  </div>
                  <div className="gv-stat">
                    <p className="gv-meta">{t('instructor.actWindowLast')}</p>
                    <p className="gv-body-sm" style={{ fontWeight: 600 }}>{windowInfo.last_activity_date}</p>
                  </div>
                </div>
              ) : (
                <EmptyState title={t('instructor.actWindowNone')} />
              )}
              <p className="gv-meta mt-3 flex items-start gap-1.5">
                <Info size={13} className="mt-0.5 shrink-0" /> {t('instructor.actOnePerDay')}
              </p>
            </section>

            {isFormOpen && (
              <section className="gv-panel p-5">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <h2 className="gv-card-title">{t('instructor.actCreate')}</h2>
                  <button type="button" className="gv-btn gv-btn--ghost" style={{ padding: 7 }}
                    onClick={() => setIsFormOpen(false)} aria-label={t('instructor.actFormCancel')}>
                    <X size={14} />
                  </button>
                </div>

                <form onSubmit={submit} className="flex flex-col" style={{ gap: 10 }}>
                  <label>
                    <span className="gv-field-label">{t('instructor.actFormKind')}</span>
                    <select className="gv-select" value={form.kind}
                      onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                      {KINDS.map((kind) => (
                        <option key={kind.value} value={kind.value}>
                          {t(`instructor.${kind.labelKey}`)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label>
                    <span className="gv-field-label">{t('instructor.actFormTitle')}</span>
                    <input className="gv-select" style={{ cursor: 'text' }} value={form.title}
                      maxLength={160}
                      placeholder={t('instructor.actFormTitlePlaceholder')}
                      onChange={(e) => setForm({ ...form, title: e.target.value })} />
                  </label>

                  <label>
                    <span className="gv-field-label">{t('instructor.actFormDate')}</span>
                    <input type="date" className="gv-select" value={form.date}
                      onChange={(e) => setForm({ ...form, date: e.target.value })} />
                  </label>

                  <div className="grid grid-cols-2" style={{ gap: 10 }}>
                    <label>
                      <span className="gv-field-label">{t('instructor.actFormStart')}</span>
                      <input type="time" className="gv-select" value={form.start}
                        onChange={(e) => setForm({ ...form, start: e.target.value })} />
                    </label>
                    <label>
                      <span className="gv-field-label">{t('instructor.actFormEnd')}</span>
                      <input type="time" className="gv-select" value={form.end}
                        onChange={(e) => setForm({ ...form, end: e.target.value })} />
                    </label>
                  </div>

                  <label>
                    <span className="gv-field-label">{t('instructor.actFormClass')}</span>
                    <select className="gv-select" value={form.courseId}
                      onChange={(e) => setForm({ ...form, courseId: e.target.value })}>
                      {courses.map((c) => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
                    </select>
                  </label>

                  {formError && (
                    <p className="gv-body-sm" style={{ color: 'var(--gv-danger)' }}>{formError}</p>
                  )}

                  <div className="flex items-center gap-2">
                    <button type="button" className="gv-btn gv-btn--ghost flex-1"
                      onClick={() => setIsFormOpen(false)}>
                      {t('instructor.actFormCancel')}
                    </button>
                    <button type="submit" className="gv-btn gv-btn--teal flex-1" disabled={isSaving}>
                      {t('instructor.actFormSubmit')}
                    </button>
                  </div>
                </form>
              </section>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
