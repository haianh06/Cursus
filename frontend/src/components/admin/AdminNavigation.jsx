import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart3, BookOpen, CalendarRange, ClipboardList, GitCompareArrows,
  LayoutDashboard, ScrollText, Settings, ShieldCheck, Users as UsersIcon,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { NAV_GROUPS } from './adminNavigationConfig';

const ITEM_ICONS = {
  '/admin/overview': LayoutDashboard,
  '/admin/people': UsersIcon,
  '/admin/datarequests': ClipboardList,
  '/admin/analytics': BarChart3,
  '/admin/courses': BookOpen,
  '/admin/academic': CalendarRange,
  '/admin/policy': ShieldCheck,
  '/admin/mocklms': GitCompareArrows,
  '/admin/users': UsersIcon,
  '/admin/org-settings': Settings,
  '/admin/audit': ScrollText,
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
    <nav aria-label={t('admin.navigationLabel')} className="flex flex-col gap-3">
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
