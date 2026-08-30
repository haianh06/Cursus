import React, { useEffect, useRef, useState } from 'react';
import { Send, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useLanguage } from '../../context/LanguageContext';
import { useNavigate } from 'react-router-dom';
import CursusMascot from '../shared/CursusMascot';
import { askLandingChat, userFacingApiError } from '../../lib/api';

// Same gradient as CursusChat.jsx's HEADER_GRADIENT -- both widgets share
// one brand treatment for the header/send-button/avatar-ring chrome, kept
// as a literal duplicate (not a shared import) because CursusChat.jsx lives
// under components/student/ and this one must not depend on a logged-in-
// only module.
const HEADER_GRADIENT = 'linear-gradient(135deg, var(--accent-cta-bg) 0%, var(--accent-cta-bg-hover) 100%)';

function QuickReplies({ onPick, disabled, t }) {
  const prompts = [
    t('landing.chatWidget.quickReply1'),
    t('landing.chatWidget.quickReply2'),
    t('landing.chatWidget.quickReply3'),
    t('landing.chatWidget.quickReply4'),
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {prompts.map((text) => (
        <button
          key={text}
          type="button"
          disabled={disabled}
          onClick={() => onPick(text)}
          className="rounded-full border border-landing-accent/30 bg-landing-accent-soft px-3 py-1.5 text-left text-xs font-medium text-landing-accent hover:bg-landing-accent/10 disabled:opacity-50 cursor-pointer"
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/** Landing-page chat bubble (bottom-right, no auth) -- pre-login product
 * demo for anonymous visitors, same UX pattern as Intercom/Drift's
 * marketing-site chat: collapsed launcher by default, opens a small panel,
 * never requires signup to ask a question. Calls the scoped public
 * `/public/landing-chat` endpoint (marketing Q&A only, zero student-data
 * access -- see landing_chat_service.py's own docstring for why).
 *
 * Exposed imperatively via `id="landing-chat-widget"` + a custom
 * `landing-chat:open` window event so the navbar's "Trải nghiệm" nav item
 * (which used to point at a `#try-it` anchor with no matching section --
 * a dead link) can open this panel instead, without prop-drilling a toggle
 * function down through LandingNavbar -> LandingPage -> here. */
export default function LandingChatWidget() {
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [showGreeting, setShowGreeting] = useState(false);
  const [popCount, setPopCount] = useState(0);
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // A brief invitation label next to the launcher on first load (Intercom/
  // Crisp/Drift convention) -- an unlabeled floating icon reads as "what is
  // this" to a first-time visitor; the label answers that without forcing
  // the panel open. Shows once per tab session, dismissed by opening the
  // panel, closing it, or scrolling.
  useEffect(() => {
    const timer = setTimeout(() => setShowGreeting(true), 2500);
    return () => clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (!showGreeting) return undefined;
    const dismiss = () => setShowGreeting(false);
    window.addEventListener('scroll', dismiss, { passive: true, once: true });
    return () => window.removeEventListener('scroll', dismiss);
  }, [showGreeting]);

  useEffect(() => {
    const onOpenEvent = () => setOpen(true);
    window.addEventListener('landing-chat:open', onOpenEvent);
    return () => window.removeEventListener('landing-chat:open', onOpenEvent);
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeydown = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    const onClickOutside = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) setOpen(false);
    };
    window.addEventListener('keydown', onKeydown);
    document.addEventListener('mousedown', onClickOutside);
    return () => {
      window.removeEventListener('keydown', onKeydown);
      document.removeEventListener('mousedown', onClickOutside);
    };
  }, [open]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  const sendText = async (question) => {
    if (!question || sending) return;
    setInput('');
    setError('');
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setSending(true);
    try {
      const result = await askLandingChat(question);
      setMessages((prev) => [...prev, { role: 'assistant', text: result.answer }]);
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('landing.chatWidget.errorFallback'));
    } finally {
      setSending(false);
    }
  };

  const send = (e) => {
    e.preventDefault();
    sendText(input.trim());
  };

  return (
    <div className="fixed bottom-5 right-5 z-[1100] flex flex-col items-end gap-3">
      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="false"
          aria-label={t('landing.chatWidget.title')}
          style={{ transformOrigin: 'bottom right' }}
          className="w-[min(360px,calc(100vw-2.5rem))] max-h-[min(560px,calc(100vh-8rem))] flex flex-col overflow-hidden rounded-2xl border border-landing-border bg-landing-surface shadow-landing-lg animate-scale-in"
        >
          <header style={{ background: HEADER_GRADIENT }} className="flex items-center justify-between px-5 py-4 text-white">
            <div className="flex items-center gap-3">
              <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/20">
                <CursusMascot size={36} state={sending ? 'thinking' : 'idle'} />
                <span
                  aria-hidden="true"
                  className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-400"
                />
              </div>
              <div>
                <h2 className="text-base font-semibold leading-tight">{t('landing.chatWidget.title')}</h2>
                <p className="text-xs text-white/80">{t('landing.chatWidget.subtitle')}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={t('landing.chatWidget.closeLabel')}
              className="text-white/85 hover:text-white cursor-pointer"
            >
              <X size={20} />
            </button>
          </header>

          <div ref={listRef} className="flex-1 min-h-[180px] overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="rounded-2xl border border-landing-border bg-landing-surface-muted p-4 text-sm text-landing-text shadow-landing-sm">
                <p>{t('landing.chatWidget.greeting')}</p>
                <div className="mt-3 border-t border-landing-border pt-3">
                  <QuickReplies onPick={sendText} disabled={sending} t={t} />
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {m.role === 'user' ? (
                  <p className="max-w-[85%] whitespace-pre-wrap rounded-xl bg-landing-cta px-3 py-2 text-[13px] leading-relaxed text-landing-cta-fg">
                    {m.text}
                  </p>
                ) : (
                  // Synced with CursusChat.jsx: same `.cursus-chat-markdown`
                  // class + ReactMarkdown wrapping, so an answer with a list
                  // or bold text renders identically in both widgets instead
                  // of showing raw markdown syntax here. Assistant-only --
                  // the user's own typed question needs no markdown parsing.
                  <div className="max-w-[85%] rounded-xl bg-landing-surface-muted px-3 py-2 text-[13px]">
                    <div className="cursus-chat-markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <p className="rounded-xl bg-landing-surface-muted px-3 py-2 text-[13px] text-landing-text-muted">
                  {t('landing.chatWidget.typing')}
                </p>
              </div>
            )}
            {error && (
              <p role="alert" className="text-[12px] text-landing-danger">{error}</p>
            )}
          </div>

          {/* Landing-only CTA -- CursusChat doesn't need this, the visitor
              there is already signed in. Kept as its own strip above the
              input (not merged into it) so the input/send-button pair below
              stays pixel-for-pixel the same markup as CursusChat's. */}
          <div className="border-t border-landing-border px-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/demo/select-role')}
              className="mb-2 w-full rounded-full px-3 py-2 text-[13px] font-semibold text-white hover:opacity-90 transition-opacity cursor-pointer"
              style={{ background: HEADER_GRADIENT }}
            >
              {t('landing.startFreeBtn')}
            </button>
          </div>
          <form onSubmit={send} className="bg-landing-surface p-3">
            <div className="flex items-end gap-2 rounded-full border border-landing-border bg-landing-bg px-4 py-2 focus-within:ring-2 focus-within:ring-landing-accent">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t('landing.chatWidget.inputPlaceholder')}
                maxLength={500}
                disabled={sending}
                className="min-h-[24px] flex-1 border-0 bg-transparent py-1 text-sm text-landing-text placeholder:text-landing-text-muted outline-none focus:ring-0 disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                aria-label={t('landing.chatWidget.sendLabel')}
                style={{ background: HEADER_GRADIENT }}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white disabled:opacity-40 cursor-pointer"
              >
                <Send size={14} />
              </button>
            </div>
            <p className="mt-1.5 text-center text-[11px] text-landing-text-muted">
              {t('landing.chatWidget.disclaimer')}
            </p>
          </form>
        </div>
      )}

      {/* Synced with CursusChat.jsx: the launcher only renders while the
          panel is closed (closing happens via the header's X, same as
          there) instead of also doubling as a floating close button. */}
      {!open && (
        <div className="flex items-center gap-2.5">
          {/* Invitation label -- dismissed the moment the visitor engages
              (opens the panel) or scrolls past it, never re-shows this
              session. Same shape as the launcher button so it reads as one
              control, not a stray tooltip. */}
          {showGreeting && (
            <button
              type="button"
              onClick={() => { setOpen(true); setShowGreeting(false); }}
              style={{ transformOrigin: 'right center' }}
              className="animate-scale-in whitespace-nowrap rounded-full border border-landing-border bg-landing-surface px-4 py-2.5 text-[13px] font-semibold text-landing-text shadow-landing-md hover:border-landing-accent transition-colors cursor-pointer"
            >
              {t('landing.chatWidget.greetingLabel')}
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              setOpen(true);
              setShowGreeting(false);
              setPopCount((c) => c + 1);
            }}
            aria-label={t('landing.chatWidget.openLabel')}
            aria-expanded={false}
            className="group relative flex h-16 w-16 items-center justify-center rounded-full border border-landing-border bg-landing-surface shadow-landing-lg transition-transform hover:scale-105 active:scale-95 bubble-breathe-anim cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent focus-visible:ring-offset-2"
          >
            {/* `key={popCount}` remounts this inner node on every click,
                which is what actually restarts a CSS animation in React --
                re-adding the same class name on an element that already has
                it is a no-op, the animation would only ever play once. This
                is the "phình to rồi ổn định" (swell-then-settle) bounce. */}
            <span key={popCount} className="landing-chat-launcher-pop-anim relative flex h-16 w-16 items-center justify-center">
              <CursusMascot size="launcher" state="idle" />
              {/* Online-status dot -- signals "someone/something is here to
                  answer", the same convention Intercom/Drift/Crisp launchers
                  use, not just a decorative accent. */}
              <span
                aria-hidden="true"
                className="absolute bottom-0.5 right-0.5 h-3.5 w-3.5 rounded-full border-2 border-landing-surface bg-landing-success"
              />
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
