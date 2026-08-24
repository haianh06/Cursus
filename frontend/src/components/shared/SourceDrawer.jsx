import React, { useEffect, useRef, useState } from 'react';
import { BookOpen, FlaskConical, X, AlertTriangle } from 'lucide-react';
import Skeleton from './Skeleton';
import ProvenanceBadge from './ProvenanceBadge';
import { getSourceChunk } from '../../lib/api';

/**
 * Citation contract (Blueprint §4.3): a citation must carry document,
 * section, excerpt and internal chunk id, and clicking it must open the
 * *actual* source text — not a paraphrase.
 *
 * The drawer fetches the chunk from `GET /qa/sources/:chunkId`, but renders
 * immediately from whatever the citation already carried, so the excerpt is
 * on screen before the round-trip finishes.
 */
export function SourceDrawer({ citation, onClose, lang = 'vi' }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const closeRef = useRef(null);
  const panelRef = useRef(null);
  const restoreFocusRef = useRef(null);

  const chunkId = citation?.chunkId;

  useEffect(() => {
    if (!chunkId) return undefined;
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    getSourceChunk(chunkId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [chunkId]);

  useEffect(() => {
    if (!citation) return undefined;
    restoreFocusRef.current = document.activeElement;
    closeRef.current?.focus();

    const selector =
      'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !panelRef.current) return;
      const items = Array.from(panelRef.current.querySelectorAll(selector));
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      if (restoreFocusRef.current instanceof HTMLElement) restoreFocusRef.current.focus();
    };
  }, [citation, onClose]);

  if (!citation) return null;

  const document_ = detail?.document ?? citation.document ?? citation.docTitle ?? citation.sourceLabel;
  const section = detail?.section ?? citation.section;
  const excerpt = detail?.excerpt ?? citation.excerpt;

  return (
    <>
      <div
        className="fixed inset-0 z-[80] bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={lang === 'vi' ? 'Nguồn trích dẫn' : 'Citation source'}
        className="fixed top-0 right-0 bottom-0 z-[85] w-full sm:w-[440px] flex flex-col animate-scale-in border-l bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 h-14 border-b shrink-0 border-line">
          <div className="flex items-center gap-2 min-w-0">
            <BookOpen size={15} className="text-citation" />
            <h2 className="font-display text-sm font-bold truncate text-fg">
              {lang === 'vi' ? 'Nguồn trích dẫn' : 'Citation source'}
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="btn-ghost w-10 h-10 inline-flex items-center justify-center rounded-lg cursor-pointer text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={onClose}
            aria-label={lang === 'vi' ? 'Đóng' : 'Close'}
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-left">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest mb-1 text-fg-muted">
              {lang === 'vi' ? 'Tài liệu' : 'Document'}
            </p>
            <p className="text-sm font-semibold text-fg">
              {document_}
            </p>
            {detail?.version && (
              <p className="mono text-[11px] mt-0.5 text-fg-muted">
                v{detail.version}
              </p>
            )}
          </div>

          {section && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest mb-1 text-fg-muted">
                {lang === 'vi' ? 'Mục' : 'Section'}
              </p>
              <p className="text-sm text-fg-secondary">
                {section}
              </p>
            </div>
          )}

          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5 text-fg-muted">
              {lang === 'vi' ? 'Đoạn trích' : 'Excerpt'}
            </p>
            {loading && !excerpt ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full rounded" />
                <Skeleton className="h-4 w-5/6 rounded" />
                <Skeleton className="h-4 w-2/3 rounded" />
              </div>
            ) : excerpt ? (
              <p
                className="text-[13px] leading-relaxed whitespace-pre-line rounded-lg p-3 text-fg-secondary bg-surface-elevated border border-line"
              >
                {excerpt}
              </p>
            ) : (
              <div className="flex items-start gap-2 rounded-lg p-3 bg-warning-soft border border-line">
                <AlertTriangle size={14} className="mt-0.5 shrink-0 text-warning" />
                <p className="text-[12px] text-fg-secondary">
                  {lang === 'vi'
                    ? 'Không tải được đoạn nguồn này. Đoạn trích có thể đã được cập nhật hoặc không còn trong tài liệu.'
                    : 'Could not load this excerpt. The source may have changed.'}
                </p>
              </div>
            )}
            {failed && excerpt && (
              <p className="text-[11px] mt-1.5 text-fg-muted">
                {lang === 'vi'
                  ? 'Đang hiển thị đoạn trích đã lưu (không kết nối được máy chủ).'
                  : 'Showing cached excerpt (server unreachable).'}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <ProvenanceBadge
              provenance={detail?.provenance ?? citation.provenance}
              sourceType={
                detail?.provenance
                  ? undefined
                  : citation.isMock
                    ? 'simulated'
                    : 'official_document'
              }
              lang={lang}
            />
            <span className="mono text-[10px] text-fg-muted">
              {chunkId}
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Clickable citation chip. Pass an `onOpen` handler so one drawer instance
 * can be hoisted to the page rather than one per chip.
 */
export function CitationChip({ citation, onOpen, lang = 'vi' }) {
  if (!citation) return null;
  const label = citation.sourceLabel || citation.document || citation.chunkId;
  // mục 16 data contract: a citation backed by fabricated demo content must
  // never look identical to a real syllabus citation — same reasoning as
  // ProvenanceBadge's "simulated" style, just at chip scale.
  if (citation.isMock) {
    return (
      <button
        type="button"
        onClick={() => onOpen(citation)}
        className="cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-full inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5"
        style={{ color: 'var(--gold)', background: 'var(--gold-soft)' }}
        title={
          lang === 'vi'
            ? `Dữ liệu mô phỏng — mở nguồn: ${label}`
            : `Simulated data — open source: ${label}`
        }
      >
        <FlaskConical size={10} aria-hidden="true" />
        <span className="truncate max-w-[180px]">{label}</span>
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      className="citation cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent rounded inline-flex items-center gap-1"
      title={lang === 'vi' ? `Mở nguồn: ${label}` : `Open source: ${label}`}
    >
      <BookOpen size={10} aria-hidden="true" />
      <span className="truncate max-w-[180px]">{label}</span>
    </button>
  );
}

export default SourceDrawer;
