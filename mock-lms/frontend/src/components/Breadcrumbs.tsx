import { ChevronRight, Home } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
  active?: boolean;
}

export function Breadcrumbs({ items, onHome }: { items: BreadcrumbItem[]; onHome: () => void }) {
  const { t } = useLanguage();
  return (
    <nav aria-label="Breadcrumb" className="w-full bg-[#F8F9FA] dark:bg-[var(--bg-elevated)] border-b border-[#E5E7EB] dark:border-white/10 px-4 py-2 text-xs text-gray-600 dark:text-slate-400 select-none">
      <div className="w-full max-w-[1440px] mx-auto flex items-center space-x-1.5 overflow-x-auto whitespace-nowrap">
        <button onClick={onHome} className="flex items-center space-x-1 text-[#0066CC] dark:text-[var(--accent)] hover:underline cursor-pointer" title={t('breadcrumb.homeTitle')}>
          <Home className="w-3.5 h-3.5" />
          <span>{t('nav.brand')}</span>
        </button>
        {items.map((item, index) => (
          <span key={index} className="flex items-center space-x-1.5">
            <ChevronRight className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            {item.active || !item.onClick ? (
              <span className="font-semibold text-gray-800 dark:text-slate-200" aria-current="page">{item.label}</span>
            ) : (
              <button onClick={item.onClick} className="text-[#0066CC] dark:text-[var(--accent)] hover:underline cursor-pointer">{item.label}</button>
            )}
          </span>
        ))}
      </div>
    </nav>
  );
}
