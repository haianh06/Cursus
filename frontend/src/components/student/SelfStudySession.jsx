import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Bell, Coffee, Flame, Loader2, Timer, X } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  abandonSelfStudySession,
  getSelfStudySession,
  getUpcomingSelfStudy,
  startSelfStudySession,
} from '../../lib/api';
import {
  notificationPermission,
  notify,
  playPomodoroChime,
  requestNotificationPermission,
} from '../../lib/notifications';

const RESYNC_MS = 10_000;

const PHASE_LABEL = {
  work: { vi: 'Tập trung', en: 'Focus' },
  break: { vi: 'Nghỉ ngắn', en: 'Short break' },
  long_break: { vi: 'Nghỉ dài', en: 'Long break' },
  done: { vi: 'Đã hoàn thành', en: 'Done' },
};

function formatClock(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds));
  const m = Math.floor(s / 60);
  const rest = s % 60;
  return `${String(m).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
}

export default function SelfStudySession() {
  const { blockId } = useParams();
  const navigate = useNavigate();
  const { lang } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [notFinishedInfo, setNotFinishedInfo] = useState(null); // window-not-open / already-finished
  const [session, setSession] = useState(null);
  const [display, setDisplay] = useState(null); // { phase, phaseRemainingSeconds, sessionRemainingSeconds }
  const [abandoning, setAbandoning] = useState(false);
  const [permission, setPermission] = useState(notificationPermission());

  const fetchedAtRef = useRef(0);
  const prevPhaseRef = useRef(null);

  const applySession = useCallback((data) => {
    setSession(data);
    fetchedAtRef.current = Date.now();
    setDisplay({
      phase: data.phase,
      phaseRemainingSeconds: data.phaseRemainingSeconds,
      sessionRemainingSeconds: data.sessionRemainingSeconds,
    });
    const phaseChanged = prevPhaseRef.current && prevPhaseRef.current !== data.phase;
    if (phaseChanged) {
      // Sound doesn't need Notification permission — only the (silent,
      // OS-level) visual notification below does.
      if (data.status === 'COMPLETED') {
        playPomodoroChime('complete');
      } else {
        playPomodoroChime(data.phase === 'break' || data.phase === 'long_break' ? 'break' : 'work');
      }
      if (permission === 'granted') {
        const label = PHASE_LABEL[data.phase]?.[lang] || data.phase;
        notify(lang === 'vi' ? 'Đổi giai đoạn tự học' : 'Study phase changed', {
          body: label,
          tag: `self-study-phase-${blockId}`,
        });
      }
    }
    prevPhaseRef.current = data.phase;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, permission, blockId]);

  // Start (or resume) the session for this block.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setNotFinishedInfo(null);
    startSelfStudySession(blockId)
      .then((data) => {
        if (cancelled) return;
        applySession(data);
      })
      .catch(async (err) => {
        if (cancelled) return;
        if (err?.status === 409) {
          // Already has a finished session — find it and show the recap.
          try {
            const upcoming = await getUpcomingSelfStudy();
            const match = upcoming.find((item) => item.blockId === blockId);
            if (match?.sessionId) {
              const data = await getSelfStudySession(match.sessionId);
              if (!cancelled) setSession(data);
              return;
            }
          } catch {
            /* fall through to generic message */
          }
          if (!cancelled) setNotFinishedInfo({ kind: 'finished' });
          return;
        }
        if (err?.status === 400) {
          if (!cancelled) setNotFinishedInfo({ kind: 'window', message: err.message });
          return;
        }
        if (!cancelled) setLoadError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blockId]);

  // Resync with the server periodically — it owns phase transitions and
  // natural completion, this page only ticks the display between polls.
  useEffect(() => {
    if (!session || !session.id) return undefined;
    if (session.status !== 'IN_PROGRESS') return undefined;
    let cancelled = false;
    const id = setInterval(() => {
      getSelfStudySession(session.id)
        .then((data) => {
          if (!cancelled) applySession(data);
        })
        .catch(() => {});
    }, RESYNC_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session, applySession]);

  // Local 1s ticker between resyncs — purely cosmetic, never authoritative.
  useEffect(() => {
    if (!display || session?.status !== 'IN_PROGRESS') return undefined;
    const id = setInterval(() => {
      setDisplay((prev) =>
        prev && {
          ...prev,
          phaseRemainingSeconds: Math.max(0, prev.phaseRemainingSeconds - 1),
          sessionRemainingSeconds: Math.max(0, prev.sessionRemainingSeconds - 1),
        },
      );
    }, 1000);
    return () => clearInterval(id);
  }, [display, session]);

  const handleEnablePermission = async () => {
    const result = await requestNotificationPermission();
    setPermission(result);
  };

  const handleAbandon = async () => {
    if (!session || abandoning) return;
    setAbandoning(true);
    try {
      const data = await abandonSelfStudySession(session.id);
      applySession(data);
    } catch {
      /* ignore — user can retry */
    } finally {
      setAbandoning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3">
        <Loader2 size={28} className="animate-spin text-accent" />
        <p className="text-[13px] text-fg-muted">
          {lang === 'vi' ? 'Đang chuẩn bị buổi tự học…' : 'Preparing your study session…'}
        </p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3 p-6 text-center">
        <p className="text-[14px] font-semibold text-danger">{loadError.message}</p>
        <button type="button" className="btn btn-outline text-[13px] px-4 py-2 rounded-lg cursor-pointer" onClick={() => navigate('/student/planner')}>
          {lang === 'vi' ? 'Về Thời khoá biểu' : 'Back to Timetable'}
        </button>
      </div>
    );
  }

  if (notFinishedInfo) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3 p-6 text-center max-w-sm mx-auto">
        <Timer size={32} className="text-fg-muted" />
        <p className="text-[14px] font-semibold text-fg">
          {notFinishedInfo.kind === 'finished'
            ? lang === 'vi' ? 'Buổi tự học này đã kết thúc trước đó.' : 'This session already finished.'
            : lang === 'vi' ? 'Chưa tới giờ tự học.' : 'This session hasn’t opened yet.'}
        </p>
        <p className="text-[12px] text-fg-muted">
          {notFinishedInfo.kind === 'window' &&
            (lang === 'vi'
              ? 'Có thể bắt đầu sớm nhất 10 phút trước giờ hẹn.'
              : 'You can start as early as 10 minutes before the scheduled time.')}
        </p>
        <button type="button" className="btn btn-outline text-[13px] px-4 py-2 rounded-lg cursor-pointer" onClick={() => navigate('/student/planner')}>
          {lang === 'vi' ? 'Về Thời khoá biểu' : 'Back to Timetable'}
        </button>
      </div>
    );
  }

  const isTerminal = session?.status === 'COMPLETED' || session?.status === 'ABANDONED';
  const phase = display?.phase || session?.phase || 'work';
  const phaseLabel = PHASE_LABEL[phase]?.[lang] || phase;
  const isBreak = phase === 'break' || phase === 'long_break';
  const ringColor = isTerminal ? 'var(--success)' : isBreak ? 'var(--gold)' : 'var(--accent)';

  return (
    <div className="flex flex-col items-center gap-6 p-6 md:p-10 animate-fade-up max-w-lg mx-auto text-center">
      <button
        type="button"
        onClick={() => navigate('/student/planner')}
        className="self-start btn-ghost text-[12px] px-2 py-1.5 rounded-lg cursor-pointer flex items-center gap-1.5 text-fg-muted"
      >
        <ArrowLeft size={14} /> {lang === 'vi' ? 'Thời khoá biểu' : 'Timetable'}
      </button>

      <p className="text-[15px] font-bold text-fg">{session?.title}</p>

      {permission === 'default' && !isTerminal && (
        <button
          type="button"
          onClick={handleEnablePermission}
          className="flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-full border border-line bg-surface-elevated text-fg-secondary cursor-pointer"
        >
          <Bell size={11} />
          {lang === 'vi' ? 'Bật nhắc lịch tự học' : 'Enable study reminders'}
        </button>
      )}

      <div
        className="w-64 h-64 rounded-full flex flex-col items-center justify-center border-8"
        style={{ borderColor: ringColor }}
      >
        {isBreak ? <Coffee size={22} style={{ color: ringColor }} /> : <Flame size={22} style={{ color: ringColor }} />}
        <span className="font-display text-5xl font-bold mt-2 mono text-fg">
          {isTerminal ? '00:00' : formatClock(display?.phaseRemainingSeconds ?? 0)}
        </span>
        <span className="text-[12px] font-bold uppercase tracking-widest mt-1" style={{ color: ringColor }}>
          {phaseLabel}
        </span>
      </div>

      <div className="flex items-center gap-6 text-[13px] text-fg-secondary">
        <span>🍅 {lang === 'vi' ? 'Đã hoàn thành' : 'Completed'}: <strong>{session?.pomodorosCompleted ?? 0}</strong></span>
        <span>
          {lang === 'vi' ? 'Buổi còn' : 'Session left'}:{' '}
          <strong>{formatClock(display?.sessionRemainingSeconds ?? 0)}</strong>
        </span>
      </div>

      {isTerminal ? (
        <div className="card p-4 w-full">
          <p className="text-[13px] font-semibold text-success mb-1">
            {session.status === 'COMPLETED'
              ? lang === 'vi' ? 'Hoàn thành buổi tự học!' : 'Study session complete!'
              : lang === 'vi' ? 'Đã kết thúc sớm.' : 'Ended early.'}
          </p>
          <p className="text-[12px] text-fg-muted">
            {lang === 'vi' ? 'Thời gian thực tế' : 'Actual time'}: {session.actualMinutes ?? 0}{' '}
            {lang === 'vi' ? 'phút' : 'min'} · 🍅 {session.pomodorosCompleted}
          </p>
          <button
            type="button"
            className="btn btn-accent text-[13px] px-4 py-2 rounded-lg cursor-pointer mt-3"
            onClick={() => navigate('/student')}
          >
            {lang === 'vi' ? 'Về Bảng điều khiển' : 'Back to Dashboard'}
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="btn btn-outline text-[13px] px-4 py-2 rounded-lg cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
          onClick={handleAbandon}
          disabled={abandoning}
        >
          <X size={14} /> {lang === 'vi' ? 'Kết thúc sớm' : 'End early'}
        </button>
      )}
    </div>
  );
}
