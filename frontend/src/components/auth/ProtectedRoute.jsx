import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import UnauthorizedPage from '../shared/UnauthorizedPage';

/**
 * Central guard for authenticated routes. Reads `authStatus`/`user` from
 * App.jsx (never from query string, form, or localStorage) and decides:
 *   - initializing  -> render nothing (App's loader overlay already covers this)
 *   - no user       -> /login?returnTo=<attempted path>
 *   - email not confirmed -> /email-verification
 *   - not onboarded -> /onboarding
 *   - role not in allowedRoles -> in-place UnauthorizedPage (explicit page,
 *     not a silent URL swap, so "why did the URL change" never comes up)
 *   - else -> children
 */
export default function ProtectedRoute({ authStatus, user, allowedRoles, children }) {
  const location = useLocation();

  if (authStatus === 'initializing') return null;

  if (!user) {
    const returnTo = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?returnTo=${returnTo}`} replace />;
  }

  if (!user.email_confirmed) return <Navigate to="/email-verification" replace />;
  if (!user.onboarded) return <Navigate to="/onboarding" replace />;

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <UnauthorizedPage role={user.role} />;
  }

  return children;
}
