/**
 * lib/authClient.js — the ONE import every auth screen and App.jsx should
 * use for login/register/getMe/logout. Re-exports the real FastAPI-backed
 * client (`lib/api.js`) unchanged; kept as its own module so screens never
 * import `lib/api.js` directly.
 */

export {
  login,
  register,
  getMe,
  logout,
  forgotPassword,
  resetPassword,
  verifyEmail,
  resendEmailVerification,
  changeEmail,
  setAuthFailureHandler,
  getInviteDetails,
  startDemoSession,
  requestOrgAccess,
  createInvite,
  getInvites,
  revokeInvite,
} from './api';
