import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Send, ShieldAlert, BookOpen, Bell, X, Trash2, CloudOff } from 'lucide-react';
import Skeleton from './Skeleton';
import { CitationChip, SourceDrawer } from './SourceDrawer';
import { getChatState, sendChatMessage, clearChat, getStudentCourses } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

/** One badge per non-plain answer mode -- mirrors the guardrail/guidance
 * "never a dead end" contract from the old CuriChatLauncher/CuriContextPanel,
 * now driven by flat fields on the message instead of a nested metadata blob. */
function ModeBadge({ message, lang }) {
  if (message.blocked) {
    return (
      <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-warning-soft text-warning">
        <ShieldAlert size={10} />
        {lang === 'vi' ? 'Hướng dẫn học tập — không làm hộ' : 'Study guidance — not doing it for you'}
      </span>
    );
  }
  if (message.mode === 'out_of_scope') {
    return (
      <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-surface-elevated text-fg-muted">
        {lang === 'vi' ? 'Ngoài phạm vi tài liệu môn' : 'Outside course sources'}
      </span>
    );
  }
  if (message.mode === 'guidance') {
    return (
      <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-accent-soft text-ai-insight">
        {lang === 'vi' ? 'Gợi ý Socratic' : 'Socratic hint'}
      </span>
    );
  }
  if (message.mode === 'companion_crisis') {
    return (
      <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-danger-soft text-danger">
        {lang === 'vi' ? 'Hỗ trợ khẩn cấp' : 'Crisis support'}
      </span>
    );
  }
  return null;
}

/** Shown alongside ModeBadge (not instead of it) when this specific answer
 * fell back to a non-LLM path because Gemini actually rejected the call for
 * quota/rate-limit -- not just "no LLM configured". Lets a student (and,
 * via the admin quota panel, an admin) tell "AI is temporarily degraded"
 * apart from "this course has no matching content". */
function DegradedBadge({ degradedReason, lang }) {
  if (degradedReason !== 'quota') return null;
  return (
    <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-warning-soft text-warning">
      <CloudOff size={10} />
      {lang === 'vi' ? 'AI tạm hết hạn mức — đang dùng chế độ dự phòng' : 'AI temporarily rate-limited — using fallback'}
    </span>
  );
}

function citationKey(citation) {
  return citation.id || citation.chunkId || citation.sourceLabel;
}

/** A citation's `kind` decides how it's rendered: academic ones open the
 * real source drawer (chunkId lookup), help ones link to the feature's own
 * page, state citations (the student's own live data) are just a label --
 * there's no separate "source" to open for your own data. */
function CitationRow({ citations, lang, onOpenAcademic, onNavigateHelp }) {
  if (!citations?.length) return null;
  return (
    <div className="mt-2.5 pt-2 border-t border-line flex flex-wrap gap-x-3 gap-y-1.5">
      {citations.map((citation) => {
        if (citation.kind === 'academic') {
          return (
            <CitationChip
              key={citationKey(citation)}
              citation={{ ...citation, chunkId: citation.id }}
              onOpen={onOpenAcademic}
              lang={lang}
            />
          );
        }
        if (citation.kind === 'help') {
          return (
            <button
              key={citationKey(citation)}
              type="button"
              onClick={() => onNavigateHelp(citation.route)}
              className="cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent rounded inline-flex items-center gap-1 text-[10px] font-semibold text-accent-text-safe"
            >
              <BookOpen size={10} aria-hidden="true" />
              <span>{citation.sourceLabel}</span>
            </button>
          );
        }
        return (
          <span
            key={citationKey(citation)}
            className="inline-flex items-center gap-1 text-[10px] font-semibold text-fg-muted"
          >
            {citation.sourceLabel}
          </span>
        );
      })}
    </div>
  );
}

/**
 * Shared chat conversation UI — one continuous per-student conversation
 * (`/api/v1/student/chat*`), used by both the floating launcher and the
 * full-page companion. Self-contained: fetches its own history/courses and
 * owns send/clear, so both shells just render `<ChatPanel />`.
 */
export default function ChatPanel({
  variant = 'full',
  navigate,
  reminder,
  onDismissReminder,
  bubbleSizeClass = '',
}) {
  const { lang } = useLanguage();
  const [messages, setMessages] = useState([]);
  const [courses, setCourses] = useState([]);
  const [subjectCode, setSubjectCode] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState('');
  const [error, setError] = useState(null);
  const [openCitation, setOpenCitation] = useState(null);
  const [confirmingClear, setConfirmingClear] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    getChatState()
      .then((data) => {
        if (!cancelled) setMessages(data?.messages || []);
      })
      .catch((err) => !cancelled && setError(err))
      .finally(() => !cancelled && setLoadingHistory(false));
    getStudentCourses()
      .then((list) => {
        if (cancelled) return;
        setCourses(list || []);
        if (list?.length) setSubjectCode((prev) => prev || list[0].code);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  const handleSend = useCallback(
    async (event) => {
      event.preventDefault();
      const text = input.trim();
      if (!text || sending) return;
      setInput('');
      setSending(true);
      setError(null);
      setMessages((prev) => [
        ...prev,
        { id: `local-${Date.now()}`, sender: 'USER', content: text, mode: 'chat', citations: [] },
      ]);
      try {
        const reply = await sendChatMessage({ subjectCode: subjectCode || null, message: text });
        setMessages((prev) => [...prev, reply]);
      } catch (err) {
        setError(err);
        setInput(text);
      } finally {
        setSending(false);
      }
    },
    [input, sending, subjectCode],
  );

  const handleClear = async () => {
    if (!confirmingClear) {
      setConfirmingClear(true);
      return;
    }
    setConfirmingClear(false);
    try {
      await clearChat();
      setMessages([]);
    } catch (err) {
      setError(err);
    }
  };

  const handleNavigateHelp = (route) => {
    if (route && typeof navigate === 'function') navigate(route);
  };

  const isFull = variant === 'full';

  return (
    <section
      aria-label={lang === 'vi' ? 'Trợ lý Cursus' : 'Cursus Assistant'}
      className={`flex flex-col min-h-0 ${isFull ? 'card overflow-hidden min-h-[480px] max-h-[760px]' : `h-full ${bubbleSizeClass}`}`}
    >
      <header className="flex items-center gap-2 px-4 py-2.5 border-b shrink-0 border-line">
        <div className="min-w-0 flex-1">
          {courses.length > 1 && (
            <select
              className="input text-[10px] w-full truncate"
              style={{ height: '28px', paddingTop: '2px', paddingBottom: '2px', lineHeight: '1.2' }}
              value={subjectCode}
              onChange={(event) => setSubjectCode(event.target.value)}
              aria-label={lang === 'vi' ? 'Chọn môn học' : 'Select course'}
            >
              {courses.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code} — {c.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <button
          type="button"
          onClick={handleClear}
          onBlur={() => setConfirmingClear(false)}
          className="btn-ghost shrink-0 p-1.5 rounded-md cursor-pointer text-fg-muted hover:text-danger"
          aria-label={lang === 'vi' ? 'Xoá hội thoại' : 'Clear conversation'}
          title={
            confirmingClear
              ? lang === 'vi'
                ? 'Bấm lần nữa để xác nhận xoá'
                : 'Click again to confirm'
              : lang === 'vi'
                ? 'Xoá hội thoại'
                : 'Clear conversation'
          }
        >
          <Trash2 size={13} className={confirmingClear ? 'text-danger' : ''} />
        </button>
      </header>

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
            onClick={onDismissReminder}
            aria-label={lang === 'vi' ? 'Đóng nhắc nhở' : 'Dismiss reminder'}
            className="shrink-0 text-fg-muted hover:text-fg cursor-pointer"
          >
            <X size={12} />
          </button>
        </div>
      )}

      <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-4 text-left min-h-0">
        {loadingHistory ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-4/5 rounded" />
            <Skeleton className="h-4 w-3/5 rounded" />
          </div>
        ) : messages.length === 0 ? (
          <p className="text-[12px] text-fg-muted text-center py-6">
            {lang === 'vi'
              ? 'Hỏi về nội dung môn học, kế hoạch/tiến độ của bạn, hoặc cách dùng Cursus.'
              : 'Ask about course content, your own plan/progress, or how to use Cursus.'}
          </p>
        ) : (
          messages.map((message) =>
            message.sender === 'USER' ? (
              <div key={message.id} className="flex justify-end">
                <p className="text-[13px] px-3.5 py-2 rounded-2xl rounded-br-sm max-w-[85%] bg-accent-cta text-white shadow-elevation-1 whitespace-pre-wrap">
                  {message.content}
                </p>
              </div>
            ) : (
              <div key={message.id} className="flex flex-col gap-2 items-start">
                <ModeBadge message={message} lang={lang} />
                <DegradedBadge degradedReason={message.degradedReason} lang={lang} />
                <div className="max-w-[90%] text-[13px] leading-relaxed px-3.5 py-3 rounded-2xl rounded-bl-sm whitespace-pre-wrap bg-surface-elevated border border-line text-fg">
                  {message.content}
                  <CitationRow
                    citations={message.citations}
                    lang={lang}
                    onOpenAcademic={setOpenCitation}
                    onNavigateHelp={handleNavigateHelp}
                  />
                </div>
              </div>
            ),
          )
        )}
        {sending && (
          <div className="space-y-2">
            <Skeleton className="h-4 w-3/5 rounded" />
          </div>
        )}
      </div>

      <form className="flex items-center gap-2 p-3 border-t shrink-0 border-line" onSubmit={handleSend}>
        <label htmlFor="chat-panel-input" className="sr-only">
          {lang === 'vi' ? 'Tin nhắn' : 'Message'}
        </label>
        <input
          id="chat-panel-input"
          className="input text-[13px] flex-1 h-10"
          placeholder={lang === 'vi' ? 'Nhắn cho Trợ lý Cursus…' : 'Message Cursus Assistant…'}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={sending}
        />
        <button
          type="submit"
          className="btn btn-accent w-10 h-10 shrink-0 rounded-lg cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
          disabled={!input.trim() || sending}
          aria-label={lang === 'vi' ? 'Gửi' : 'Send'}
        >
          <Send size={14} />
        </button>
      </form>

      {error && <p className="px-4 pb-3 text-[11px] text-danger">{error.message}</p>}

      {openCitation && (
        <SourceDrawer citation={openCitation} onClose={() => setOpenCitation(null)} lang={lang} />
      )}
    </section>
  );
}
