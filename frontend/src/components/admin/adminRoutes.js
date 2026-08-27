export const ADMIN_PATHS = Object.freeze({
  overview: '/admin/overview',
  people: '/admin/people',
  dataRequests: '/admin/data-requests',
  analytics: '/admin/analytics',
  curriculum: '/admin/governance/curriculum',
  sections: '/admin/governance/sections',
  academic: '/admin/governance/academic',
  aiPolicy: '/admin/governance/ai-policy',
  eduSync: '/admin/governance/edusync',
  access: '/admin/governance/access',
  settings: '/admin/governance/settings',
  logs: '/admin/governance/logs',
});

/** Old URLs stay valid so saved links and queue items never strand an operator. */
export const LEGACY_ADMIN_REDIRECTS = Object.freeze([
  { from: 'datarequests', to: ADMIN_PATHS.dataRequests },
  { from: 'courses', to: ADMIN_PATHS.curriculum },
  { from: 'academic', to: ADMIN_PATHS.academic },
  { from: 'policy', to: ADMIN_PATHS.aiPolicy },
  { from: 'mocklms', to: ADMIN_PATHS.eduSync },
  { from: 'users', to: ADMIN_PATHS.access },
  { from: 'org-settings', to: ADMIN_PATHS.settings },
  { from: 'audit', to: ADMIN_PATHS.logs },
]);
