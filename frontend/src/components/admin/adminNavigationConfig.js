/**
 * Admin Console sidebar navigation as data, adapted from chung's
 * observation-before-governance ordering contract (docs/branch-audit/
 * chung-admin-frontend.md) to this branch's actual route set. Chung only
 * has 8 items across its 2 groups; this branch additionally exposes
 * Analytics (observational -- grouped with Observe), Term & exams and
 * EduSync sync (governance actions -- grouped with Governance), which
 * chung's Admin Console doesn't have at all.
 */
export const NAV_GROUPS = [
  {
    id: 'observe',
    labelKey: 'admin.navGroupObserve',
    items: [
      { to: '/admin/overview', labelKey: 'admin.navOverview', end: true },
      { to: '/admin/people', labelKey: 'admin.navPeople' },
      { to: '/admin/datarequests', labelKey: 'admin.navDataRequests' },
      { to: '/admin/analytics', labelKey: 'admin.navAnalytics' },
    ],
  },
  {
    id: 'governance',
    labelKey: 'admin.navGroupGovernance',
    items: [
      { to: '/admin/courses', labelKey: 'admin.navCurriculum' },
      { to: '/admin/academic', labelKey: 'admin.navAcademic' },
      { to: '/admin/policy', labelKey: 'admin.navAiPolicy' },
      { to: '/admin/mocklms', labelKey: 'admin.navMockLms' },
      { to: '/admin/users', labelKey: 'admin.navAccounts' },
      { to: '/admin/org-settings', labelKey: 'admin.navSettings' },
      { to: '/admin/audit', labelKey: 'admin.navSystemLog' },
    ],
  },
];
