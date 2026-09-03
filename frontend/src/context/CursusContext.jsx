import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getAdminCourses,
  addAdminCourse,
  deleteAdminCourse,
  getAdminKpi,
  listSemesters,
  getInstructorNotifications,
  markInstructorNotificationRead,
  markAllInstructorNotificationsRead,
} from '../lib/api';

/**
 * Admin course-catalog data plumbing — talks to the real backend
 * (`src/api/admin.py`) via `lib/api.js`. Instructor pages fetch their own
 * dashboard/alerts data independently (see InstructorHome, InstructorRiskPage)
 * and don't use this context for that — the one exception is the
 * notification bell below, which IS real for instructors (backed by
 * `/instructor/notifications`, see `src/api/instructor.py`).
 *
 * This provider is mounted for every session (including anonymous ones, see
 * App.jsx) because the notification bell + mascot toggle it also hosts are
 * shared UI chrome. Admin/student notifications stay a static local-only
 * demo seed below (no backend endpoint for those roles yet) — only
 * instructor notifications round-trip to the server.
 */

// Local-only UI chrome for admin/student (no notifications API for those
// roles yet) — kept as a static seed so the bell / settings screen keep
// their previous demo behaviour. Instructor notifications are real, see load().
const INITIAL_NOTIFICATIONS = [
  { id: 'n1', type: 'deadline', title: 'Project — Part 1 (SSA101) đến hạn trong 24 giờ', read: false, timestamp: '2026-08-08T09:00:00Z' },
  { id: 'n2', type: 'reflection', title: 'Đã đến lúc viết Reflect tuần 4', read: false, timestamp: '2026-08-08T07:00:00Z' },
  { id: 'n3', type: 'system', title: 'Trợ lý Cursus vừa nạp thêm 12 chunk mới cho môn PRF192', read: true, timestamp: '2026-08-06T14:00:00Z' },
];

const CursusContext = createContext();

export function CursusProvider({ user, children }) {
  const role = user?.role;

  // Admin slice
  const [courses, setCourses] = useState([]);
  const [kpi, setKpi] = useState(null);

  // Student slice — active semester, for the topbar's "Học kỳ ... • Tuần ..."
  // indicator (previously a hardcoded placeholder string, see App.jsx Topbar).
  const [activeSemester, setActiveSemester] = useState(null);

  // Shared UI chrome (no backend endpoint yet)
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);

  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const load = useCallback(
    ({ silent = false } = {}) => {
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

      if (role === 'student') {
        if (!silent) setLoading(true);
        setLoadError(null);
        setCourses([]);
        setKpi(null);
        return listSemesters()
          .then((data) => {
            const semesters = data?.semesters ?? [];
            const active = semesters.find((s) => s.id === data?.active_id) ?? semesters.find((s) => s.is_active) ?? null;
            setActiveSemester(active);
          })
          .catch((err) => {
            setLoadError(err);
            throw err;
          })
          .finally(() => {
            if (!silent) setLoading(false);
          });
      }

      if (role === 'instructor') {
        if (!silent) setLoading(true);
        setLoadError(null);
        setCourses([]);
        setKpi(null);
        setActiveSemester(null);
        return getInstructorNotifications()
          .then((data) => {
            setNotifications(
              (data?.items ?? []).map((n) => ({
                id: n.id,
                type: n.type,
                title: n.title,
                link: n.link,
                read: n.read,
                timestamp: n.timestamp,
              })),
            );
          })
          .catch((err) => {
            setLoadError(err);
            throw err;
          })
          .finally(() => {
            if (!silent) setLoading(false);
          });
      }

      // Anonymous — this context has nothing to load; make sure a previous
      // session's data doesn't leak across a role switch on a shared device.
      setCourses([]);
      setKpi(null);
      setActiveSemester(null);
      setNotifications(INITIAL_NOTIFICATIONS);
      setLoading(false);
      setLoadError(null);
      return Promise.resolve();
    },
    [role],
  );

  useEffect(() => {
    load().catch(() => {
      /* surfaced through loadError */
    });
  }, [load]);

  // Instructor notification bell is real (backend-backed), so keep it fresh
  // without requiring a manual refresh -- same "poll quietly" pattern as
  // CursusChat's server-health check.
  useEffect(() => {
    if (role !== 'instructor') return undefined;
    const interval = setInterval(() => {
      load({ silent: true }).catch(() => {
        /* surfaced through loadError on the next non-silent load */
      });
    }, 30000);
    return () => clearInterval(interval);
  }, [role, load]);

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

  const markNotificationRead = (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    if (role === 'instructor') {
      markInstructorNotificationRead(id).catch(() => {
        /* best-effort -- the bell already shows it as read locally */
      });
    }
  };

  const markAllNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    if (role === 'instructor') {
      markAllInstructorNotificationsRead().catch(() => {
        /* best-effort -- the bell already shows everything as read locally */
      });
    }
  };

  return (
    <CursusContext.Provider
      value={{
        // Admin
        courses,
        addCourse,
        deleteCourse,
        kpi,
        // Student
        activeSemester,
        // Shared
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
