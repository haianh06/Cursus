import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Send,
  ShieldAlert,
  Lightbulb,
  HelpCircle,
  Cpu,
  ThumbsUp,
  ThumbsDown,
  ClipboardList,
} from 'lucide-react';
import CursusMascot from '../shared/CursusMascot';
import Skeleton from '../shared/Skeleton';
import { CitationChip } from '../shared/SourceDrawer';
import { askQuestion } from '../../lib/api';

/**
 * Cursus Assistant inside an authenticated Student page.
 *
 * Distinct from `CuriChatLauncher`, which is the public marketing widget with
 * canned copy: this one calls the real `POST /qa` pipeline
 * (guardrail → chat-intent → FAQ → retrieval → answer) and renders whatever
 * the backend actually decided, including:
 *
 *  - grounded answers with clickable citations into the real syllabus,
 *  - a guardrail block that redirects to concept + Socratic question + an
 *    empty template rather than dead-ending,
 *  - an honest engine label, so a deterministic/templated answer is never
 *    dressed up as a live LLM response.
 */
const SUGGESTED = [
  'Điều kiện qua môn SSA101 là gì?',
  'Dự án SSA101 gồm bao nhiêu phần?',
  'Em nên bắt đầu phân tích stakeholder từ đâu?',
];

function EngineLabel({ engine, mode, lang }) {
  const isLlm = engine === 'llm';
  const text = isLlm
    ? lang === 'vi'
      ? 'Trả lời bằng mô hình ngôn ngữ'
      : 'Answered by a language model'
    : lang === 'vi'
      ? 'Trả lời tiền định (không gọi LLM)'
      : 'Deterministic answer (no LLM call)';
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full text-fg-muted bg-surface-elevated"
      title={`mode=${mode}`}
    >
      <Cpu size={9} aria-hidden="true" />
      {text}
    </span>
  );
}

function GuardrailGuidance({ guidance, lang }) {
  if (!guidance || Object.keys(guidance).length === 0) return null;
  return (
    <div className="mt-3 space-y-3">
      {guidance.concept && (
        <div className="rounded-lg p-3 bg-accent-soft border border-line">
          <p className="text-[10px] font-bold uppercase tracking-widest mb-1 flex items-center gap-1 text-ai-insight">
            <Lightbulb size={10} /> {lang === 'vi' ? 'Khái niệm' : 'Concept'}
          </p>
          <p className="text-[12px] leading-relaxed text-fg-secondary">
            {guidance.concept}
          </p>
        </div>
      )}

      {Array.isArray(guidance.steps) && guidance.steps.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5 text-fg-muted">
            {lang === 'vi' ? 'Hướng dẫn từng bước' : 'Step by step'}
          </p>
          <ol className="space-y-1 list-none">
            {guidance.steps.map((step) => (
              <li key={step} className="text-[12px] leading-relaxed text-fg-secondary">
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      {Array.isArray(guidance.socraticQuestions) && guidance.socraticQuestions.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5 flex items-center gap-1 text-fg-muted">
            <HelpCircle size={10} /> {lang === 'vi' ? 'Câu hỏi để bạn tự bật ý' : 'Questions for you'}
          </p>
          <ul className="space-y-1">
            {guidance.socraticQuestions.map((question) => (
              <li
                key={question}
                className="text-[12px] leading-relaxed pl-3 border-l-2 text-fg-secondary border-ai-insight"
              >
                {question}
              </li>
            ))}
          </ul>
        </div>
      )}

      {guidance.template && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5 flex items-center gap-1 text-fg-muted">
            <ClipboardList size={10} /> {lang === 'vi' ? 'Khung trống để bạn tự điền' : 'Empty template'}
          </p>
          <pre
            className="text-[12px] leading-relaxed whitespace-pre-wrap rounded-lg p-3 font-sans text-fg-secondary bg-surface-elevated border border-dashed border-line-strong"
          >
            {guidance.template}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function CuriContextPanel({
  subjectCode = 'SSA101',
  contextTask = null,
  onOpenCitation,
  lang = 'vi',
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState({});
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  const send = useCallback(
    async (rawQuestion) => {
      const question = (rawQuestion ?? '').trim();
      if (!question || loading) return;
      setError(null);
      setInput('');
      const id = `m${Date.now()}`;
      setMessages((prev) => [...prev, { id, role: 'user', text: question }]);
      setLoading(true);
      try {
        // Task context is prepended so retrieval is scoped to what the
        // student is actually doing right now.
        const scoped = contextTask ? `[${contextTask.title}] ${question}` : question;
        const result = await askQuestion({ subjectCode, question: scoped });
        setMessages((prev) => [...prev, { id: `${id}-a`, role: 'assistant', ...result }]);
      } catch (err) {
        setError(err);
        setMessages((prev) => [
          ...prev,
          {
            id: `${id}-e`,
            role: 'assistant',
            failed: true,
            answer:
              lang === 'vi'
                ? 'Không hỏi được Trợ lý Cursus lúc này. Kiểm tra kết nối rồi thử lại — câu hỏi của bạn vẫn còn ở ô nhập.'
                : 'Could not reach Cursus Assistant. Check your connection and try again.',
          },
        ]);
        setInput(question);
      } finally {
        setLoading(false);
      }
    },
    [contextTask, lang, loading, subjectCode],
  );

  return (
    <section
      aria-label={lang === 'vi' ? 'Hỏi Trợ lý Cursus theo ngữ cảnh' : 'Ask Cursus Assistant in context'}
      className="card flex flex-col overflow-hidden min-h-[380px] max-h-[720px]"
    >
      <header className="flex items-center gap-2 px-4 py-3 border-b shrink-0 border-line">
        <CursusMascot size={22} />
        <div className="min-w-0 flex-1">
          <h2 className="text-[14px] font-bold font-display text-fg">
            {lang === 'vi' ? 'Hỏi Trợ lý Cursus' : 'Ask Cursus Assistant'}
          </h2>
          <p className="text-[11px] truncate text-fg-muted">
            {contextTask
              ? `${lang === 'vi' ? 'Ngữ cảnh' : 'Context'}: ${contextTask.title}`
              : `${lang === 'vi' ? 'Ngữ cảnh môn' : 'Course context'}: ${subjectCode}`}
          </p>
        </div>
      </header>

      <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !loading && (
          <div className="text-center py-6">
            <p className="text-[13px] mb-3 text-fg-secondary">
              {lang === 'vi'
                ? 'Hỏi về nội dung môn học — Trợ lý Cursus trả lời kèm nguồn, và sẽ không viết hộ phần bài tính điểm.'
                : 'Ask about the course — Cursus Assistant answers with sources and will not write graded work for you.'}
            </p>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {SUGGESTED.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => send(item)}
                  className="text-[11px] px-3 min-h-9 inline-flex items-center rounded-full border cursor-pointer transition-colors duration-200 border-line text-fg-secondary bg-surface-elevated hover:border-accent hover:text-accent-text-safe outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) =>
          message.role === 'user' ? (
            <div key={message.id} className="flex justify-end">
              <p className="text-[13px] px-3.5 py-2 rounded-2xl rounded-br-sm max-w-[85%] bg-accent-cta text-white shadow-elevation-1">
                {message.text}
              </p>
            </div>
          ) : (
            <div key={message.id} className="flex flex-col gap-2">
              {message.blocked && (
                <span
                  className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-warning-soft text-warning"
                >
                  <ShieldAlert size={10} />
                  {lang === 'vi'
                    ? 'Hướng dẫn học tập — không làm hộ'
                    : 'Study guidance — not doing it for you'}
                </span>
              )}
              {message.blockReason === 'out_of_scope' && !message.blocked && (
                <span
                  className="self-start inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-surface-elevated text-fg-muted"
                >
                  {lang === 'vi' ? 'Ngoài phạm vi tài liệu môn' : 'Outside course sources'}
                </span>
              )}

              <div
                className={`text-[13px] leading-relaxed px-3.5 py-3 rounded-2xl rounded-bl-sm whitespace-pre-line bg-surface-elevated border border-line ${
                  message.failed ? 'text-danger' : 'text-fg'
                }`}
              >
                {message.answer}
                <GuardrailGuidance guidance={message.guidance} lang={lang} />
              </div>

              {message.citations?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {message.citations.map((citation) => (
                    <CitationChip
                      key={citation.chunkId}
                      citation={citation}
                      onOpen={onOpenCitation}
                      lang={lang}
                    />
                  ))}
                </div>
              )}

              {message.alternatives?.length > 0 && (
                <ul className="space-y-0.5 pl-1">
                  {message.alternatives.map((item) => (
                    <li key={item} className="text-[11px] text-fg-muted">
                      • {item}
                    </li>
                  ))}
                </ul>
              )}

              {message.followUpQuestions?.length > 0 && !message.failed && (
                <div className="flex flex-wrap gap-1.5">
                  {message.followUpQuestions.slice(0, 3).map((question) => (
                    <button
                      key={question}
                      type="button"
                      onClick={() => send(question)}
                      className="text-[11px] px-3 min-h-9 inline-flex items-center rounded-full border border-line bg-transparent text-accent-text-safe cursor-pointer transition-colors duration-200 hover:bg-accent-soft hover:border-accent outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              )}

              {!message.failed && (
                <div className="flex items-center gap-2">
                  <EngineLabel engine={message.engine} mode={message.mode} lang={lang} />
                  <span className="flex items-center gap-1">
                    <button
                      type="button"
                      aria-label={lang === 'vi' ? 'Hữu ích' : 'Helpful'}
                      aria-pressed={feedback[message.id] === 'up'}
                      className="btn-ghost w-8 h-8 inline-flex items-center justify-center rounded-lg cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      style={{
                        color: feedback[message.id] === 'up' ? 'var(--success)' : 'var(--text-muted)',
                      }}
                      onClick={() => setFeedback((prev) => ({ ...prev, [message.id]: 'up' }))}
                    >
                      <ThumbsUp size={11} />
                    </button>
                    <button
                      type="button"
                      aria-label={lang === 'vi' ? 'Chưa hữu ích' : 'Not helpful'}
                      aria-pressed={feedback[message.id] === 'down'}
                      className="btn-ghost w-8 h-8 inline-flex items-center justify-center rounded-lg cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      style={{
                        color: feedback[message.id] === 'down' ? 'var(--danger)' : 'var(--text-muted)',
                      }}
                      onClick={() => setFeedback((prev) => ({ ...prev, [message.id]: 'down' }))}
                    >
                      <ThumbsDown size={11} />
                    </button>
                  </span>
                </div>
              )}
            </div>
          ),
        )}

        {loading && (
          <div className="space-y-2">
            <Skeleton className="h-4 w-4/5 rounded" />
            <Skeleton className="h-4 w-3/5 rounded" />
          </div>
        )}
      </div>

      <form
        className="flex items-center gap-2 p-3 border-t shrink-0 border-line"
        onSubmit={(event) => {
          event.preventDefault();
          send(input);
        }}
      >
        <label htmlFor="curi-input" className="sr-only">
          {lang === 'vi' ? 'Câu hỏi cho Trợ lý Cursus' : 'Question for Cursus Assistant'}
        </label>
        <input
          id="curi-input"
          className="input text-[13px] flex-1 h-10"
          placeholder={lang === 'vi' ? 'Hỏi về nội dung môn học…' : 'Ask about the course…'}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="btn btn-accent w-10 h-10 shrink-0 rounded-lg cursor-pointer disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent"
          disabled={!input.trim() || loading}
          aria-label={lang === 'vi' ? 'Gửi' : 'Send'}
        >
          <Send size={14} />
        </button>
      </form>

      {error && (
        <p className="px-3 pb-3 text-[11px] text-danger">
          {error.message}
        </p>
      )}
    </section>
  );
}
