import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { NAV_GROUPS } from './adminNavigationConfig';

export default function AdminTopbarSearch() {
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const rootRef = useRef(null);
  const inputRef = useRef(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const pages = useMemo(
    () => NAV_GROUPS.flatMap((group) => group.items.map((item) => ({
      ...item,
      groupLabel: t(group.labelKey),
      label: t(item.labelKey),
    }))),
    [t],
  );

  const results = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase(lang === 'vi' ? 'vi-VN' : 'en-US');
    if (!normalized) return pages.slice(0, 6);
    return pages.filter((page) => page.label
      .toLocaleLowerCase(lang === 'vi' ? 'vi-VN' : 'en-US')
      .includes(normalized));
  }, [lang, pages, query]);

  useEffect(() => {
    const onPointerDown = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    const onKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === 'k') {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, []);

  function goTo(page) {
    navigate(page.to);
    setQuery('');
    setOpen(false);
  }

  function submit(event) {
    event.preventDefault();
    if (results[0]) goTo(results[0]);
  }

  return (
    <div ref={rootRef} className="relative hidden w-full max-w-md md:block">
      <form role="search" onSubmit={submit}>
        <Search
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted"
          aria-hidden="true"
        />
        <input
          ref={inputRef}
          type="search"
          className="input h-9 w-full bg-surface text-xs"
          style={{ paddingLeft: '2.25rem', paddingRight: '3.25rem' }}
          value={query}
          placeholder={t('common.searchPlaceholder')}
          aria-label={t('common.searchPlaceholder')}
          aria-expanded={open}
          aria-controls="admin-global-search-results"
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
        />
        <kbd className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 rounded border border-line bg-surface-card px-1.5 py-0.5 text-[9px] font-semibold text-fg-muted">
          Ctrl K
        </kbd>
      </form>

      {open && (
        <div
          id="admin-global-search-results"
          className="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-50 overflow-hidden rounded-lg border border-line bg-surface-card shadow-elevation-2"
        >
          {results.length === 0 ? (
            <p className="px-3 py-4 text-center text-xs text-fg-muted">
              {lang === 'vi' ? 'Không tìm thấy chức năng phù hợp.' : 'No matching admin page.'}
            </p>
          ) : (
            <ul className="max-h-72 overflow-y-auto p-1.5">
              {results.map((page) => (
                <li key={page.to}>
                  <button
                    type="button"
                    className="flex min-h-10 w-full items-center justify-between rounded-md px-3 py-2 text-left hover:bg-surface-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    onClick={() => goTo(page)}
                  >
                    <span className="text-xs font-semibold text-fg">{page.label}</span>
                    <span className="text-[10px] text-fg-muted">{page.groupLabel}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
