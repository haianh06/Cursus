import React, { useEffect, useRef, useState } from 'react';
import { MessageCircle, X, ChevronDown, Maximize2, Minimize2, Bell } from 'lucide-react';
import CursusMascot from './CursusMascot';
import Skeleton from './Skeleton';
import { CourseCompanionChat } from '../student/CourseCompanionChat';
import { getStudentCourses } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';
import { onCompanionReminderRequest } from '../../lib/companionChatBus';

const MIN_WIDTH = 380;
const MIN_HEIGHT = 460;
const DEFAULT_WIDTH = 440;
const DEFAULT_HEIGHT = 'min(660px, calc(100vh - 7rem))';
const SIZE_STORAGE_KEY = 'cursus_companion_chat_size';

function loadStoredSize() {
  try {
    const raw = localStorage.getItem(SIZE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.width === 'number' && typeof parsed?.height === 'number') return parsed;
  } catch {
    /* ignore malformed/blocked storage */
  }
  return null;
}

/**
 * Single global entry point for the student companion chat — a floating
 * bubble (bottom-right, every authenticated student page) that opens a
 * panel wrapping the real, backend-wired `CourseCompanionChat`. Replaces
 * the old split UI: a separate "Trợ lý theo môn" sidebar page plus a
 * scripted, backend-less FAQ launcher on the marketing site. Only the
 * course picker here is new — the chat itself is unchanged.
 *
 * The panel is user-resizable (drag the top-left grip) and can be toggled
 * to a near-fullscreen size — it no longer ships at one fixed size. The
 * dragged size is remembered in localStorage (per browser) across opens.
 */
export default function CompanionChatBubble() {
  const { lang } = useLanguage();
  const [open, setOpen] = useState(false);
  const [courses, setCourses] = useState([]);
  const [subjectCode, setSubjectCode] = useState('');
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [size, setSize] = useState(loadStoredSize);
  const [maximized, setMaximized] = useState(false);
  const [reminder, setReminder] = useState(null);
  const panelRef = useRef(null);

  // A page (e.g. "Today's plan") can ask this bubble to pop open with a
  // proactive reminder of real, already-scheduled tasks — see
  // lib/companionChatBus.js. Closing the panel clears it.
  useEffect(
    () =>
      onCompanionReminderRequest((payload) => {
        setReminder(payload);
        setOpen(true);
      }),
    [],
  );

  const closePanel = () => {
    setOpen(false);
    setReminder(null);
  };

  useEffect(() => {
    if (!open || courses.length || !loadingCourses) return;
    let cancelled = false;
    getStudentCourses()
      .then((list) => {
        if (cancelled) return;
        setCourses(list || []);
        if (list?.length) setSubjectCode((prev) => prev || list[0].code);
      })
      .finally(() => !cancelled && setLoadingCourses(false));
    return () => {
      cancelled = true;
    };
  }, [open, courses.length, loadingCourses]);

  const handleResizeStart = (event) => {
    event.preventDefault();
    const panel = panelRef.current;
    if (!panel) return;
    setMaximized(false);
    const startX = event.clientX;
    const startY = event.clientY;
    const startWidth = panel.offsetWidth;
    const startHeight = panel.offsetHeight;

    const onMove = (moveEvent) => {
      const nextWidth = Math.min(
        window.innerWidth - 40,
        Math.max(MIN_WIDTH, startWidth + (startX - moveEvent.clientX)),
      );
      const nextHeight = Math.min(
        window.innerHeight - 112,
        Math.max(MIN_HEIGHT, startHeight + (startY - moveEvent.clientY)),
      );
      setSize({ width: nextWidth, height: nextHeight });
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      setSize((current) => {
        if (current) {
          try {
            localStorage.setItem(SIZE_STORAGE_KEY, JSON.stringify(current));
          } catch {
            /* ignore */
          }
        }
        return current;
      });
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const panelStyle = maximized
    ? { width: 'min(760px, calc(100vw - 2.5rem))', height: 'calc(100vh - 7rem)' }
    : size
      ? { width: `${size.width}px`, height: `${size.height}px` }
      : { width: `${DEFAULT_WIDTH}px`, height: DEFAULT_HEIGHT };

  return (
    <>
      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-label={lang === 'vi' ? 'Trợ lý học tập theo môn' : 'Course companion chat'}
          className="fixed bottom-24 right-5 z-50 max-w-[calc(100vw-2.5rem)] max-h-[calc(100vh-7rem)] rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 flex flex-col overflow-hidden animate-fade-up"
          style={panelStyle}
        >
          {!maximized && (
            <div
              onPointerDown={handleResizeStart}
              role="separator"
              aria-label={lang === 'vi' ? 'Kéo để đổi kích thước' : 'Drag to resize'}
              title={lang === 'vi' ? 'Kéo để đổi kích thước' : 'Drag to resize'}
              className="absolute top-0 left-0 w-4 h-4 cursor-nwse-resize touch-none z-10"
              style={{
                background:
                  'linear-gradient(135deg, transparent 0%, transparent 45%, var(--line) 45%, var(--line) 55%, transparent 55%, transparent 100%)',
              }}
            />
          )}
          <div className="flex flex-col border-b border-line shrink-0">
            <div className="flex items-center gap-2.5 px-4 pt-3 pb-2">
              <CursusMascot size={24} />
              <span className="text-[14px] font-bold text-fg flex-1 truncate">
                {lang === 'vi' ? 'Trợ lý học tập' : 'Study assistant'}
              </span>
              <button
                type="button"
                className="btn-ghost p-1.5 rounded-md cursor-pointer shrink-0 text-fg-muted hover:text-fg transition-colors"
                onClick={() => setMaximized((prev) => !prev)}
                aria-label={
                  maximized
                    ? lang === 'vi' ? 'Thu nhỏ' : 'Restore size'
                    : lang === 'vi' ? 'Phóng to' : 'Maximize'
                }
                title={
                  maximized
                    ? lang === 'vi' ? 'Thu nhỏ' : 'Restore size'
                    : lang === 'vi' ? 'Phóng to' : 'Maximize'
                }
              >
                {maximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>
              <button
                type="button"
                className="btn-ghost p-1.5 rounded-md cursor-pointer shrink-0 text-fg-muted hover:text-fg transition-colors"
                onClick={closePanel}
                aria-label={lang === 'vi' ? 'Đóng' : 'Close'}
              >
                <X size={15} />
              </button>
            </div>
            <div className="px-4 pb-3">
              {loadingCourses ? (
                <Skeleton className="h-9 w-full rounded-lg" />
              ) : courses.length > 0 ? (
                <div className="relative">
                  <select
                    className="input text-[12px] h-9 pr-8 w-full appearance-none"
                    value={subjectCode}
                    onChange={(e) => setSubjectCode(e.target.value)}
                    aria-label={lang === 'vi' ? 'Chọn môn học' : 'Select course'}
                  >
                    {courses.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.code} — {c.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted pointer-events-none" />
                </div>
              ) : null}
            </div>
          </div>
          {reminder?.tasks?.length > 0 && (
            <div className="flex items-start gap-2 px-3.5 py-2.5 border-b border-line bg-accent-soft shrink-0" role="status">
              <Bell size={14} className="text-accent shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-[12px] font-bold text-fg mb-1">
                  {lang === 'vi' ? 'Việc gần nhất hôm nay' : 'Coming up today'}
                </p>
                <ul className="space-y-0.5">
                  {reminder.tasks.map((task) => (
                    <li key={task.id} className="text-[11px] text-fg-secondary truncate">
                      {task.title}
                      {task.estimatedMinutes != null && ` · ${task.estimatedMinutes}${lang === 'vi' ? ' phút' : 'm'}`}
                    </li>
                  ))}
                </ul>
              </div>
              <button
                type="button"
                onClick={() => setReminder(null)}
                aria-label={lang === 'vi' ? 'Đóng nhắc nhở' : 'Dismiss reminder'}
                className="shrink-0 text-fg-muted hover:text-fg cursor-pointer"
              >
                <X size={12} />
              </button>
            </div>
          )}
          <div className="flex-1 min-h-0">
            <CourseCompanionChat subjectCode={subjectCode} embedded />
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={lang === 'vi' ? 'Mở trợ lý học tập' : 'Open course companion'}
        aria-expanded={open}
        className="fixed bottom-5 right-5 z-50 w-14 h-14 rounded-full bg-accent-cta text-white shadow-elevation-3 flex items-center justify-center cursor-pointer transition-transform hover:scale-105 active:scale-95"
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </>
  );
}
