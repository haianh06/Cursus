import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, Send, X, History, Download, Trash2, Check, XCircle, Sparkles } from 'lucide-react';
import {
  streamCursusChat,
  getCursusBriefing,
  dismissCursusBriefing,
  getCursusConversations,
  getCursusConversationMessages,
  exportCursusHistory,
  deleteCursusHistory,
  confirmCursusAction,
  cancelCursusAction,
} from '../../lib/api';
import { CitationChip, SourceDrawer } from '../shared/SourceDrawer';
import ConfirmDialog from '../shared/ConfirmDialog';

/** One message per failure mode backend/ai-service can report, instead of
 * a single generic "Cursus is unavailable" for every case — a rate limit
 * or a daily-budget pause is not the same problem as the service being
 * genuinely down, and telling the student which one it is sets the right
 * expectation for whether "try again in a minute" will actually help. */
const ERROR_MESSAGES = {
  RATE_LIMITED: 'Bạn đang gửi tin nhắn quá nhanh. Vui lòng đợi một chút rồi thử lại.',
  QUOTA_EXHAUSTED: 'Hệ thống AI đang tạm hết hạn mức sử dụng. Vui lòng thử lại sau ít phút.',
  LLM_BUDGET_EXCEEDED: 'Cursus đang tạm ngừng do đã dùng hết hạn mức hỗ trợ AI trong ngày. Vui lòng quay lại vào ngày mai.',
  DB_ERROR: 'Không thể kết nối cơ sở dữ liệu lúc này. Vui lòng thử lại sau ít phút.',
  AI_UNAVAILABLE: 'Cursus đang tạm thời không phản hồi. Hãy thử lại sau.',
  // Same student-facing copy as AI_UNAVAILABLE — a bad server-side API key
  // isn't something the student can act on differently, but ops logs/alerts
  // upstream keep this code distinct from a real provider outage.
  AI_MISCONFIGURED: 'Cursus đang tạm thời không phản hồi. Hãy thử lại sau.',
  INTERNAL_ERROR: 'Có lỗi xảy ra phía hệ thống. Vui lòng thử lại.',
  NETWORK_ERROR: 'Không kết nối được tới máy chủ. Kiểm tra lại kết nối mạng của bạn.',
};

function messageForErrorCode(code) {
  return ERROR_MESSAGES[code] || ERROR_MESSAGES.AI_UNAVAILABLE;
}

/** Shared with the launcher button and the panel header so the "brand" gradient
 * lives in one place — reuses the same tokens as .btn-accent in index.css. */
const HEADER_GRADIENT = 'linear-gradient(135deg, var(--accent-cta-bg) 0%, var(--accent-cta-bg-hover) 100%)';

const QUICK_REPLIES = [
  'Hôm nay mình nên học gì trước?',
  'Tóm tắt syllabus môn này giúp mình',
  'Kế hoạch học tập của mình đang thế nào?',
];

function QuickReplies({ onPick, disabled }) {
  return (
    <div className="flex flex-wrap gap-2">
      {QUICK_REPLIES.map((text) => (
        <button
          key={text}
          type="button"
          disabled={disabled}
          onClick={() => onPick(text)}
          className="rounded-full border border-accent/30 bg-accent-soft px-3 py-1.5 text-left text-xs font-medium text-accent hover:bg-accent/10 disabled:opacity-50"
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/** Welcome card shown before the first message — merges the frequency-capped
 * server briefing (ChatBriefingImpression) with a generic greeting fallback,
 * plus quick-reply chips to get a first message out with one tap. */
function WelcomeCard({ briefing, onDismissBriefing, onPickReply, disabled }) {
  return (
    <div className="rounded-2xl border border-border bg-paper p-4 text-sm text-ink shadow-sm">
      <p>
        {briefing
          ? briefing.message
          : 'Chào bạn! Mình là Cursus. Bạn muốn hỏi gì về môn học, kế hoạch học tập hay cách dùng Cursus?'}
      </p>
      {briefing && (
        <div className="mt-2 flex gap-3 text-xs font-semibold">
          <button type="button" onClick={() => onDismissBriefing(1)} className="text-accent hover:underline">
            Đã hiểu
          </button>
          <button type="button" onClick={() => onDismissBriefing(7)} className="text-ink-secondary hover:underline">
            Nhắc lại sau
          </button>
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2 border-t border-border pt-3">
        <QuickReplies onPick={onPickReply} disabled={disabled} />
      </div>
    </div>
  );
}

function ChatHistorySidebar({ conversations, activeId, onSelect, onExport, onDeleteAll, onClose }) {
  return (
    <div className="absolute inset-0 z-10 flex flex-col bg-paper">
      <header className="flex items-center justify-between border-b border-border bg-surface px-5 py-4">
        <h3 className="font-serif text-base text-ink">Lịch sử trò chuyện</h3>
        <button type="button" aria-label="Đóng lịch sử" onClick={onClose}>
          <X size={18} />
        </button>
      </header>
      <div className="flex-1 overflow-y-auto p-3">
        {conversations.length === 0 ? (
          <p className="p-2 text-sm text-ink-secondary">Chưa có cuộc trò chuyện nào.</p>
        ) : (
          <ul className="space-y-1">
            {conversations.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm hover:bg-surface ${item.id === activeId ? 'bg-accent-soft text-accent' : 'text-ink'}`}
                >
                  {new Date(item.updatedAt).toLocaleString('vi')}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <footer className="flex gap-2 border-t border-border bg-surface p-3">
        <button type="button" onClick={onExport} className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1.5 text-xs font-semibold text-ink hover:bg-paper">
          <Download size={14} /> Xuất dữ liệu
        </button>
        <button type="button" onClick={onDeleteAll} className="inline-flex items-center gap-1 rounded-md border border-danger/30 px-2 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10">
          <Trash2 size={14} /> Xoá tất cả
        </button>
      </footer>
    </div>
  );
}

function ActionProposalCard({ proposal, onConfirm, onCancel, busy }) {
  if (!proposal || proposal.resolved) return null;
  const label =
    proposal.actionType === 'update_task_status'
      ? `Đánh dấu task này là "${proposal.payload?.status}"?`
      : proposal.actionType === 'open_reflection'
        ? 'Mở trang phản tư tuần này?'
        : 'Xác nhận hành động này?';
  return (
    <div className="mt-2 rounded-lg border border-accent/30 bg-accent-soft p-3 text-sm text-ink">
      <p className="font-semibold">{label}</p>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onConfirm}
          className="inline-flex items-center gap-1 rounded-md bg-accent px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
        >
          <Check size={13} /> Xác nhận
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs font-semibold text-ink-secondary disabled:opacity-50"
        >
          <XCircle size={13} /> Huỷ
        </button>
      </div>
    </div>
  );
}

export default function CursusChat({ user }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [value, setValue] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [briefing, setBriefing] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [openCitation, setOpenCitation] = useState(null);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [actioningId, setActioningId] = useState(null);
  const briefingCheckedRef = useRef(false);

  useEffect(() => {
    if (!open || briefingCheckedRef.current) return;
    briefingCheckedRef.current = true;
    getCursusBriefing()
      .then((res) => { if (res.show) setBriefing(res); })
      .catch(() => {});
  }, [open]);

  const dismissBriefing = async (snoozeDays) => {
    setBriefing(null);
    try {
      await dismissCursusBriefing(snoozeDays);
    } catch {
      /* best-effort — the bubble is already hidden client-side */
    }
  };

  const openHistory = async () => {
    setHistoryOpen(true);
    try {
      const res = await getCursusConversations();
      setConversations(res.items || []);
    } catch {
      setConversations([]);
    }
  };

  const selectConversation = async (id) => {
    try {
      const res = await getCursusConversationMessages(id);
      setMessages((res.messages || []).map((m) => ({ role: m.role, text: m.content, citations: m.citations || [] })));
      setConversationId(id);
      setHistoryOpen(false);
    } catch {
      /* keep current view if the conversation failed to load */
    }
  };

  const handleExport = async () => {
    try {
      const data = await exportCursusHistory();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'cursus-chat-history.json';
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      /* export failure is non-critical, no history is lost */
    }
  };

  const handleDeleteAll = async () => {
    setConfirmDeleteAll(false);
    try {
      await deleteCursusHistory();
    } finally {
      setConversations([]);
      setMessages([]);
      setConversationId(null);
      setHistoryOpen(false);
    }
  };

  const resolveProposal = (index, patch) => {
    setMessages((items) => items.map((item, i) => (i === index ? { ...item, actionProposal: { ...item.actionProposal, ...patch } } : item)));
  };

  const handleConfirmAction = async (index, proposal) => {
    setActioningId(proposal.id);
    try {
      const res = await confirmCursusAction(proposal.id);
      resolveProposal(index, { resolved: true });
      if (res.navigateTo) {
        setOpen(false);
        navigate(res.navigateTo);
      }
    } catch {
      resolveProposal(index, { resolved: true, failed: true });
    } finally {
      setActioningId(null);
    }
  };

  const handleCancelAction = async (index, proposal) => {
    setActioningId(proposal.id);
    try {
      await cancelCursusAction(proposal.id);
    } finally {
      resolveProposal(index, { resolved: true });
      setActioningId(null);
    }
  };

  if (user?.role !== 'student') return null;

  const send = async (event) => {
    event.preventDefault();
    sendMessage(value);
  };

  const sendMessage = async (rawText) => {
    const text = rawText.trim();
    if (!text || loading) return;
    setValue('');
    setMessages((items) => [...items, { role: 'user', text }, { role: 'assistant', text: '', citations: [] }]);
    setLoading(true);
    try {
      await streamCursusChat({
        message: text,
        conversationId,
        onEvent: (type, data) => {
          if (type === 'meta') setConversationId(data.conversationId);
          if (type === 'delta') setMessages((items) => items.map((item, i) => (i === items.length - 1 ? { ...item, text: item.text + data.text } : item)));
          if (type === 'citation') setMessages((items) => items.map((item, i) => (i === items.length - 1 ? { ...item, citations: data.items } : item)));
          if (type === 'action_proposal') setMessages((items) => items.map((item, i) => (i === items.length - 1 ? { ...item, actionProposal: { ...data, resolved: false } } : item)));
          if (type === 'error') setMessages((items) => items.map((item, i) => (i === items.length - 1 ? { ...item, text: messageForErrorCode(data.code) } : item)));
        },
      });
    } catch {
      // streamCursusChat itself threw -- the backend was never reached at
      // all (network down, CORS, DNS), so no 'error' SSE event ever fired.
      setMessages((items) => items.map((item, i) => (i === items.length - 1 ? { ...item, text: messageForErrorCode('NETWORK_ERROR') } : item)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {!open && (
        <button
          aria-label="Mở Cursus"
          onClick={() => setOpen(true)}
          style={{ background: HEADER_GRADIENT }}
          className="fixed bottom-5 right-5 z-[90] flex h-14 w-14 items-center justify-center rounded-full text-white shadow-lg transition-transform hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          <Bot size={24} />
        </button>
      )}
      {open && (
        <aside
          aria-label="Cursus chat"
          className="fixed bottom-5 right-5 z-[100] flex h-[min(640px,80vh)] w-[calc(100vw-2.5rem)] max-w-[400px] flex-col overflow-hidden rounded-2xl border border-border bg-paper shadow-2xl"
        >
          <header style={{ background: HEADER_GRADIENT }} className="flex items-center justify-between px-5 py-4 text-white">
            <div className="flex items-center gap-3">
              <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/20">
                <Bot size={20} />
                <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-400" />
              </div>
              <div>
                <h2 className="flex items-center gap-1.5 font-serif text-base font-semibold leading-tight">
                  Cursus <Sparkles size={14} className="text-white/80" />
                </h2>
                <p className="text-xs text-white/80">Trợ lý học tập có nguồn</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button aria-label="Lịch sử trò chuyện" onClick={openHistory} className="text-white/85 hover:text-white">
                <History size={18} />
              </button>
              <button aria-label="Đóng Cursus" onClick={() => setOpen(false)} className="text-white/85 hover:text-white">
                <X size={20} />
              </button>
            </div>
          </header>
          <main className="flex-1 space-y-4 overflow-y-auto bg-surface p-5">
            {messages.length === 0 && (
              <WelcomeCard briefing={briefing} onDismissBriefing={dismissBriefing} onPickReply={sendMessage} disabled={loading} />
            )}
            {messages.map((item, index) => (
              <article
                key={index}
                className={
                  item.role === 'user'
                    ? 'ml-8 rounded-2xl rounded-br-sm bg-accent-soft p-3 text-sm text-ink'
                    : 'mr-4 rounded-2xl rounded-bl-sm border border-border bg-paper p-3 text-sm text-ink shadow-sm'
                }
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.text || 'Đang soạn câu trả lời…'}</ReactMarkdown>
                {item.citations?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2 border-t border-border pt-2">
                    {item.citations.map((citation) => (
                      <CitationChip key={citation.id} citation={citation} onOpen={setOpenCitation} lang="vi" />
                    ))}
                  </div>
                )}
                {item.actionProposal && !item.actionProposal.resolved && (
                  <ActionProposalCard
                    proposal={item.actionProposal}
                    busy={actioningId === item.actionProposal.id}
                    onConfirm={() => handleConfirmAction(index, item.actionProposal)}
                    onCancel={() => handleCancelAction(index, item.actionProposal)}
                  />
                )}
              </article>
            ))}
          </main>
          <form onSubmit={send} className="border-t border-border bg-paper p-3">
            <div className="flex items-end gap-2 rounded-full border border-border bg-surface px-4 py-2 focus-within:ring-2 focus-within:ring-accent">
              <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(value);
                  }
                }}
                placeholder="Hỏi Cursus…"
                rows={1}
                className="max-h-24 min-h-[24px] flex-1 resize-none border-0 bg-transparent py-1 text-sm text-ink placeholder:text-ink-secondary focus:outline-none focus:ring-0"
              />
              <button
                type="submit"
                aria-label="Gửi"
                disabled={loading || !value.trim()}
                style={{ background: HEADER_GRADIENT }}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white disabled:opacity-40"
              >
                <Send size={14} />
              </button>
            </div>
            <p className="mt-1.5 text-center text-[11px] text-ink-secondary">
              Cursus có thể nhầm; hãy kiểm tra lại thông tin quan trọng.
            </p>
          </form>
          {historyOpen && (
            <ChatHistorySidebar
              conversations={conversations}
              activeId={conversationId}
              onSelect={selectConversation}
              onExport={handleExport}
              onDeleteAll={() => setConfirmDeleteAll(true)}
              onClose={() => setHistoryOpen(false)}
            />
          )}
        </aside>
      )}
      {openCitation && <SourceDrawer citation={openCitation} onClose={() => setOpenCitation(null)} lang="vi" />}
      <ConfirmDialog
        open={confirmDeleteAll}
        title="Xoá toàn bộ lịch sử trò chuyện?"
        message="Hành động này không thể hoàn tác."
        confirmLabel="Xoá tất cả"
        cancelLabel="Huỷ"
        danger
        onConfirm={handleDeleteAll}
        onCancel={() => setConfirmDeleteAll(false)}
      />
    </>
  );
}
