import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Chrome dung chung cho 7 man Giang vien: thanh tieu de ghim khi cuon va
 * phan trang cho cac danh sach dai.
 *
 * Vung cuon cua app la <main id="main-content"> (App.jsx). `position: sticky`
 * tinh theo to tien cuon gan nhat, nen chi can top: 0 — khong can do toa do
 * hay dung scroll listener.
 */

/**
 * Boc thanh tieu de (+ thanh bo loc / tab neu co) de no ghim lai khi cuon.
 *
 * `pinned` phat hien bang IntersectionObserver tren mot moc 1px dat ngay
 * tren thanh, chu khong bang scroll listener: khong co handler nao chay
 * theo tung frame cuon, va khong phai gia dinh phan tu nao dang cuon.
 */
export function GvStickyHeader({ children, className = '' }) {
  const [pinned, setPinned] = useState(false);
  const sentinelRef = useRef(null);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(
      ([entry]) => setPinned(!entry.isIntersecting),
      // root: null = viewport. Moc nam trong <main> nen khi <main> cuon,
      // moc ra khoi viewport va thanh duoc coi la da ghim.
      { threshold: 1 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <>
      <div ref={sentinelRef} className="gv-sticky-sentinel" aria-hidden="true" />
      <div className={`gv-sticky${pinned ? ' gv-sticky--pinned' : ''}${className ? ` ${className}` : ''}`}>
        {children}
      </div>
    </>
  );
}

/**
 * Cat mot mang thanh trang.
 *
 * Tra ve ca `page` da bi kep lai trong khoang hop le: khi bo loc thu hep
 * ket qua, so trang giam va trang dang xem co the vuot qua cuoi — luc do
 * hook tu keo ve trang cuoi thay vi hien danh sach rong.
 */
export function usePaged(items, pageSize = 8) {
  const [page, setPage] = useState(1);
  const total = items.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, pageCount);

  useEffect(() => {
    if (page !== safePage) setPage(safePage);
  }, [page, safePage]);

  const slice = useMemo(
    () => items.slice((safePage - 1) * pageSize, safePage * pageSize),
    [items, safePage, pageSize],
  );

  // Ve dau danh sach moi khi bo loc doi — trang 3 cua ket qua cu khong con
  // y nghia gi voi ket qua moi.
  const reset = () => setPage(1);

  return {
    slice,
    page: safePage,
    pageCount,
    total,
    setPage,
    reset,
    from: total === 0 ? 0 : (safePage - 1) * pageSize + 1,
    to: Math.min(safePage * pageSize, total),
  };
}

/** Danh so trang dang 1 … 4 5 6 … 12: luon giu trang dau, cuoi va lang gieng. */
function pageWindow(page, pageCount) {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, i) => i + 1);
  const out = new Set([1, pageCount, page, page - 1, page + 1]);
  if (page <= 3) [2, 3, 4].forEach((n) => out.add(n));
  if (page >= pageCount - 2) [pageCount - 3, pageCount - 2, pageCount - 1].forEach((n) => out.add(n));
  const nums = [...out].filter((n) => n >= 1 && n <= pageCount).sort((a, b) => a - b);
  const withGaps = [];
  nums.forEach((n, i) => {
    if (i > 0 && n - nums[i - 1] > 1) withGaps.push('gap');
    withGaps.push(n);
  });
  return withGaps;
}

/**
 * Thanh phan trang. An hoan toan khi chi co mot trang — khong hien mot thanh
 * dieu huong khong dieu huong duoc di dau.
 */
export function GvPager({ page, pageCount, total, from, to, onChange, label }) {
  const { t } = useLanguage();
  if (pageCount <= 1) return null;

  return (
    <nav className="gv-pager" aria-label={label}>
      <p className="gv-pager__info">{t('gv.pagerShowing', { from, to, total })}</p>
      <div className="gv-pager__nav">
        <button
          type="button"
          className="gv-pager__btn"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          aria-label={t('gv.pagerPrev')}
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>

        {pageWindow(page, pageCount).map((entry, i) => (
          entry === 'gap' ? (
            // eslint-disable-next-line react/no-array-index-key
            <span key={`gap-${i}`} className="gv-pager__gap" aria-hidden="true">{t('gv.pagerMore')}</span>
          ) : (
            <button
              key={entry}
              type="button"
              className="gv-pager__btn"
              aria-current={entry === page ? 'page' : undefined}
              aria-label={t('gv.pagerPage', { n: entry })}
              onClick={() => onChange(entry)}
            >
              {entry}
            </button>
          )
        ))}

        <button
          type="button"
          className="gv-pager__btn"
          onClick={() => onChange(page + 1)}
          disabled={page >= pageCount}
          aria-label={t('gv.pagerNext')}
        >
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
