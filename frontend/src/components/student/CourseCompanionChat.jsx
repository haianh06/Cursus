import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Send, Plus, Trash2, ShieldAlert, MessageSquare, BookOpen } from 'lucide-react';
import CursusMascot from '../shared/CursusMascot';
import Skeleton from '../shared/Skeleton';
import EmptyState from '../shared/EmptyState';
import {
  getCompanionThreads,
  createCompanionThread,
  getCompanionThread,
  deleteCompanionThread,
  sendCompanionMessage,
  getStudentCourses,
} from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Per-course companion chat — thread-based (multiple named conversations per
 * course), backed by `/student/companion/threads*`. Distinct from
 * `CuriContextPanel` (single ephemeral session tied to `/qa`): this one
 * persists threads server-side and lets the student switch between them.
 *
 * Guardrail/blocked responses arrive as ordinary assistant messages whose
 * `metadata.mode` is one of `blocked | out_of_scope | guidance | grounded |
 * web_search | no_source` — there is no boolean "blocked" flag on the wire,
 * so we branch on that string the same way CuriContextPanel branches on
 * `blocked`/`blockReason`, to keep the same "never a dead end" UX contract.
 */
function ModeBadge({ mode, lang }) {
  if (!mode || mode === 'grounded' || mode === 'web_search') return null;
  if (mode === 'blocked') {
    return (
      <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-warning-soft text-warning">
        <ShieldAlert size={10} />
        {lang === 'vi' ? 'Hướng dẫn học tập — không làm hộ' : 'Study guidance — not doing it for you'}
      </span>
    );
  }
  if (mode === 'out_of_scope') {
    return (
      <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-surface-elevated text-fg-muted">
        {lang === 'vi' ? 'Ngoài phạm vi tài liệu môn' : 'Outside course sources'}
      </span>
    );
  }
  if (mode === 'guidance') {
    return (
      <span className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-accent-soft text-ai-insight">
        {lang === 'vi' ? 'Gợi ý Socratic' : 'Socratic hint'}
      </span>
    );
  }
  return null;
}

/** Standalone page: owns its own course picker, then renders the chat below. */
export default function StudentCompanionPage() {
  const { lang } = useLanguage();
  const [courses, setCourses] = useState([]);
  const [subjectCode, setSubjectCode] = useState('');
  const [loadingCourses, setLoadingCourses] = useState(true);

  useEffect(() => {
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
  }, []);

  return (
    <div className="flex flex-col gap-4 p-6 animate-fade-up max-w-4xl">
      <div className="flex items-center justify-between border-b pb-4 border-line">
        <div className="text-left">
          <h1 className="font-display text-xl font-bold text-fg">
            {lang === 'vi' ? 'Trợ lý học tập theo môn' : 'Course companion'}
          </h1>
          <p className="text-xs text-fg-muted mt-1">
            {lang === 'vi'
              ? 'Trò chuyện nhiều luồng riêng cho từng môn học, có rào chắn học thuật.'
              : 'Multi-thread chat scoped to a course, with academic guardrails.'}
          </p>
        </div>
        {loadingCourses ? (
          <Skeleton className="h-9 w-48 rounded-lg" />
        ) : (
          <select
            className="input text-xs w-52"
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
        )}
      </div>
      <CourseCompanionChat subjectCode={subjectCode} />
    </div>
  );
}

export function CourseCompanionChat({ subjectCode }) {
  const { lang } = useLanguage();
  const [threads, setThreads] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState('');
  const [error, setError] = useState(null);
  const listRef = useRef(null);

  const loadThreads = useCallback(async () => {
    if (!subjectCode) return;
    setLoadingThreads(true);
    setError(null);
    try {
      const list = await getCompanionThreads(subjectCode);
      setThreads(list || []);
      if (list?.length && !activeId) {
        setActiveId(list[0].id);
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoadingThreads(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subjectCode]);

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  const loadDetail = useCallback(async (conversationId) => {
    if (!conversationId) {
      setDetail(null);
      return;
    }
    setLoadingDetail(true);
    setError(null);
    try {
      const data = await getCompanionThread(conversationId);
      setDetail(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    loadDetail(activeId);
  }, [activeId, loadDetail]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [detail, sending]);

  const handleNewThread = async () => {
    if (!subjectCode) return;
    setError(null);
    try {
      const created = await createCompanionThread({ subjectCode, title: '' });
      setThreads((prev) => [created, ...prev]);
      setActiveId(created.id);
    } catch (err) {
      setError(err);
    }
  };

  const handleDeleteThread = async (conversationId) => {
    // Confirm-before-destroy: deleting a thread is not undoable server-side.
    // Plain confirm() here on purpose — Checkpoint 3 (ConfirmDialog) will
    // swap this call site over once the shared dialog exists, to keep a
    // single confirm pattern across the app instead of two different ones.
    const message =
      lang === 'vi'
        ? 'Xoá hội thoại này? Không thể hoàn tác.'
        : 'Delete this thread? This cannot be undone.';
    if (!window.confirm(message)) return;
    setError(null);
    try {
      await deleteCompanionThread(conversationId);
      setThreads((prev) => prev.filter((t) => t.id !== conversationId));
      if (activeId === conversationId) {
        setActiveId(null);
        setDetail(null);
      }
    } catch (err) {
      setError(err);
    }
  };

  const handleThreadKeyDown = (event, threadId) => {
    // Only react when the wrapper div itself has focus — a bubbled keydown from
    // the nested delete button must reach its own native button activation
    // unimpeded, or Enter/Space on "Delete" would silently do nothing.
    if (event.target !== event.currentTarget) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setActiveId(threadId);
    }
  };

  const handleSend = async (event) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || sending || !activeId) return;
    setInput('');
    setSending(true);
    setError(null);
    // Optimistic user message so the UI feels immediate.
    setDetail((prev) =>
      prev
        ? { ...prev, messages: [...(prev.messages || []), { id: `local-${Date.now()}`, sender: 'USER', content: text, metadata: {} }] }
        : prev,
    );
    try {
      const reply = await sendCompanionMessage(activeId, text);
      setDetail((prev) =>
        prev ? { ...prev, messages: [...(prev.messages || []), reply] } : prev,
      );
    } catch (err) {
      setError(err);
      setInput(text);
    } finally {
      setSending(false);
    }
  };

  if (!subjectCode) {
    return (
      <div className="card">
        <EmptyState
          icon={<BookOpen size={28} className="text-fg-muted" />}
          title={lang === 'vi' ? 'Chọn một môn học để bắt đầu' : 'Pick a course to get started'}
          description={
            lang === 'vi'
              ? 'Chọn môn học ở trên để mở trợ lý học tập riêng cho môn đó.'
              : 'Select a course above to open its dedicated companion chat.'
          }
        />
      </div>
    );
  }

  return (
    <section
      aria-label={lang === 'vi' ? 'Trợ lý học tập theo môn' : 'Course companion'}
      className="card flex overflow-hidden min-h-[420px] max-h-[720px]"
    >
      {/* Thread list */}
      <div className="w-48 shrink-0 border-r border-line flex flex-col">
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-line">
          <span className="text-[11px] font-bold text-fg-muted uppercase tracking-wide">
            {lang === 'vi' ? 'Hội thoại' : 'Threads'}
          </span>
          <button
            type="button"
            className="btn-ghost p-1 rounded-md cursor-pointer"
            onClick={handleNewThread}
            aria-label={lang === 'vi' ? 'Cuộc trò chuyện mới' : 'New thread'}
          >
            <Plus size={13} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loadingThreads ? (
            <div className="p-3 space-y-2">
              <Skeleton className="h-8 w-full rounded-lg" />
              <Skeleton className="h-8 w-full rounded-lg" />
            </div>
          ) : threads.length === 0 ? (
            <div className="flex flex-col items-center gap-2 text-center py-6 px-2">
              <MessageSquare size={20} className="text-fg-muted" />
              <p className="text-[11px] text-fg-muted">
                {lang === 'vi' ? 'Chưa có hội thoại nào.' : 'No threads yet.'}
              </p>
            </div>
          ) : (
            threads.map((thread) => (
              <div
                key={thread.id}
                role="button"
                tabIndex={0}
                aria-current={thread.id === activeId ? 'true' : undefined}
                className={`group flex items-center gap-1 px-2 py-2 border-b border-line cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset ${
                  thread.id === activeId ? 'bg-accent-soft' : 'hover:bg-surface-elevated'
                }`}
                onClick={() => setActiveId(thread.id)}
                onKeyDown={(event) => handleThreadKeyDown(event, thread.id)}
              >
                <MessageSquare size={12} className="shrink-0 text-fg-muted" />
                <span className="flex-1 text-[11px] truncate text-fg-secondary">
                  {thread.title || (lang === 'vi' ? 'Hội thoại mới' : 'New thread')}
                </span>
                <button
                  type="button"
                  className="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 btn-ghost p-1 rounded cursor-pointer shrink-0"
                  onClick={(event) => {
                    event.stopPropagation();
                    handleDeleteThread(thread.id);
                  }}
                  aria-label={lang === 'vi' ? 'Xóa hội thoại' : 'Delete thread'}
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Active thread */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-2 px-4 py-3 border-b shrink-0 border-line">
          <CursusMascot size={22} />
          <div className="min-w-0 flex-1">
            <h2 className="text-[14px] font-bold font-display text-fg">
              {lang === 'vi' ? 'Trợ lý học tập' : 'Course companion'}
            </h2>
            <p className="text-[11px] truncate text-fg-muted">{subjectCode}</p>
          </div>
        </header>

        {!activeId ? (
          <div className="flex-1 flex items-center justify-center p-6">
            <EmptyState
              icon={<MessageSquare size={28} className="text-fg-muted" />}
              title={lang === 'vi' ? 'Chọn hoặc tạo một hội thoại' : 'Select or start a thread'}
              description={
                lang === 'vi'
                  ? 'Bắt đầu hỏi trợ lý học tập về nội dung môn học này.'
                  : 'Start asking the companion about this course.'
              }
              actionLabel={lang === 'vi' ? 'Cuộc trò chuyện mới' : 'New thread'}
              onAction={handleNewThread}
            />
          </div>
        ) : (
          <>
            <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-4">
              {loadingDetail ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-4/5 rounded" />
                  <Skeleton className="h-4 w-3/5 rounded" />
                </div>
              ) : (
                (detail?.messages || []).map((message) =>
                  message.sender === 'USER' ? (
                    <div key={message.id} className="flex justify-end">
                      <p className="text-[13px] px-3.5 py-2 rounded-2xl rounded-br-sm max-w-[85%] bg-accent-cta text-white shadow-elevation-1">
                        {message.content}
                      </p>
                    </div>
                  ) : (
                    <div key={message.id} className="flex flex-col gap-2">
                      <ModeBadge mode={message.metadata?.mode} lang={lang} />
                      <div className="text-[13px] leading-relaxed px-3.5 py-3 rounded-2xl rounded-bl-sm whitespace-pre-line bg-surface-elevated border border-line text-fg">
                        {message.content}
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
              <label htmlFor="companion-input" className="sr-only">
                {lang === 'vi' ? 'Tin nhắn' : 'Message'}
              </label>
              <input
                id="companion-input"
                className="input text-[13px] flex-1 h-10"
                placeholder={lang === 'vi' ? 'Nhắn cho trợ lý học tập…' : 'Message the companion…'}
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
          </>
        )}

        {error && <p className="px-4 pb-3 text-[11px] text-danger">{error.message}</p>}
      </div>
    </section>
  );
}
