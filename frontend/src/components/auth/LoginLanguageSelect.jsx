import React, { useEffect, useId, useRef, useState } from 'react';
import { Globe2, ChevronDown, Check } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

const OPTIONS = [
  { code: 'vi', key: 'auth.langNameVi' },
  { code: 'en', key: 'auth.langNameEn' },
];

/**
 * Bo chon ngon ngu cua man dang nhap: pill "globe + Tieng Viet + chevron"
 * dung theo anh tham chieu.
 *
 * Day chi la mot LOP GIAO DIEN khac cho LanguageContext da co — no goi
 * setLang y het LanguageToggle (dang VI|EN dung o cac man khac). Khong co
 * he i18n thu hai nao duoc dung len o day.
 *
 * Dung mau nut + menu thay vi <select> vi reference co chevron va vien
 * pill rieng ma <select> khong style duoc dong bo giua cac trinh duyet.
 * Doi lai phai tu lo ban phim: Escape dong, click ra ngoai dong, va focus
 * quay ve nut sau khi chon.
 */
export default function LoginLanguageSelect() {
  const { lang, setLang, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const btnRef = useRef(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (!rootRef.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      setOpen(false);
      btnRef.current?.focus();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const current = OPTIONS.find((o) => o.code === lang) || OPTIONS[0];

  return (
    <div className="clp-lang" ref={rootRef}>
      <button
        ref={btnRef}
        type="button"
        className="clp-lang__btn"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={t('auth.langSwitchLabel')}
        onClick={() => setOpen((v) => !v)}
      >
        <Globe2 size={21} strokeWidth={1.9} aria-hidden="true" />
        <span className="clp-lang__name">{t(current.key)}</span>
        <ChevronDown size={18} strokeWidth={2} className="clp-lang__chev" aria-hidden="true" />
      </button>

      {open && (
        <ul className="clp-lang__menu" id={menuId} role="listbox" aria-label={t('auth.langSwitchLabel')}>
          {OPTIONS.map((o) => (
            <li key={o.code} role="none">
              <button
                type="button"
                role="option"
                aria-selected={o.code === lang}
                className="clp-lang__opt"
                onClick={() => { setLang(o.code); setOpen(false); btnRef.current?.focus(); }}
              >
                {t(o.key)}
                {o.code === lang && <Check size={17} strokeWidth={2.2} aria-hidden="true" />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
