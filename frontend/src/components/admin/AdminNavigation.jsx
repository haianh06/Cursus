import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart3, BookOpen, CalendarRange, ClipboardList, GitCompareArrows,
  LayoutDashboard, ScrollText, Settings, ShieldCheck, Users as UsersIcon,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { NAV_GROUPS } from './adminNavigationConfig';
import { ADMIN_PATHS } from './adminRoutes';
import './admin-operations.css';

const ITEM_ICONS = {
  [ADMIN_PATHS.overview]: LayoutDashboard,
  [ADMIN_PATHS.people]: UsersIcon,
  [ADMIN_PATHS.dataRequests]: ClipboardList,
  [ADMIN_PATHS.analytics]: BarChart3,
  [ADMIN_PATHS.curriculum]: BookOpen,
  [ADMIN_PATHS.academic]: CalendarRange,
  [ADMIN_PATHS.aiPolicy]: ShieldCheck,
  [ADMIN_PATHS.eduSync]: GitCompareArrows,
  [ADMIN_PATHS.access]: UsersIcon,
  [ADMIN_PATHS.settings]: Settings,
  [ADMIN_PATHS.logs]: ScrollText,
};

/** Admin Console's primary navigation, rebuilt from chung's "observe before
 * governance" sidebar (docs/branch-audit/chung-admin-frontend.md), restyled
 * to this app's own `.nav-item`/`.active` tokens instead of chung's
 * separate slate/blue palette -- see admin-operations.css's note on why a
 * second color theme was dropped. Replaces the single "Admin Console" link
 * that used to sit in the app shell's sidebar; AdminConsole.jsx no longer
 * renders its own internal tab bar for these same sections. */
export default function AdminNavigation({ onNavigate }) {
  const { t } = useLanguage();

  return (
    <nav aria-label={t('admin.navigationLabel')} className="admin-nav flex flex-col gap-3">
      {NAV_GROUPS.map((group) => {
        const labelId = `admin-nav-group-${group.id}`;
        return (
          <div key={group.id}>
            <p
              id={labelId}
              className="select-none px-3 pb-1 text-[10px] font-bold uppercase tracking-[0.08em] text-sidebar-text/70"
            >
              {t(group.labelKey)}
            </p>
            <ul aria-labelledby={labelId} className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const Icon = ITEM_ICONS[item.to] || ClipboardList;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={Boolean(item.end)}
                      onClick={onNavigate}
                      className={({ isActive }) => `nav-item w-full text-left ${isActive ? 'active' : ''}`}
                    >
                      <Icon size={15} aria-hidden="true" />
                      <span>{t(item.labelKey)}</span>
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
