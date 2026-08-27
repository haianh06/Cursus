import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, Send, X, History, Download, Trash2, Check, XCircle } from 'lucide-react';
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

/** Frequency-capped greeting shown once per open panel session — the server
 * (ChatBriefingImpression) decides whether it's actually due; this is just
 * the dismiss/snooze UI on top of that decision. */
function BriefingBubble({ briefing, onDismiss }) {
  if (!briefing) return null;
  return (
    <div className="rounded-lg border border-accent/30 bg-accent-soft p-3 text-sm text-ink">
      <p>{briefing.message}</p>
      <div className="mt-2 flex gap-3 text-xs font-semibold">
        <button type="button" onClick={() => onDismiss(1)} className="text-accent hover:underline">
          Đã hiểu
        </button>
        <button type="button" onClick={() => onDismiss(7)} className="text-ink-secondary hover:underline">
          Nhắc lại sau
        </button>
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
    const text = value.trim();
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
          if (type === 'error') setMessages((items) => items.map((item, i) => (i === items.length - 1 ? { ...item, text: 'Cursus đang tạm thời không phản hồi. Hãy thử lại sau.' } : item)));
        },
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button aria-label="Mở Cursus" onClick={() => setOpen(true)} className="fixed bottom-5 right-5 z-[90] flex h-12 items-center gap-2 rounded-lg border border-accent bg-surface px-3 text-sm font-semibold text-fg shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">
        <Bot size={18} /> Cursus
      </button>
      {open && (
        <aside aria-label="Cursus chat" className="fixed inset-y-0 right-0 z-[100] flex w-full max-w-[440px] flex-col border-l border-border bg-paper shadow-xl">
          <header className="relative flex items-center justify-between border-b border-border bg-surface px-5 py-4">
            <div>
              <h2 className="font-serif text-lg text-ink">Cursus</h2>
              <p className="text-xs text-ink-secondary">Trợ lý học tập có nguồn</p>
            </div>
            <div className="flex items-center gap-3">
              <button aria-label="Lịch sử trò chuyện" onClick={openHistory}>
                <History size={18} />
              </button>
              <button aria-label="Đóng Cursus" onClick={() => setOpen(false)}>
                <X size={20} />
              </button>
            </div>
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
          </header>
          <main className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.length === 0 && (
              <BriefingBubble briefing={briefing} onDismiss={dismissBriefing} />
            )}
            {messages.length === 0 && !briefing && (
              <p className="rounded-lg border border-border bg-surface p-4 text-sm text-ink-secondary">
                Bạn muốn biết gì về môn học, kế hoạch hoặc cách dùng Cursus?
              </p>
            )}
            {messages.map((item, index) => (
              <article key={index} className={item.role === 'user' ? 'ml-8 rounded-lg bg-accent-soft p-3 text-sm text-ink' : 'mr-4 rounded-lg border border-border bg-surface p-3 text-sm text-ink'}>
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
          <form onSubmit={send} className="border-t border-border bg-surface p-4">
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Hỏi Cursus…"
              className="min-h-20 w-full resize-none rounded-md border border-border bg-paper p-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <button disabled={loading} className="mt-2 inline-flex items-center gap-2 rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
              <Send size={15} /> Gửi
            </button>
          </form>
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
