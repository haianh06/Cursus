import { ADMIN_PATHS } from './adminRoutes';

/** One canonical information architecture: observe first, then govern. */
export const NAV_GROUPS = [
  {
    id: 'observe',
    labelKey: 'admin.navGroupObserve',
    items: [
      { to: ADMIN_PATHS.overview, labelKey: 'admin.navOverview', end: true },
      { to: ADMIN_PATHS.people, labelKey: 'admin.navPeople' },
      { to: ADMIN_PATHS.analytics, labelKey: 'admin.navAnalytics' },
      { to: ADMIN_PATHS.aiUsage, labelKey: 'admin.navAiUsage' },
    ],
  },
  {
    id: 'governance',
    labelKey: 'admin.navGroupGovernance',
    items: [
      { to: ADMIN_PATHS.curriculum, labelKey: 'admin.navCurriculum' },
      { to: ADMIN_PATHS.sections, labelKey: 'admin.navSections' },
      { to: ADMIN_PATHS.academic, labelKey: 'admin.navAcademic' },
      { to: ADMIN_PATHS.aiPolicy, labelKey: 'admin.navAiPolicy' },
      { to: ADMIN_PATHS.eduSync, labelKey: 'admin.navMockLms' },
      { to: ADMIN_PATHS.access, labelKey: 'admin.navAccounts' },
      { to: ADMIN_PATHS.settings, labelKey: 'admin.navSettings' },
      { to: ADMIN_PATHS.logs, labelKey: 'admin.navSystemLog' },
    ],
  },
];
