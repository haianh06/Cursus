import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import {
  Calendar, ChevronLeft, ChevronRight, Loader2, Play, Plus, Sparkles, X, Repeat,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  bootstrapTimetable,
  createTimetableBlock,
  deleteTimetableBlock,
  getTimetable,
  startOfMonday,
  toDateInputValue,
  updateTimetableBlock,
} from '../../lib/api';

/**
 * Google-Calendar-style timetable: real class/exam schedule (locked, from
 * TimetableService._class_blocks/_exam_blocks) overlaid with the student's
 * own draggable/resizable self-study blocks (ScheduleBlock rows), in Day /
 * Week / Month views. Recurrence ("repeat weekly until") shares a
 * recurrenceSeriesId (src/services/timetable_service.py) so edit/delete can
 * be scoped to just this occurrence or the whole series.
 */

const DAY_LABELS_VI = ['Th 2', 'Th 3', 'Th 4', 'Th 5', 'Th 6', 'Th 7', 'CN'];
const DAY_LABELS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTH_LABELS_VI = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'];
const MONTH_LABELS_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const HOUR_FLOOR = 6;
const HOUR_CEIL = 22;
const PX_PER_HOUR = 48;
const SNAP_MINUTES = 15;
const EDGE_MS = 450;

function addDays(date, days) {
  const value = new Date(date);
  value.setDate(value.getDate() + days);
  return value;
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

/** 6x7 grid start — the Monday on/before the 1st of the month. */
function monthGridStart(date) {
  const first = startOfMonth(date);
  const dow = (first.getDay() + 6) % 7; // 0=Mon
  return addDays(first, -dow);
}

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** Local wall-clock parse — backend sends naive local ISO strings (see
 * wall_clock_iso in src/academic/slots.py), never UTC/`Z`-suffixed. */
function parseLocal(iso) {
  if (!iso) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(iso);
  if (!match) return null;
  const [, y, mo, d, h, mi] = match.map(Number);
  return new Date(y, mo - 1, d, h, mi, 0, 0);
}

function toIsoLocal(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}

function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const MODAL_PANEL_WIDTH = 320;
const MODAL_PANEL_EST_HEIGHT = 420;
const MODAL_PANEL_MARGIN = 12;
// The app's topbar (App.jsx, `h-14`) is a fixed 56px header sitting above
// this fixed-position popup — clamping the popup's top edge to the same
// 12px margin used elsewhere let it render partly hidden underneath that
// header when the clicked block was near the top of the viewport.
const MODAL_PANEL_TOP_SAFE = 64;

/**
 * Anchors the create/edit popup next to the calendar cell/block the student
 * just clicked instead of dead-centering it on the whole page — a modal
 * taller than the viewport used to center-overflow both above and below
 * the fold with no way to see or scroll to the clipped part (found via a
 * live user report). `estimatedHeight` is a best-effort guess (no
 * measured-DOM pass), so the panel also caps its own max-height + scrolls
 * internally as a safety net regardless of anchoring.
 */
function modalPanelStyle(anchorPos) {
  const base = {
    width: MODAL_PANEL_WIDTH,
    maxHeight: `calc(100vh - ${MODAL_PANEL_TOP_SAFE + MODAL_PANEL_MARGIN}px)`,
  };
  if (typeof window === 'undefined' || !anchorPos) {
    return { ...base, left: '50%', top: '50%', transform: 'translate(-50%, -50%)' };
  }
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const left = Math.min(
    Math.max(anchorPos.x - MODAL_PANEL_WIDTH / 2, MODAL_PANEL_MARGIN),
    Math.max(vw - MODAL_PANEL_WIDTH - MODAL_PANEL_MARGIN, MODAL_PANEL_MARGIN),
  );
  const spaceBelow = vh - anchorPos.y;
  const spaceAbove = anchorPos.y - MODAL_PANEL_TOP_SAFE;
  const opensBelow = spaceBelow >= MODAL_PANEL_EST_HEIGHT + MODAL_PANEL_MARGIN || spaceBelow >= spaceAbove;
  const top = opensBelow
    ? Math.min(anchorPos.y + MODAL_PANEL_MARGIN, Math.max(vh - MODAL_PANEL_MARGIN, MODAL_PANEL_TOP_SAFE))
    : Math.max(anchorPos.y - MODAL_PANEL_EST_HEIGHT - MODAL_PANEL_MARGIN, MODAL_PANEL_TOP_SAFE);
  return { ...base, left, top };
}

function snapDate(date) {
  const next = new Date(date);
  const snapped = Math.round(next.getMinutes() / SNAP_MINUTES) * SNAP_MINUTES;
  next.setMinutes(snapped % 60, 0, 0);
  if (snapped === 60) next.setHours(next.getHours() + 1);
  return next;
}

function minutesFromTop(date, hourStart) {
  return (date.getHours() - hourStart) * 60 + date.getMinutes();
}

function dateFromOffsetY(day, offsetY, hourStart, hourEnd) {
  const rel = Math.max(0, offsetY);
  const totalMinutes = Math.round(rel / (PX_PER_HOUR / 60) / SNAP_MINUTES) * SNAP_MINUTES;
  const hours = hourStart + Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const next = new Date(day);
  next.setHours(Math.min(hourEnd - 1, Math.max(hourStart, hours)), minutes, 0, 0);
  return snapDate(next);
}

function formatDuration(start, end) {
  const mins = Math.max(0, Math.round((end - start) / 60000));
  if (mins < 60) return `${mins}p`;
  const hours = Math.floor(mins / 60);
  const rest = mins % 60;
  return rest ? `${hours}h${String(rest).padStart(2, '0')}` : `${hours}h`;
}

function blockTone(block) {
  const kind = String(block.kind || '').toUpperCase();
  const isExam = kind === 'EXAM_PE' || kind === 'EXAM_FE' || kind === 'EXAM';
  const isActivity = kind === 'CLASS_ACTIVITY';
  const isClass = kind === 'CLASS' || (block.locked && !isExam && !isActivity);
  if (isExam) {
    return { bar: 'var(--danger)', className: 'bg-[var(--danger-soft)] border-[color:var(--danger)] text-[color:var(--danger)] cursor-default' };
  }
  if (isActivity || isClass) {
    return { bar: 'var(--accent)', className: 'bg-[var(--accent-soft)] border-[color:var(--accent)] text-fg cursor-default' };
  }
  return { bar: 'var(--success, #2F6B3A)', className: 'bg-[var(--success-soft,#E6EFE2)] border-[color:var(--success,#2F6B3A)] text-[color:var(--success,#2F6B3A)] cursor-grab active:cursor-grabbing' };
}

export default function Timetable({ initialView = 'week', initialAnchor = null, previewPlanId = null } = {}) {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const dayLabels = lang === 'vi' ? DAY_LABELS_VI : DAY_LABELS_EN;
  const monthLabels = lang === 'vi' ? MONTH_LABELS_VI : MONTH_LABELS_EN;

  const [view, setView] = useState(initialView); // 'day' | 'week' | 'month'
  const [anchor, setAnchor] = useState(() => initialAnchor || new Date());
  const [data, setData] = useState(null);
  const [monthData, setMonthData] = useState({}); // { 'YYYY-MM-DD-weekKey': payload }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [toast, setToast] = useState('');
  const [modal, setModal] = useState(null);
  const [scopePrompt, setScopePrompt] = useState(null);
  const [saving, setSaving] = useState(false);
  const dragRef = useRef(null);
  const edgeTimerRef = useRef(null);
  const gridRef = useRef(null);

  const weekStart = useMemo(() => startOfMonday(anchor), [anchor]);
  const weekKey = toDateInputValue(weekStart);
  const hourStart = HOUR_FLOOR;
  const hourEnd = HOUR_CEIL;
  const hours = useMemo(() => Array.from({ length: hourEnd - hourStart }, (_, i) => hourStart + i), []);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);
  const visibleDays = view === 'day' ? [anchor] : weekDays;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getTimetable(weekKey, { previewPlanId });
      setData(payload);
    } catch (err) {
      setError(err?.message || (lang === 'vi' ? 'Không tải được thời khoá biểu.' : 'Could not load the timetable.'));
    } finally {
      setLoading(false);
    }
  }, [weekKey, lang, previewPlanId]);

  useEffect(() => {
    if (view !== 'month') load();
  }, [load, view]);

  // Month view needs every week that touches the visible 6x7 grid.
  useEffect(() => {
    if (view !== 'month') return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const gridStart = monthGridStart(anchor);
    const weekKeys = Array.from({ length: 6 }, (_, i) => toDateInputValue(addDays(gridStart, i * 7)));
    Promise.all(weekKeys.map((key) => getTimetable(key).catch(() => null)))
      .then((results) => {
        if (cancelled) return;
        const next = {};
        weekKeys.forEach((key, i) => { next[key] = results[i]; });
        setMonthData(next);
      })
      .catch((err) => !cancelled && setError(err?.message || null))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [view, anchor]);

  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(() => setToast(''), 4000);
    return () => clearTimeout(id);
  }, [toast]);

  useEffect(() => {
    if (!modal && !scopePrompt) return undefined;
    const onKeyDown = (event) => {
      if (event.key !== 'Escape' || saving) return;
      setScopePrompt(null);
      setModal(null);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [modal, scopePrompt, saving]);

  const blocksByDay = useMemo(() => {
    const map = Object.fromEntries(visibleDays.map((day) => [toDateInputValue(day), []]));
    for (const block of data?.blocks || []) {
      const start = parseLocal(block.start);
      if (!start) continue;
      const key = toDateInputValue(start);
      if (!map[key]) continue;
      map[key].push({ ...block, _start: start, _end: parseLocal(block.end) });
    }
    Object.values(map).forEach((list) => list.sort((a, b) => a._start - b._start));
    return map;
  }, [data, visibleDays]);

  const monthCells = useMemo(() => {
    if (view !== 'month') return [];
    const gridStart = monthGridStart(anchor);
    const cells = [];
    for (let i = 0; i < 42; i += 1) {
      const day = addDays(gridStart, i);
      const weekKeyForDay = toDateInputValue(startOfMonday(day));
      const payload = monthData[weekKeyForDay];
      const dayKey = toDateInputValue(day);
      const blocks = (payload?.blocks || [])
        .map((b) => ({ ...b, _start: parseLocal(b.start), _end: parseLocal(b.end) }))
        .filter((b) => b._start && toDateInputValue(b._start) === dayKey)
        .sort((a, b) => a._start - b._start);
      cells.push({ day, blocks, inMonth: day.getMonth() === anchor.getMonth() });
    }
    return cells;
  }, [view, anchor, monthData]);

  const goToday = () => setAnchor(new Date());
  const goPrev = () => setAnchor((prev) => (view === 'month' ? addMonths(prev, -1) : addDays(prev, view === 'day' ? -1 : -7)));
  const goNext = () => setAnchor((prev) => (view === 'month' ? addMonths(prev, 1) : addDays(prev, view === 'day' ? 1 : 7)));

  function addMonths(date, n) {
    return new Date(date.getFullYear(), date.getMonth() + n, 1);
  }

  const openCreateModal = (start, anchorPos) => {
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    setModal({ mode: 'create', title: '', start: toLocalInputValue(start), end: toLocalInputValue(end), repeatUntil: '', block: null, anchorPos });
  };
  const openCreateAt = (day, offsetY, anchorPos) => openCreateModal(dateFromOffsetY(day, offsetY, hourStart, hourEnd), anchorPos);
  const openCreateAtHour = (day, hour, anchorPos) => {
    const start = new Date(day);
    start.setHours(hour, 0, 0, 0);
    openCreateModal(start, anchorPos);
  };
  const openCreateDefault = () => {
    const start = new Date(visibleDays[0] || anchor);
    start.setHours(19, 0, 0, 0);
    openCreateModal(start);
  };
  const openEdit = (block, anchorPos) => {
    setModal({ mode: 'edit', title: block.title || '', start: toLocalInputValue(block._start), end: toLocalInputValue(block._end), repeatUntil: '', block, anchorPos });
  };

  const handleBootstrap = async () => {
    setBootstrapping(true);
    setError(null);
    try {
      const payload = await bootstrapTimetable(weekKey);
      setData(payload);
    } catch (err) {
      setError(err?.message || null);
    } finally {
      setBootstrapping(false);
    }
  };

  const persistMove = async (block, start, end) => {
    try {
      if (block.recurrenceSeriesId) {
        setScopePrompt({ type: 'update', block, start, end, title: block.title });
        await load();
        return;
      }
      await updateTimetableBlock(block.id, { start: toIsoLocal(start), end: toIsoLocal(end), recurrenceScope: 'this' });
      await load();
    } catch (err) {
      setError(err?.message || null);
      await load();
    }
  };

  const onPointerDownBlock = (event, block, mode) => {
    if (block.locked) return;
    event.preventDefault();
    event.stopPropagation();
    const start = block._start;
    const end = block._end;
    dragRef.current = {
      mode, block, originY: event.clientY, originX: event.clientX, start, end,
      dayIndex: visibleDays.findIndex((d) => toDateInputValue(d) === toDateInputValue(start)),
      moved: false,
    };

    const onMove = (ev) => {
      const state = dragRef.current;
      if (!state) return;
      state.moved = true;
      const dy = ev.clientY - state.originY;
      const deltaMin = Math.round(dy / (PX_PER_HOUR / 60) / SNAP_MINUTES) * SNAP_MINUTES;
      let nextStart = new Date(state.start);
      let nextEnd = new Date(state.end);
      if (state.mode === 'move') {
        nextStart = new Date(state.start.getTime() + deltaMin * 60000);
        nextEnd = new Date(state.end.getTime() + deltaMin * 60000);
        if (view === 'week') {
          const col = document.elementFromPoint(ev.clientX, ev.clientY)?.closest('[data-day-index]');
          if (col) {
            const idx = Number(col.getAttribute('data-day-index'));
            if (!Number.isNaN(idx) && idx !== state.dayIndex) {
              const dayDelta = idx - state.dayIndex;
              nextStart = addDays(nextStart, dayDelta);
              nextEnd = addDays(nextEnd, dayDelta);
              state.dayIndex = idx;
              state.start = addDays(state.start, dayDelta);
              state.end = addDays(state.end, dayDelta);
            }
          }
          const grid = gridRef.current?.getBoundingClientRect();
          if (grid) {
            const nearLeft = ev.clientX < grid.left + 24;
            const nearRight = ev.clientX > grid.right - 24;
            if (nearLeft || nearRight) {
              if (!edgeTimerRef.current) {
                edgeTimerRef.current = setTimeout(() => {
                  const shift = nearLeft ? -7 : 7;
                  setAnchor((prev) => addDays(prev, shift));
                  state.start = addDays(state.start, shift);
                  state.end = addDays(state.end, shift);
                  nextStart = addDays(nextStart, shift);
                  nextEnd = addDays(nextEnd, shift);
                  edgeTimerRef.current = null;
                }, EDGE_MS);
              }
            } else if (edgeTimerRef.current) {
              clearTimeout(edgeTimerRef.current);
              edgeTimerRef.current = null;
            }
          }
        }
      } else if (state.mode === 'resize-top') {
        nextStart = snapDate(new Date(state.start.getTime() + deltaMin * 60000));
        if (nextEnd - nextStart < 15 * 60000) nextStart = new Date(nextEnd.getTime() - 15 * 60000);
      } else if (state.mode === 'resize-bottom') {
        nextEnd = snapDate(new Date(state.end.getTime() + deltaMin * 60000));
        if (nextEnd - nextStart < 15 * 60000) nextEnd = new Date(nextStart.getTime() + 15 * 60000);
      }
      state.previewStart = snapDate(nextStart);
      state.previewEnd = snapDate(nextEnd);
      setData((prev) => (!prev ? prev : {
        ...prev,
        blocks: prev.blocks.map((b) => (b.id === state.block.id
          ? { ...b, start: toIsoLocal(state.previewStart), end: toIsoLocal(state.previewEnd) }
          : b)),
      }));
    };

    const onUp = async () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      if (edgeTimerRef.current) { clearTimeout(edgeTimerRef.current); edgeTimerRef.current = null; }
      const state = dragRef.current;
      dragRef.current = null;
      if (!state) return;
      if (!state.moved) { openEdit(block, { x: state.originX, y: state.originY }); return; }
      const startAt = state.previewStart || state.start;
      const endAt = state.previewEnd || state.end;
      if (state.block.recurrenceSeriesId) {
        setScopePrompt({ type: 'update', block: state.block, start: startAt, end: endAt, title: state.block.title });
        return;
      }
      await persistMove(state.block, startAt, endAt);
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const submitModal = async () => {
    if (!modal) return;
    setSaving(true);
    setError(null);
    try {
      const start = new Date(modal.start);
      const end = new Date(modal.end);
      if (!(start instanceof Date) || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) {
        setError(lang === 'vi' ? 'Khoảng thời gian không hợp lệ.' : 'Invalid time range.');
        setSaving(false);
        return;
      }
      const title = modal.title.trim() || (lang === 'vi' ? 'Tự học' : 'Self-study');
      if (modal.mode === 'create') {
        await createTimetableBlock({ title, start: toIsoLocal(start), end: toIsoLocal(end), repeatWeeklyUntil: modal.repeatUntil || null });
        setModal(null);
        setAnchor(start);
        await load();
      } else if (modal.block?.recurrenceSeriesId) {
        setScopePrompt({ type: 'update', block: modal.block, start, end, title });
        setModal(null);
      } else {
        await updateTimetableBlock(modal.block.id, { title, start: toIsoLocal(start), end: toIsoLocal(end), recurrenceScope: 'this' });
        setModal(null);
        await load();
      }
    } catch (err) {
      setError(err?.message || null);
    } finally {
      setSaving(false);
    }
  };

  const requestDelete = () => {
    if (!modal?.block) return;
    if (modal.block.recurrenceSeriesId) {
      setScopePrompt({ type: 'delete', block: modal.block });
      setModal(null);
      return;
    }
    if (!window.confirm(lang === 'vi' ? 'Xoá mục này?' : 'Delete this item?')) return;
    (async () => {
      setSaving(true);
      try {
        await deleteTimetableBlock(modal.block.id, 'this');
        setModal(null);
        await load();
      } catch (err) {
        setError(err?.message || null);
      } finally {
        setSaving(false);
      }
    })();
  };

  const applyScope = async (scope) => {
    if (!scopePrompt) return;
    setSaving(true);
    try {
      if (scopePrompt.type === 'delete') {
        await deleteTimetableBlock(scopePrompt.block.id, scope);
      } else {
        await updateTimetableBlock(scopePrompt.block.id, {
          title: scopePrompt.title, start: toIsoLocal(scopePrompt.start), end: toIsoLocal(scopePrompt.end), recurrenceScope: scope,
        });
      }
      setScopePrompt(null);
      await load();
    } catch (err) {
      setError(err?.message || null);
    } finally {
      setSaving(false);
    }
  };

  const gridHeight = (hourEnd - hourStart) * PX_PER_HOUR;
  const rangeLabel = view === 'month'
    ? `${monthLabels[anchor.getMonth()]} ${anchor.getFullYear()}`
    : view === 'day'
      ? `${dayLabels[(anchor.getDay() + 6) % 7]} ${anchor.getDate()}/${anchor.getMonth() + 1}`
      : `${toDateInputValue(weekStart)} → ${toDateInputValue(addDays(weekStart, 6))}`;

  return (
    <div className="card p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Calendar size={15} className="text-accent" />
          <h3 className="text-[13px] font-bold text-fg uppercase tracking-wider">
            {lang === 'vi' ? 'Thời khoá biểu' : 'Timetable'}
          </h3>
          {loading && <Loader2 size={13} className="animate-spin text-fg-muted" />}
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <div className="flex items-center rounded-lg border border-line overflow-hidden">
            {['day', 'week', 'month'].map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setView(mode)}
                className={`px-2.5 py-1 text-[11px] font-bold cursor-pointer transition-colors ${view === mode ? 'bg-accent-cta text-white' : 'bg-surface-elevated text-fg-secondary hover:text-fg'}`}
              >
                {mode === 'day' ? (lang === 'vi' ? 'Ngày' : 'Day') : mode === 'week' ? (lang === 'vi' ? 'Tuần' : 'Week') : (lang === 'vi' ? 'Tháng' : 'Month')}
              </button>
            ))}
          </div>
          <button type="button" onClick={goPrev} className="p-1.5 rounded-lg border border-line text-fg-muted hover:bg-surface-elevated cursor-pointer" aria-label="prev">
            <ChevronLeft size={14} />
          </button>
          <span className="text-[11px] font-semibold text-fg-muted min-w-[9.5rem] text-center font-mono">{rangeLabel}</span>
          <button type="button" onClick={goNext} className="p-1.5 rounded-lg border border-line text-fg-muted hover:bg-surface-elevated cursor-pointer" aria-label="next">
            <ChevronRight size={14} />
          </button>
          <button type="button" onClick={goToday} className="px-2 py-1 text-[10px] font-bold rounded-lg border border-line text-accent cursor-pointer">
            {lang === 'vi' ? 'Hôm nay' : 'Today'}
          </button>
          <button
            type="button"
            onClick={openCreateDefault}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold rounded-lg text-white cursor-pointer bg-accent-cta"
          >
            <Plus size={12} />
            {lang === 'vi' ? 'Thêm tự học' : 'Add self-study'}
          </button>
        </div>
      </div>

      {toast && <div className="text-[11px] font-semibold px-3 py-2 rounded-lg bg-warning-soft text-warning">{toast}</div>}
      {error && <div className="text-[11px] font-bold px-3 py-2 rounded-lg bg-danger-soft text-danger">{error}</div>}

      {view === 'month' ? (
        <div className="rounded-lg border border-line overflow-hidden">
          <div className="grid grid-cols-7">
            {dayLabels.map((label) => (
              <div key={label} className="text-center py-1.5 text-[10px] font-black text-fg-muted bg-surface-elevated border-b border-line">{label}</div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {monthCells.map(({ day, blocks, inMonth }) => {
              const isToday = sameDay(day, new Date());
              return (
                <button
                  key={toDateInputValue(day)}
                  type="button"
                  onClick={() => { setAnchor(day); setView('day'); }}
                  className={`text-left border-b border-r border-line p-1.5 min-h-[84px] align-top cursor-pointer hover:bg-surface-elevated ${inMonth ? '' : 'opacity-40'}`}
                >
                  <span className={`text-[11px] font-bold ${isToday ? 'inline-flex items-center justify-center w-5 h-5 rounded-full text-white bg-accent-cta' : 'text-fg'}`}>
                    {day.getDate()}
                  </span>
                  <div className="mt-1 space-y-0.5">
                    {blocks.slice(0, 3).map((b) => (
                      <div key={b.id} className="truncate text-[9px] font-semibold px-1 py-0.5 rounded" style={{ background: blockTone(b).bar, color: '#fff', opacity: 0.85 }}>
                        {b.title}
                      </div>
                    ))}
                    {blocks.length > 3 && (
                      <div className="text-[9px] text-fg-muted">+{blocks.length - 3} {lang === 'vi' ? 'khác' : 'more'}</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <>
          {data?.isEmpty && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-dashed border-line px-3 py-2.5">
              <p className="text-[11px] font-semibold text-fg-muted">
                {lang === 'vi' ? 'Chưa có lịch nào trong tuần này.' : 'Nothing scheduled this week yet.'}
              </p>
              <button
                type="button"
                onClick={handleBootstrap}
                disabled={bootstrapping}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-cta disabled:opacity-50 text-white text-[11px] font-bold cursor-pointer"
              >
                {bootstrapping ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                {lang === 'vi' ? 'Tải lịch mẫu' : 'Load demo schedule'}
              </button>
            </div>
          )}

          <div ref={gridRef} className="overflow-x-auto rounded-lg border border-line">
            <div
              className="grid gap-px w-full"
              style={{ minWidth: view === 'day' ? '260px' : '630px', gridTemplateColumns: `52px repeat(${visibleDays.length}, minmax(0,1fr))` }}
            >
              <div className="sticky top-0 z-[4] bg-surface" />
              {visibleDays.map((day, index) => (
                <div key={`h-${index}`} className="sticky top-0 z-[4] text-center py-1 bg-surface">
                  <div className="text-[10px] font-black text-fg">{dayLabels[(day.getDay() + 6) % 7]}</div>
                  <div className="text-[10px] text-fg-muted font-mono">{day.getDate()}/{day.getMonth() + 1}</div>
                </div>
              ))}

              <div className="relative" style={{ height: gridHeight }}>
                {hours.map((hour) => (
                  <div key={hour} className="absolute left-0 right-0 text-[9px] text-fg-muted font-mono pr-1 text-right" style={{ top: (hour - hourStart) * PX_PER_HOUR - 6 }}>
                    {String(hour).padStart(2, '0')}:00
                  </div>
                ))}
              </div>

              {visibleDays.map((day, dayIndex) => {
                const key = toDateInputValue(day);
                const blocks = blocksByDay[key] || [];
                return (
                  <div
                    key={key}
                    data-day-index={dayIndex}
                    className="relative border-l border-line bg-surface"
                    style={{ height: gridHeight }}
                    onClick={(e) => { if (e.target === e.currentTarget) openCreateAt(day, e.nativeEvent.offsetY, { x: e.clientX, y: e.clientY }); }}
                  >
                    {hours.map((hour) => (
                      <button
                        key={hour}
                        type="button"
                        className="absolute left-0 right-0 border-t border-dashed border-line hover:bg-accent-soft"
                        style={{ top: (hour - hourStart) * PX_PER_HOUR, height: PX_PER_HOUR }}
                        aria-label={`${dayLabels[(day.getDay() + 6) % 7]} ${hour}:00`}
                        onClick={(event) => { event.stopPropagation(); openCreateAtHour(day, hour, { x: event.clientX, y: event.clientY }); }}
                      />
                    ))}
                    {blocks.map((block) => {
                      if (!block._start || !block._end) return null;
                      const top = Math.max(0, minutesFromTop(block._start, hourStart) * (PX_PER_HOUR / 60));
                      const height = Math.max(20, ((block._end - block._start) / 60000) * (PX_PER_HOUR / 60));
                      const tone = blockTone(block);
                      const showTime = height >= 30;
                      const showCourse = height >= 46 && block.courseCode;
                      return (
                        <div
                          key={block.id}
                          className={`absolute left-0.5 right-0.5 rounded-md border overflow-hidden select-none px-1.5 py-1 ${tone.className} ${block.isDraft ? 'border-dashed opacity-80' : ''}`}
                          style={{ top, height, zIndex: 3 }}
                          title={block.description || block.title}
                          onPointerDown={(e) => !block.locked && onPointerDownBlock(e, block, 'move')}
                        >
                          {!block.locked && (
                            <div
                              className="absolute left-0 right-0 top-0 h-1.5 cursor-n-resize z-[1]"
                              onPointerDown={(e) => onPointerDownBlock(e, block, 'resize-top')}
                            />
                          )}
                          <div className="text-[10px] font-bold truncate leading-tight flex items-center gap-1">
                            {block.recurrenceSeriesId && <Repeat size={9} className="shrink-0" />}
                            {block.isDraft && (
                              <span className="badge text-[8px] px-1 py-0 bg-surface-elevated border border-current shrink-0">
                                {lang === 'vi' ? 'Nháp' : 'Draft'}
                              </span>
                            )}
                            {block.title}
                          </div>
                          {showCourse && <div className="text-[9px] font-mono opacity-80 truncate">{block.courseCode}</div>}
                          {showTime && <div className="text-[9px] font-mono opacity-70">{formatDuration(block._start, block._end)}</div>}
                          {!block.locked && (
                            <div
                              className="absolute left-0 right-0 bottom-0 h-1.5 cursor-s-resize z-[1]"
                              onPointerDown={(e) => onPointerDownBlock(e, block, 'resize-bottom')}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {modal && (
        <div className="fixed inset-0 z-50 bg-black/40" onClick={() => !saving && setModal(null)}>
          <div
            className="card p-5 space-y-3 absolute overflow-y-auto"
            style={modalPanelStyle(modal.anchorPos)}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h4 className="text-[13px] font-bold text-fg">
                {modal.mode === 'create' ? (lang === 'vi' ? 'Thêm buổi tự học' : 'Add self-study') : (lang === 'vi' ? 'Sửa buổi tự học' : 'Edit self-study')}
              </h4>
              <button type="button" onClick={() => setModal(null)} className="text-fg-muted cursor-pointer"><X size={16} /></button>
            </div>
            {modal.mode === 'edit' && (
              <button
                type="button"
                onClick={() => navigate(`/student/self-study/${modal.block.id}`)}
                className="btn btn-accent w-full text-[12px] py-2 rounded-lg cursor-pointer flex items-center justify-center gap-1.5"
              >
                <Play size={13} /> {lang === 'vi' ? 'Bắt đầu tự học (Pomodoro)' : 'Start studying (Pomodoro)'}
              </button>
            )}
            <div>
              <label className="block text-[11px] font-semibold mb-1 text-fg-secondary">{lang === 'vi' ? 'Tiêu đề' : 'Title'}</label>
              <input className="input text-[13px] h-9" value={modal.title} onChange={(e) => setModal((m) => ({ ...m, title: e.target.value }))} placeholder={lang === 'vi' ? 'Tự học' : 'Self-study'} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold mb-1 text-fg-secondary">{lang === 'vi' ? 'Bắt đầu' : 'Start'}</label>
                <input type="datetime-local" className="input text-[12px] h-9" value={modal.start} onChange={(e) => setModal((m) => ({ ...m, start: e.target.value }))} />
              </div>
              <div>
                <label className="block text-[11px] font-semibold mb-1 text-fg-secondary">{lang === 'vi' ? 'Kết thúc' : 'End'}</label>
                <input type="datetime-local" className="input text-[12px] h-9" value={modal.end} onChange={(e) => setModal((m) => ({ ...m, end: e.target.value }))} />
              </div>
            </div>
            {modal.mode === 'create' && (
              <div>
                <label className="block text-[11px] font-semibold mb-1 text-fg-secondary flex items-center gap-1">
                  <Repeat size={11} /> {lang === 'vi' ? 'Lặp lại mỗi tuần đến (tuỳ chọn)' : 'Repeat weekly until (optional)'}
                </label>
                <input type="date" className="input text-[12px] h-9" value={modal.repeatUntil} onChange={(e) => setModal((m) => ({ ...m, repeatUntil: e.target.value }))} />
              </div>
            )}
            <div className="flex items-center justify-between pt-1">
              {modal.mode === 'edit' ? (
                <button type="button" onClick={requestDelete} disabled={saving} className="text-[11px] font-bold text-danger cursor-pointer disabled:opacity-50">
                  {lang === 'vi' ? 'Xoá' : 'Delete'}
                </button>
              ) : <span />}
              <div className="flex items-center gap-2">
                <button type="button" onClick={() => setModal(null)} disabled={saving} className="btn-ghost text-[11px] px-3 py-1.5 rounded-lg cursor-pointer">
                  {lang === 'vi' ? 'Huỷ' : 'Cancel'}
                </button>
                <button type="button" onClick={submitModal} disabled={saving} className="btn btn-accent text-[11px] px-3 py-1.5 rounded-lg cursor-pointer disabled:opacity-50">
                  {saving ? <Loader2 size={13} className="animate-spin" /> : (lang === 'vi' ? 'Lưu' : 'Save')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {scopePrompt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="card w-full max-w-xs p-5 space-y-3">
            <h4 className="text-[13px] font-bold text-fg">
              {lang === 'vi' ? 'Áp dụng cho…' : 'Apply to…'}
            </h4>
            <p className="text-[11px] text-fg-muted">
              {lang === 'vi'
                ? 'Đây là một mục trong chuỗi lặp lại. Bạn muốn áp dụng thay đổi cho riêng mục này hay toàn bộ chuỗi?'
                : 'This is part of a recurring series. Apply the change to just this occurrence or the whole series?'}
            </p>
            <div className="flex flex-col gap-2">
              <button type="button" disabled={saving} onClick={() => applyScope('this')} className="btn-ghost text-[11px] px-3 py-2 rounded-lg cursor-pointer disabled:opacity-50">
                {lang === 'vi' ? 'Chỉ mục này' : 'This occurrence only'}
              </button>
              <button type="button" disabled={saving} onClick={() => applyScope('all')} className="btn btn-accent text-[11px] px-3 py-2 rounded-lg cursor-pointer disabled:opacity-50">
                {lang === 'vi' ? 'Toàn bộ chuỗi' : 'The whole series'}
              </button>
              <button type="button" disabled={saving} onClick={() => { setScopePrompt(null); load(); }} className="text-[11px] text-fg-muted cursor-pointer">
                {lang === 'vi' ? 'Huỷ' : 'Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
