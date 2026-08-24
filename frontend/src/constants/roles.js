export const ROLE_LABEL = {
  vi: { student: 'Sinh viên', instructor: 'Giảng viên', admin: 'Admin' },
  en: { student: 'Student', instructor: 'Instructor', admin: 'Admin' },
};

export const ROLE_DESC = {
  vi: {
    student: 'Dashboard học tập SSA101',
    instructor: 'Giám sát & Duyệt Guardrail',
    admin: 'Quản lý Curriculum & KPI',
  },
  en: {
    student: 'SSA101 learning dashboard',
    instructor: 'Class oversight & guardrail review',
    admin: 'Curriculum & KPI management',
  },
};

export const DEFAULT_ROUTE = { student: '/student', instructor: '/instructor', admin: '/admin' };

export function routeForRole(role) {
  return DEFAULT_ROUTE[role] || DEFAULT_ROUTE.student;
}
