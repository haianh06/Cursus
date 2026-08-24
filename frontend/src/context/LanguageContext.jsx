import React, { createContext, useContext, useState, useEffect } from 'react';
import { vi } from '../locales/vi';
import { en } from '../locales/en';

const dictionaries = { vi, en };

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try {
      const saved = localStorage.getItem('cursus_lang');
      return saved === 'en' ? 'en' : 'vi';
    } catch {
      return 'vi';
    }
  });

  const setLang = (newLang) => {
    const validLang = newLang === 'en' ? 'en' : 'vi';
    setLangState(validLang);
    try {
      localStorage.setItem('cursus_lang', validLang);
    } catch {
      // Ignore storage errors
    }
  };

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // <title>/meta/OG/Twitter tags are owned by <SeoManager> (mounted inside
  // the Router in App.jsx) — it reacts to both `lang` AND route changes.
  // This provider only owns the `lang` value itself.

  const toggleLang = () => {
    setLang(lang === 'vi' ? 'en' : 'vi');
  };

  /**
   * Helper function t(keyPath, params)
   * Example: t('auth.titleLogin') -> "Đăng nhập Cursus" / "Sign in to Cursus"
   */
  const t = (keyPath, params = {}) => {
    if (!keyPath) return '';
    const dict = dictionaries[lang] || dictionaries.vi;
    const keys = keyPath.split('.');
    
    let current = dict;
    for (const key of keys) {
      if (current && typeof current === 'object' && key in current) {
        current = current[key];
      } else {
        // Fallback to Vietnamese dictionary if key missing in target language
        let fallback = dictionaries.vi;
        for (const fk of keys) {
          if (fallback && typeof fallback === 'object' && fk in fallback) {
            fallback = fallback[fk];
          } else {
            return keyPath;
          }
        }
        current = fallback;
        break;
      }
    }

    if (typeof current === 'string') {
      let result = current;
      Object.keys(params).forEach((paramKey) => {
        result = result.replace(new RegExp(`{${paramKey}}`, 'g'), params[paramKey]);
      });
      return result;
    }

    return keyPath;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
