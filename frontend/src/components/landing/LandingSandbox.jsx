import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { Send, FileText, Ban, Bot, AlertTriangle, Sparkles, RotateCcw } from 'lucide-react';

export default function LandingSandbox() {
  const { t, lang } = useLanguage();
  const sm = (key) => t(`landing.sandboxMock.${key}`);

  const SUGGESTED_PROMPTS = [
    { id: 'p1', text: t('landing.presetPassQuestion'), type: 'knowledge' },
    { id: 'p2', text: t('landing.presetGuardrailQuestion'), type: 'guardrail' },
    { id: 'p3', text: t('landing.presetOutOfScopeQuestion'), type: 'out-of-scope' }
  ];

  const initialMessages = () => [
    { id: 'welcome', role: 'assistant', text: t('landing.sandboxWelcomeText') },
    { id: 'seed-q', role: 'user', text: t('landing.presetPassQuestion') },
    { id: 'seed-a', role: 'assistant', text: t('landing.presetPassAnswer'), citation: t('landing.presetPassSource') }
  ];

  // Pre-seeded with one real exchange so the sandbox reads as an actual
  // conversation on load, not an empty composer waiting for input.
  const [messages, setMessages] = useState(initialMessages);
  const [isTyping, setIsTyping] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const chatEndRef = useRef(null);
  const prevMessageCount = useRef(messages.length);
  const prevIsTyping = useRef(isTyping);
  // As long as the visitor hasn't sent anything of their own, the seeded
  // demo exchange is still "pristine" — re-translate it in place on a
  // locale switch so VI/EN text never mixes on screen. Once they interact,
  // this stops firing so their real conversation is never rewritten.
  const isPristine = useRef(true);

  useEffect(() => {
    if (isPristine.current) {
      setMessages(initialMessages());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-seed on a language change
  }, [lang]);

  useEffect(() => {
    // Only scroll when a message was actually *added*, or typing just
    // started — never on mount. A plain "first render" boolean flag isn't
    // enough: React StrictMode's dev-only double-invoke of effects re-runs
    // this after the flag is already flipped. Comparing against the
    // previous count/flag is stable across that double-invoke because
    // neither value actually changes between the two runs.
    const grew = messages.length > prevMessageCount.current;
    const startedTyping = isTyping && !prevIsTyping.current;
    prevMessageCount.current = messages.length;
    prevIsTyping.current = isTyping;
    if (grew || startedTyping) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messages, isTyping]);

  const handleSend = (text, type = 'general') => {
    if (!text.trim()) return;

    isPristine.current = false;
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text }]);
    setInputValue('');
    setIsTyping(true);

    setTimeout(() => {
      setIsTyping(false);

      let reply;
      if (type === 'knowledge' || text.toLowerCase().includes('grade') || text.toLowerCase().includes('điều kiện qua môn ssa')) {
        reply = {
          role: 'assistant',
          text: t('landing.presetPassAnswer'),
          citation: t('landing.presetPassSource')
        };
      } else if (type === 'guardrail' || text.toLowerCase().includes('assignment') || text.toLowerCase().includes('viết hộ')) {
        reply = {
          role: 'assistant',
          text: t('landing.presetGuardrailAnswer'),
          guardrail: true
        };
      } else {
        reply = {
          role: 'assistant',
          text: t('landing.unsupportedAnswer'),
          outOfScope: true
        };
      }

      setMessages(prev => [...prev, { id: Date.now().toString(), ...reply }]);
    }, 1200);
  };

  const handleReset = () => {
    isPristine.current = true;
    setIsTyping(false);
    setInputValue('');
    setMessages(initialMessages());
  };

  return (
    <section id="try-it" className="py-24 lg:py-32 px-6 lg:px-10 bg-landing-surface-elevated relative z-10 border-t border-landing-border">
      <div className="max-w-[1280px] mx-auto flex flex-col lg:flex-row items-start gap-12 lg:gap-20">

        {/* Left Copy */}
        <div className="flex-1 text-left max-w-xl lg:pt-4">
          <span className="text-xs font-medium text-landing-text-muted mb-3 block">
            {lang === 'vi' ? 'Trải nghiệm' : 'Try it'}
          </span>
          <h2 className="landing-section-heading text-2xl md:text-4xl font-display text-landing-text mb-6">
            {lang === 'vi' ? 'Hỏi thử Trợ lý Cursus ngay bây giờ' : 'Ask Cursus Assistant anything'}
          </h2>
          <p className="text-landing-text-secondary text-base md:text-lg mb-8 leading-relaxed">
            {lang === 'vi'
              ? 'Trải nghiệm cách Cursus trả lời dựa trên syllabus thật của môn SSA101, và cách guardrail liêm chính học thuật hoạt động.'
              : 'Experience how Cursus answers based on the real SSA101 syllabus, and how the academic integrity guardrail works.'}
          </p>
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-landing-text-secondary text-sm">
              <FileText size={15} className="text-landing-text-muted shrink-0" />
              {lang === 'vi' ? 'Trả lời có trích dẫn nguồn rõ ràng' : 'Answers with clear citations'}
            </div>
            <div className="flex items-center gap-3 text-landing-text-secondary text-sm">
              <Ban size={15} className="text-landing-text-muted shrink-0" />
              {lang === 'vi' ? 'Chặn yêu cầu giải bài tập tính điểm' : 'Blocks graded assignment requests'}
            </div>
          </div>
        </div>

        {/* Right Chat UI */}
        <div className="w-full lg:w-[560px] bg-landing-surface border border-landing-border rounded-2xl shadow-landing-lg flex flex-col h-[520px] overflow-hidden">

          {/* Header */}
          <div className="px-5 py-3.5 border-b border-landing-border bg-landing-surface-elevated flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-landing-surface-muted border border-landing-border flex items-center justify-center text-landing-text-secondary">
                <Bot size={16} />
              </div>
              <div className="text-left">
                <div className="text-sm font-semibold text-landing-text leading-tight">{lang === 'vi' ? 'Trợ lý Cursus' : 'Cursus Assistant'}</div>
                <div className="text-[11px] text-landing-text-muted mt-0.5">
                  {sm('activeDemoData')}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1.5 text-[11px] font-medium text-landing-text-muted hover:text-landing-text transition-colors px-2 py-1.5 rounded-lg hover:bg-landing-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent"
              title={lang === 'vi' ? 'Bắt đầu lại cuộc trò chuyện' : 'Restart the conversation'}
            >
              <RotateCcw size={13} />
              {lang === 'vi' ? 'Bắt đầu lại' : 'Restart'}
            </button>
          </div>

          {/* Chat Body */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-landing-bg" aria-live="polite">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {msg.guardrail && (
                  <div className="mb-2 px-3 py-1.5 rounded-lg bg-landing-danger-soft border border-landing-danger/30 flex items-center gap-2 text-landing-danger max-w-[85%]">
                    <Ban size={13} className="shrink-0" />
                    <span className="text-[11px] font-semibold uppercase tracking-wide">{sm('blockedRequestLabel')}</span>
                  </div>
                )}

                <div
                  className={`
                    max-w-[85%] p-3.5 text-sm leading-relaxed rounded-2xl
                    ${msg.role === 'user'
                      ? 'bg-landing-surface-inverse text-landing-text-inverse rounded-br-none'
                      : 'bg-landing-surface border border-landing-border text-landing-text rounded-bl-none shadow-landing-sm'}
                  `}
                >
                  {msg.outOfScope && (
                    <div className="flex items-center gap-2 mb-2 pb-2 border-b border-landing-border text-landing-warning font-semibold text-[11px] uppercase tracking-wide">
                      <AlertTriangle size={13} /> {sm('outOfScopeLabel')}
                    </div>
                  )}
                  {msg.text}

                  {msg.citation && (
                    <div className="mt-3 pt-2.5 border-t border-landing-border flex items-center gap-2 text-xs text-landing-accent-hover font-semibold cursor-pointer hover:underline transition-colors">
                      <FileText size={13} /> {msg.citation}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex items-center gap-2 p-3 bg-landing-surface border border-landing-border shadow-landing-sm rounded-2xl rounded-bl-none w-fit">
                <Sparkles size={14} className="text-landing-accent animate-pulse" />
                <span className="text-xs font-medium text-landing-text-secondary mr-1">{sm('thinking')}</span>
                <div className="flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-landing-text-muted animate-pulse" />
                  <span className="w-1 h-1 rounded-full bg-landing-text-muted animate-pulse delay-75" />
                  <span className="w-1 h-1 rounded-full bg-landing-text-muted animate-pulse delay-150" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Composer */}
          <div className="p-3.5 bg-landing-surface border-t border-landing-border shrink-0 flex flex-col gap-2.5">
            {/* Fixed basis + truncate: each chip occupies the same footprint
                regardless of VI/EN sentence length, so the wrap point is
                identical between locales — only the visible text differs,
                never the layout. Full text is still available via title. */}
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_PROMPTS.map(p => (
                <button
                  key={p.id}
                  onClick={() => handleSend(p.text, p.type)}
                  disabled={isTyping}
                  title={p.text}
                  className="flex-none basis-[46%] sm:basis-[220px] max-w-full truncate text-xs font-medium px-3 py-1.5 bg-landing-surface border border-landing-border rounded-lg text-landing-text-secondary hover:text-landing-text hover:bg-landing-surface-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent text-left disabled:opacity-50"
                >
                  {p.text}
                </button>
              ))}
            </div>

            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(inputValue); }}
              className="flex items-center gap-2 relative"
            >
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={lang === 'vi' ? 'Hỏi điều gì đó...' : 'Ask something...'}
                className="flex-1 bg-landing-surface-muted border border-landing-border rounded-xl pl-4 pr-11 py-3 text-sm text-landing-text placeholder:text-landing-text-muted focus:outline-none focus:border-landing-accent focus:ring-1 focus:ring-landing-accent transition-all"
                disabled={isTyping}
              />
              <button
                type="submit"
                disabled={!inputValue.trim() || isTyping}
                aria-label={lang === 'vi' ? 'Gửi câu hỏi' : 'Send message'}
                className="absolute right-1.5 p-1.5 rounded-lg text-landing-text-inverse bg-landing-surface-inverse hover:opacity-90 disabled:opacity-40 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-landing-accent"
              >
                <Send size={16} />
              </button>
            </form>
          </div>

        </div>
      </div>
    </section>
  );
}
