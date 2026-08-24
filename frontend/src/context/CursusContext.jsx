import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getInstructorDashboard,
  getInstructorAlerts,
  recordIntervention,
  getGuardrailReviewQueue,
  resolveGuardrailReview,
  getAdminCourses,
  addAdminCourse,
  deleteAdminCourse,
  getAdminKpi,
  updatePreferences,
} from '../lib/api';

/**
 * Instructor + Admin data plumbing — talks to the real backend
 * (`src/api/instructor.py`, `src/api/admin.py`) via `lib/api.js`.
 *
 * This provider is mounted for every session (including anonymous / student
 * ones, see App.jsx) because the notification bell + mascot toggle it also
 * hosts are shared UI chrome. Only `user.role === 'instructor' | 'admin'`
 * triggers any network call — a student or logged-out visitor never hits
 * these authenticated, role-gated endpoints.
 */

// Local-only UI chrome that has no backend equivalent (no notifications API
// exists yet) — kept as a static seed so the bell / settings screen keep
// their previous demo behaviour.
const INITIAL_NOTIFICATIONS = [
  { id: 'n1', type: 'deadline', title: 'Project — Part 1 (SSA101) đến hạn trong 24 giờ', read: false, timestamp: '2026-08-08T09:00:00Z' },
  { id: 'n2', type: 'reflection', title: 'Đã đến lúc viết Reflect tuần 4', read: false, timestamp: '2026-08-08T07:00:00Z' },
  { id: 'n3', type: 'system', title: 'Trợ lý Cursus vừa nạp thêm 12 chunk mới cho môn PRF192', read: true, timestamp: '2026-08-06T14:00:00Z' },
];

const CursusContext = createContext();

export function CursusProvider({ user, children }) {
  const role = user?.role;

  // Instructor slice
  const [classInfo, setClassInfo] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [queue, setQueue] = useState([]);
  // mục 6.4 "bộ chọn lớp ở đầu trang" -- null means "every class combined"
  // (previous, unchanged default). Persisted per-tab only, not across
  // sessions: an instructor landing back on the dashboard tomorrow should
  // see the same "all classes" overview as always, not a stale filter.
  const [selectedCourseId, setSelectedCourseId] = useState(null);

  // Admin slice
  const [courses, setCourses] = useState([]);
  const [kpi, setKpi] = useState(null);

  // Shared UI chrome (no backend endpoint yet)
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);

  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const load = useCallback(
    ({ silent = false } = {}) => {
      if (role === 'instructor') {
        if (!silent) setLoading(true);
        setLoadError(null);
        return Promise.all([
          getInstructorDashboard(selectedCourseId),
          getInstructorAlerts(selectedCourseId),
          getGuardrailReviewQueue(),
        ])
          .then(([dashboard, alertData, queueData]) => {
            setClassInfo(dashboard);
            setAlerts(alertData?.alerts ?? []);
            setQueue(Array.isArray(queueData) ? queueData : []);
          })
          .catch((err) => {
            setLoadError(err);
            throw err;
          })
          .finally(() => {
            if (!silent) setLoading(false);
          });
      }

      if (role === 'admin') {
        if (!silent) setLoading(true);
        setLoadError(null);
        return Promise.all([getAdminCourses(), getAdminKpi()])
          .then(([courseData, kpiData]) => {
            setCourses(courseData?.courses ?? []);
            setKpi(kpiData ?? null);
          })
          .catch((err) => {
            setLoadError(err);
            throw err;
          })
          .finally(() => {
            if (!silent) setLoading(false);
          });
      }

      // Student / anonymous — this context has nothing to load; make sure
      // a previous instructor/admin session's data doesn't leak across a
      // role switch on a shared device.
      setClassInfo(null);
      setAlerts([]);
      setQueue([]);
      setCourses([]);
      setKpi(null);
      setLoading(false);
      setLoadError(null);
      return Promise.resolve();
    },
    [role, selectedCourseId],
  );

  useEffect(() => {
    load().catch(() => {
      /* surfaced through loadError */
    });
  }, [load]);

  const selectClass = useCallback((courseId) => {
    setSelectedCourseId(courseId || null);
  }, []);

  // ── Instructor: alerts + guardrail appeal queue ──────────────────────
  const interveneAlert = useCallback(
    (alertId, { action = 'contacted', note = null } = {}) =>
      recordIntervention(alertId, { action, note }).then(() => load({ silent: true })),
    [load],
  );

  const resolveAppeal = useCallback(
    (appealId, decision) => {
      const backendDecision = decision === 'approved' ? 'UNBLOCK' : 'KEEP';
      return resolveGuardrailReview(appealId, backendDecision).then(() => load({ silent: true }));
    },
    [load],
  );

  // ── Admin: course catalog ─────────────────────────────────────────────
  const addCourse = useCallback((code, name, semester) => {
    return addAdminCourse({ subjectCode: code, subjectName: name, semester }).then((data) => {
      setCourses(data?.courses ?? []);
    });
  }, []);

  const deleteCourse = useCallback((code) => {
    return deleteAdminCourse(code).then((data) => {
      setCourses(data?.courses ?? []);
    });
  }, []);

  // ── Shared UI chrome ──────────────────────────────────────────────────
  const [showMascot, setShowMascot] = useState(() => {
    if (user?.preferences && typeof user.preferences.showMascot === 'boolean') {
      return user.preferences.showMascot;
    }
    return localStorage.getItem('cursus_show_mascot') !== 'false';
  });

  const toggleMascot = () => {
    setShowMascot((prev) => {
      const next = !prev;
      localStorage.setItem('cursus_show_mascot', String(next));
      // Synced server-side so the toggle follows the account across devices
      // (see src/api/auth.py PUT /auth/me/preferences) — skipped for demo
      // users since demo sessions aren't meant to persist preferences.
      if (user && !user.isDemo) {
        updatePreferences({ showMascot: next }).catch(() => {
          /* best-effort sync — localStorage already has the new value */
        });
      }
      return next;
    });
  };

  const markNotificationRead = (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const markAllNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <CursusContext.Provider
      value={{
        // Instructor
        classInfo,
        alerts,
        interveneAlert,
        queue,
        resolveAppeal,
        selectedCourseId,
        selectClass,
        // Admin
        courses,
        addCourse,
        deleteCourse,
        kpi,
        // Shared
        showMascot,
        toggleMascot,
        notifications,
        markNotificationRead,
        markAllNotificationsRead,
        loading,
        loadError,
        retryLoad: load,
      }}
    >
      {children}
    </CursusContext.Provider>
  );
}

export function useCursus() {
  const context = useContext(CursusContext);
  if (!context) {
    throw new Error('useCursus must be used within a CursusProvider');
  }
  return context;
}
