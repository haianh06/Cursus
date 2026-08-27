import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { vi } from '../locales/vi';
import { en } from '../locales/en';

type Lang = 'vi' | 'en';

const dictionaries = { vi, en };

const LanguageContext = createContext<{
  lang: Lang;
  setLang: (lang: Lang) => void;
  toggleLang: () => void;
  t: (keyPath: string) => string;
} | null>(null);

const STORAGE_KEY = 'mock_lms_lang';

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'vi';
    } catch {
      return 'vi';
    }
  });

  const setLang = (next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore storage errors
    }
  };

  const toggleLang = () => setLang(lang === 'vi' ? 'en' : 'vi');

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const t = (keyPath: string): string => {
    const dict = dictionaries[lang] ?? dictionaries.vi;
    const value = keyPath.split('.').reduce<unknown>((acc, key) => {
      if (acc && typeof acc === 'object' && key in acc) return (acc as Record<string, unknown>)[key];
      return undefined;
    }, dict);
    if (typeof value === 'string') return value;
    // Missing key: fall back to Vietnamese rather than showing "a.b.c" raw.
    const fallback = keyPath.split('.').reduce<unknown>((acc, key) => {
      if (acc && typeof acc === 'object' && key in acc) return (acc as Record<string, unknown>)[key];
      return undefined;
    }, dictionaries.vi);
    return typeof fallback === 'string' ? fallback : keyPath;
  };

  return <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within a LanguageProvider');
  return ctx;
}
