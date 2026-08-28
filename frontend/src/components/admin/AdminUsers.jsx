import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Clock3, KeyRound, Lock, Mail, ShieldCheck, Unlock, UserPlus, User, X } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import ConfirmDialog from '../shared/ConfirmDialog';
import { ROLE_LABEL } from '../../constants/roles';
import {
  createInvite,
  getAdminSections,
  getInvites,
  getOrgUsers,
  resetAdminUserPassword,
  revokeInvite,
  resendInvite,
  updateUserStatus,
} from '../../lib/api';

const INVITABLE_ROLES = ['STUDENT', 'INSTRUCTOR', 'ADMIN'];

function roleLabel(role, lang) {
  const key = String(role || '').toLowerCase();
  return (ROLE_LABEL[lang] || ROLE_LABEL.vi)[key] || role;
}

function inviteStatus(invite) {
  if (invite.revoked_at) return 'revoked';
  if (invite.used_at) return 'used';
  if (invite.expires_at && new Date(invite.expires_at).getTime() < Date.now()) return 'expired';
  return 'pending';
}

/** mục 6.5 Admin Console: send/revoke invites + list/lock org members.
 * Backend (POST/GET/DELETE /admin/invites, GET /admin/users,
 * PATCH /admin/users/{id}/status) already existed or was added alongside
 * this component -- this tab was the only missing piece. */
export default function AdminUsers() {
  const { t, lang } = useLanguage();
  const [users, setUsers] = useState(null);
  const [invites, setInvites] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busyId, setBusyId] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null); // { type: 'lockUser' | 'unlockUser' | 'revokeInvite' | 'resetPassword', target: any, reason: '' }

  const load = useCallback(() => {
    setError('');
    return Promise.all([getOrgUsers(), getInvites()])
      .then(([userRows, inviteRows]) => {
        setUsers(userRows);
        setInvites(inviteRows);
      })
      .catch((err) => setError(err.message || String(err)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function executeAction() {
    if (!confirmAction) return;
    const { type, target, reason } = confirmAction;

    if (type === 'lockUser' || type === 'unlockUser') {
      if ((type === 'lockUser' || type === 'unlockUser') && reason.trim().length < 5) {
        alert(lang === 'vi' ? 'Lý do phải dài ít nhất 5 ký tự.' : 'Reason must be at least 5 characters.');
        return;
      }
      setConfirmAction(null);
      setBusyId(target.id);
      setError('');
      updateUserStatus(target.id, type === 'unlockUser', reason)
        .then((updated) => {
          setUsers((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
        })
        .catch((err) => setError(err.message || String(err)))
        .finally(() => setBusyId(''));
    } else if (type === 'revokeInvite') {
      setConfirmAction(null);
      setBusyId(target.id);
      setError('');
      revokeInvite(target.id)
        .then(() => setInvites((rows) => rows.filter((row) => row.id !== target.id)))
        .catch((err) => setError(err.message || String(err)))
        .finally(() => setBusyId(''));
    } else if (type === 'resendInvite') {
      setConfirmAction(null);
      setBusyId(target.id);
      setError('');
      resendInvite(target.id)
        .then((updated) => setInvites((rows) => rows.map((row) => (row.id === updated.id ? updated : row))))
        .catch((err) => setError(err.message || String(err)))
        .finally(() => setBusyId(''));
    } else if (type === 'resetPassword') {
      setConfirmAction(null);
      setBusyId(target.id);
      setError('');
      setNotice('');
      // Response is `{success, emailSent}` with no `data` key, so
      // request()'s envelope-unwrap resolves this to `undefined` -- a
      // resolved promise (not its value) is what "it worked" means here.
      resetAdminUserPassword(target.id)
        .then(() => setNotice(t('admin.resetPasswordSuccess')))
        .catch((err) => setError(err.message || String(err)))
        .finally(() => setBusyId(''));
    }
  }

  function toggleUserStatus(user) {
    setConfirmAction({
      type: user.is_active ? 'lockUser' : 'unlockUser',
      target: user,
      reason: ''
    });
  }

  function handleRevoke(invite) {
    setConfirmAction({
      type: 'revokeInvite',
      target: invite,
      reason: ''
    });
  }

  function handleResend(invite) {
    setConfirmAction({ type: 'resendInvite', target: invite, reason: '' });
  }

  function handleResetPassword(user) {
    setNotice('');
    setConfirmAction({ type: 'resetPassword', target: user, reason: '' });
  }

  const activeUsers = users?.filter((user) => user.is_active).length || 0;
  const lockedUsers = users?.filter((user) => !user.is_active).length || 0;
  const pendingInvites = invites?.filter((invite) => inviteStatus(invite) === 'pending').length || 0;

  return (
    <div className="flex flex-col gap-6 text-left">
      {error && (
        <p className="flex items-center gap-2 text-xs text-danger" role="alert">
          <AlertCircle size={14} className="shrink-0" />{error}
        </p>
      )}
      {notice && (
        <p className="flex items-center gap-2 text-xs text-success" role="status">
          <ShieldCheck size={14} className="shrink-0" />{notice}
        </p>
      )}

      {users && invites && (
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-3" aria-label={lang === 'vi' ? 'Tổng hợp tài khoản' : 'Account summary'}>
          {[
            { label: lang === 'vi' ? 'Đang hoạt động' : 'Active accounts', value: activeUsers, note: lang === 'vi' ? 'Thành viên' : 'Members', icon: ShieldCheck, tone: 'text-success bg-success-soft' },
            { label: lang === 'vi' ? 'Lời mời chờ' : 'Pending invites', value: pendingInvites, note: lang === 'vi' ? 'Chưa kích hoạt' : 'Awaiting activation', icon: Clock3, tone: 'text-warning bg-warning-soft' },
            { label: lang === 'vi' ? 'Đã khoá' : 'Locked', value: lockedUsers, note: lang === 'vi' ? 'Tài khoản' : 'Accounts', icon: Lock, tone: 'text-danger bg-danger-soft' },
          ].map(({ label, value, note, icon: Icon, tone }) => (
            <article key={label} className="admin-stat-card">
              <span className={`admin-stat-icon ${tone}`}><Icon size={16} aria-hidden="true" /></span>
              <div><p className="text-[10px] font-bold uppercase tracking-wide text-fg-muted">{label}</p><p className="mono mt-1 text-2xl font-bold text-fg">{value}</p><p className="mt-1 text-[10px] text-fg-muted">{note}</p></div>
            </article>
          ))}
        </section>
      )}

      {/* Invites */}
      <section className="card p-5 sm:p-6 space-y-4" aria-labelledby="invites-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="invites-title" className="text-sm font-bold text-fg flex items-center gap-2">
            <Mail size={16} className="text-accent" /> {t('admin.invitesSectionTitle')}
          </h2>
          <button
            type="button"
            className="btn btn-accent text-xs px-4 py-2 cursor-pointer"
            onClick={() => setShowInviteModal(true)}
          >
            <UserPlus size={14} /> {t('admin.inviteBtn')}
          </button>
        </div>

        {invites === null ? (
          <p className="text-xs text-fg-muted">{t('admin.loading')}</p>
        ) : invites.length === 0 ? (
          <p className="text-xs text-fg-muted">{t('admin.invitesEmpty')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">{t('admin.inviteColEmail')}</th>
                  <th scope="col">{t('admin.inviteColRole')}</th>
                  <th scope="col">{t('admin.inviteColStatus')}</th>
                  <th scope="col">{t('admin.inviteColExpires')}</th>
                  <th scope="col">{t('admin.inviteColActions')}</th>
                </tr>
              </thead>
              <tbody>
                {invites.map((invite) => {
                  const status = inviteStatus(invite);
                  return (
                    <tr key={invite.id}>
                      <td className="text-fg">{invite.email}</td>
                      <td className="text-fg-secondary">{roleLabel(invite.role, lang)}</td>
                      <td>
                        <span className={`badge text-[9px] font-bold ${status === 'pending' ? 'badge-gold' : status === 'used' ? 'badge-success' : 'badge-neutral'}`}>
                          {t(`admin.${status === 'pending' ? 'invitePending' : status === 'used' ? 'inviteUsedStatus' : status === 'revoked' ? 'inviteRevokedStatus' : 'inviteExpiredStatus'}`)}
                        </span>
                        <span className="ml-2 text-[10px] text-fg-muted">
                          {invite.delivery_status === 'failed'
                            ? (lang === 'vi' ? 'Gửi lỗi' : 'Delivery failed')
                            : invite.delivery_status === 'pending'
                              ? (lang === 'vi' ? 'Đang gửi' : 'Sending')
                              : (lang === 'vi' ? 'Đã gửi' : 'Sent')}
                        </span>
                      </td>
                      <td className="text-fg-muted">{new Date(invite.expires_at).toLocaleDateString(lang === 'vi' ? 'vi-VN' : 'en-US')}</td>
                      <td>
                        {status === 'pending' && (
                          <div className="flex flex-wrap items-center gap-3">
                            <button
                              type="button"
                              className="font-bold text-accent cursor-pointer hover:underline disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                              disabled={busyId === invite.id}
                              onClick={() => handleResend(invite)}
                            >
                              {lang === 'vi' ? 'Gửi lại' : 'Resend'}
                            </button>
                            <button
                              type="button"
                              className="text-danger font-bold cursor-pointer hover:underline disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                              disabled={busyId === invite.id}
                              onClick={() => handleRevoke(invite)}
                            >
                              {t('admin.inviteRevokeBtn')}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Users */}
      <section className="card p-5 sm:p-6 space-y-4" aria-labelledby="users-title">
        <h2 id="users-title" className="text-sm font-bold text-fg">{t('admin.usersSectionTitle')}</h2>

        {users === null ? (
          <p className="text-xs text-fg-muted">{t('admin.loading')}</p>
        ) : users.length === 0 ? (
          <p className="text-xs text-fg-muted">{t('admin.usersEmpty')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">{t('admin.userColEmail')}</th>
                  <th scope="col">{t('admin.userColName')}</th>
                  <th scope="col">{t('admin.userColRole')}</th>
                  <th scope="col">{t('admin.userColStatus')}</th>
                  <th scope="col">{t('admin.userColActions')}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="text-fg">{user.email}</td>
                    <td className="text-fg-secondary">{user.full_name}</td>
                    <td className="text-fg-secondary">{roleLabel(user.role, lang)}</td>
                    <td>
                      {user.is_active ? (
                        <span className="text-fg-muted">{t('admin.userActive')}</span>
                      ) : (
                        <span className="badge badge-danger text-[9px] font-bold inline-flex items-center gap-1">
                          <Lock size={10} /> {t('admin.userLocked')}
                        </span>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-3 flex-wrap">
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 min-h-[28px] font-bold cursor-pointer hover:underline disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                          style={{ color: user.is_active ? 'var(--danger)' : 'var(--success)' }}
                          disabled={busyId === user.id}
                          onClick={() => toggleUserStatus(user)}
                        >
                          {user.is_active ? <Lock size={12} /> : <Unlock size={12} />}
                          {user.is_active ? t('admin.userLockBtn') : t('admin.userUnlockBtn')}
                        </button>
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 min-h-[28px] font-bold text-accent-text-safe cursor-pointer hover:underline disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                          disabled={busyId === user.id}
                          onClick={() => handleResetPassword(user)}
                        >
                          <KeyRound size={12} /> {t('admin.resetPassword')}
                        </button>
                        {user.role === 'STUDENT' && (
                          <Link
                            to={`/admin/students/${user.id}`}
                            className="inline-flex items-center gap-1.5 min-h-[28px] font-bold text-accent-text-safe hover:underline outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                          >
                            <User size={12} /> {lang === 'vi' ? 'Xem hồ sơ 360' : 'View 360'}
                          </Link>
                        )}
                        {user.role === 'INSTRUCTOR' && (
                          <Link
                            to={`/admin/instructors/${user.id}`}
                            className="inline-flex items-center gap-1.5 min-h-[28px] font-bold text-accent-text-safe hover:underline outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
                          >
                            <User size={12} /> {lang === 'vi' ? 'Xem hồ sơ 360' : 'View 360'}
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showInviteModal && (
        <InviteModal
          onClose={() => setShowInviteModal(false)}
          onSent={(invite) => {
            setInvites((rows) => [invite, ...(rows || [])]);
            setShowInviteModal(false);
          }}
        />
      )}

      <ConfirmDialog
        open={!!confirmAction}
        title={confirmAction?.type === 'resendInvite' ? (lang === 'vi' ? 'Gửi lại lời mời?' : 'Resend this invitation?') :
               confirmAction?.type === 'revokeInvite' ? t('admin.inviteRevokeConfirm') :
               confirmAction?.type === 'lockUser' ? t('admin.userLockConfirm') :
               confirmAction?.type === 'resetPassword' ? t('admin.resetPasswordTitle') :
               (lang === 'vi' ? 'Xác nhận mở khóa tài khoản?' : 'Unlock this account?')}
        message={confirmAction?.type === 'resendInvite'
          ? (lang === 'vi' ? 'Token cũ sẽ hết hiệu lực và hệ thống tạo link mới.' : 'The old token will be invalidated and a new link will be sent.')
          : confirmAction?.type === 'resetPassword'
          ? t('admin.resetPasswordConfirm')
          : (lang === 'vi' ? 'Thao tác này sẽ được ghi vào nhật ký hệ thống (Audit Log).' : 'This action will be recorded in the Audit Log.')}
        confirmLabel={t('admin.confirmBtn')}
        cancelLabel={t('admin.cancelBtn')}
        danger={confirmAction?.type === 'lockUser' || confirmAction?.type === 'revokeInvite'}
        onConfirm={executeAction}
        onCancel={() => setConfirmAction(null)}
      >
        {(confirmAction?.type === 'lockUser' || confirmAction?.type === 'unlockUser') && (
          <div className="mt-2">
            <label className="block text-xs font-bold text-fg-secondary mb-1">
              {lang === 'vi' ? 'Lý do' : 'Reason'} <span className="text-danger">*</span>
            </label>
            <textarea
              className="input text-xs w-full resize-none h-20"
              placeholder={lang === 'vi' ? 'Vui lòng ghi rõ lý do...' : 'Please specify a reason...'}
              value={confirmAction.reason}
              onChange={e => setConfirmAction(p => ({ ...p, reason: e.target.value }))}
              autoFocus
            />
          </div>
        )}
      </ConfirmDialog>
    </div>
  );
}

function InviteModal({ onClose, onSent }) {
  const { t, lang } = useLanguage();
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('STUDENT');
  // B5: lớp gán ngay cho giảng viên được mời. Chỉ nạp danh sách khi admin thật
  // sự chọn role INSTRUCTOR -- mời sinh viên là trường hợp phổ biến hơn nhiều,
  // không cần trả giá một request thừa cho nó.
  const [sections, setSections] = useState(null);
  const [sectionId, setSectionId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const panelRef = useRef(null);
  const firstRef = useRef(null);
  const restoreRef = useRef(null);

  useEffect(() => {
    restoreRef.current = document.activeElement;
    firstRef.current?.focus();
    const selector =
      'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !panelRef.current) return;
      const items = Array.from(panelRef.current.querySelectorAll(selector));
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      if (restoreRef.current instanceof HTMLElement) restoreRef.current.focus();
    };
  }, [onClose]);

  useEffect(() => {
    if (role !== 'INSTRUCTOR' || sections !== null) return;
    let alive = true;
    getAdminSections()
      .then((payload) => {
        if (alive) setSections(payload?.items || []);
      })
      .catch(() => {
        // Không chặn việc gửi lời mời chỉ vì không nạp được danh sách lớp --
        // gán lớp là tuỳ chọn, admin vẫn gán tay ở màn Lớp học được.
        if (alive) setSections([]);
      });
    return () => {
      alive = false;
    };
  }, [role, sections]);

  const unassignedSections = (sections || []).filter((row) => !row.instructorId);

  function submit(event) {
    event.preventDefault();
    if (!email.trim() || !fullName.trim()) return;
    setBusy(true);
    setError('');
    createInvite({
      email: email.trim(),
      fullName: fullName.trim(),
      role,
      sectionId: role === 'INSTRUCTOR' ? sectionId || null : null,
    })
      .then(onSent)
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusy(false));
  }

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="invite-modal-title"
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-md rounded-2xl border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-line">
          <h2 id="invite-modal-title" className="font-display text-sm font-bold text-fg">
            {t('admin.inviteModalTitle')}
          </h2>
          <button
            type="button"
            className="btn-ghost w-10 h-10 inline-flex items-center justify-center rounded-lg cursor-pointer text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={onClose}
            aria-label={t('admin.cancelBtn')}
          >
            <X size={15} />
          </button>
        </div>

        <form onSubmit={submit} className="p-5 space-y-4 text-left">
          {error && (
            <p className="flex items-center gap-2 text-xs text-danger" role="alert">
              <AlertCircle size={14} className="shrink-0" />{error}
            </p>
          )}
          <div>
            <label htmlFor="invite-email" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {t('admin.inviteEmailLabel')}
            </label>
            <input
              ref={firstRef}
              id="invite-email"
              type="email"
              required
              className="input text-[13px] w-full"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="invite-fullname" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {t('admin.inviteFullNameLabel')}
            </label>
            <input
              id="invite-fullname"
              type="text"
              required
              className="input text-[13px] w-full"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="invite-role" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {t('admin.inviteRoleLabel')}
            </label>
            <select
              id="invite-role"
              className="input text-[13px] w-full"
              value={role}
              onChange={(event) => {
                setRole(event.target.value);
                if (event.target.value !== 'INSTRUCTOR') setSectionId('');
              }}
            >
              {INVITABLE_ROLES.map((value) => (
                <option key={value} value={value}>{roleLabel(value, lang)}</option>
              ))}
            </select>
          </div>
          {role === 'INSTRUCTOR' && (
            <div>
              <label htmlFor="invite-section" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
                {t('admin.inviteSectionLabel')}
              </label>
              <select
                id="invite-section"
                className="input text-[13px] w-full"
                value={sectionId}
                onChange={(event) => setSectionId(event.target.value)}
                disabled={sections === null}
              >
                <option value="">{t('admin.inviteSectionNone')}</option>
                {unassignedSections.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.courseCode} · {row.sectionCode} · {row.term}
                  </option>
                ))}
              </select>
              <p className="mt-1.5 text-[11px] text-fg-muted">
                {sections !== null && unassignedSections.length === 0
                  ? t('admin.inviteSectionEmpty')
                  : t('admin.inviteSectionHint')}
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn btn-outline text-[13px] px-4 min-h-10 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent" onClick={onClose}>
              {t('admin.cancelBtn')}
            </button>
            <button
              type="submit"
              className="btn btn-accent text-[13px] px-4 min-h-10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent"
              disabled={busy || !email.trim() || !fullName.trim()}
            >
              {busy ? t('admin.inviteSendingBtn') : t('admin.inviteSendBtn')}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
