import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sun, Moon, Globe, LogOut, Bell, MessageSquare, Trash2, BrainCircuit } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useLanguage } from '../../context/LanguageContext';
import { useCursus } from '../../context/CursusContext';
import { ROLE_LABEL, ROLE_DESC } from '../../constants/roles';
import { deleteMyPersonalData, getMemoryConsent, setMemoryConsent, forgetAllMemory } from '../../lib/api';

/**
 * Shared Hồ sơ & Cài đặt screen — same component for all 3 roles (student/
 * instructor/admin), reached via the Topbar avatar button. Per docs/frontend
 * §screen-consistency: one settings surface, not a per-role reimplementation.
 */
export default function SettingsScreen({ user, onLogout }) {
  const { theme, toggleTheme } = useTheme();
  const { lang, toggleLang } = useLanguage();
  const { showMascot, toggleMascot, notifications, markAllNotificationsRead } = useCursus();
  const unread = notifications.filter((n) => !n.read).length;
  const navigate = useNavigate();
  const [deleteState, setDeleteState] = useState({ busy: false, result: null, error: null });
  const [memoryConsent, setMemoryConsentState] = useState(null); // null = loading
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [memoryForgetDone, setMemoryForgetDone] = useState(false);

  useEffect(() => {
    if (user.role !== 'student') return;
    let cancelled = false;
    getMemoryConsent()
      .then((res) => { if (!cancelled) setMemoryConsentState(Boolean(res.granted)); })
      .catch(() => { if (!cancelled) setMemoryConsentState(false); });
    return () => { cancelled = true; };
  }, [user.role]);

  const handleToggleMemoryConsent = async () => {
    if (memoryBusy || memoryConsent === null) return;
    setMemoryBusy(true);
    try {
      const res = await setMemoryConsent(!memoryConsent);
      setMemoryConsentState(Boolean(res.granted));
    } catch {
      /* leave state unchanged, user can retry */
    } finally {
      setMemoryBusy(false);
    }
  };

  const handleForgetAllMemory = async () => {
    const confirmed = window.confirm(
      lang === 'vi'
        ? 'Xoá vĩnh viễn toàn bộ ghi nhớ của Trợ lý Cursus về bạn? Hành động này không thể hoàn tác.'
        : "Permanently delete everything Cursus Assistant has remembered about you? This can't be undone."
    );
    if (!confirmed) return;
    setMemoryBusy(true);
    try {
      await forgetAllMemory();
      setMemoryForgetDone(true);
    } catch {
      /* ignore — user can retry */
    } finally {
      setMemoryBusy(false);
    }
  };

  const handleLogout = async () => {
    await onLogout();
    navigate(user.isDemo ? '/request-access' : '/login', { replace: true });
  };

  const handleDeletePersonalData = async () => {
    const confirmed = window.confirm(
      lang === 'vi'
        ? 'Xoá vĩnh viễn toàn bộ phản tư và lịch sử hỏi đáp với Cursus Assistant của bạn? Hành động này không thể hoàn tác.'
        : 'Permanently delete all of your reflections and Cursus Assistant chat history? This cannot be undone.'
    );
    if (!confirmed) return;
    setDeleteState({ busy: true, result: null, error: null });
    try {
      const res = await deleteMyPersonalData();
      setDeleteState({ busy: false, result: res, error: null });
    } catch (err) {
      setDeleteState({ busy: false, result: null, error: err.message || String(err) });
    }
  };

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 max-w-2xl animate-fade-up">
      <div className="text-left border-b border-line pb-4">
        <h1 className="font-display text-xl font-bold text-fg">
          {lang === 'vi' ? 'Hồ sơ & Cài đặt' : 'Profile & Settings'}
        </h1>
      </div>

      {/* Profile card */}
      <div className="card p-5 flex items-center gap-4 text-left">
        <span className="w-14 h-14 rounded-full bg-accent-soft text-accent-text-safe flex items-center justify-center text-xl font-bold shrink-0 select-none">
          {user.name?.trim()?.[0]?.toUpperCase() || '?'}
        </span>
        <div className="min-w-0">
          <p className="text-base font-bold text-fg truncate">{user.name}</p>
          <p className="text-xs text-fg-muted truncate">{user.email}</p>
          <span className="badge badge-neutral text-[9px] font-bold mt-1.5 inline-block">
            {(ROLE_LABEL[lang] || ROLE_LABEL.vi)[user.role]} · {(ROLE_DESC[lang] || ROLE_DESC.vi)[user.role]}
          </span>
        </div>
      </div>

      {/* Preferences */}
      <div className="text-left">
        <h2 className="text-xs font-bold uppercase tracking-wider text-fg-muted mb-3">
          {lang === 'vi' ? 'Tuỳ chỉnh' : 'Preferences'}
        </h2>
        <div className="card divide-y divide-line">
          <button
            type="button"
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-4 py-3.5 cursor-pointer hover:bg-surface-elevated transition-colors"
          >
            <span className="flex items-center gap-3 text-sm text-fg">
              {theme === 'dark' ? <Sun size={16} className="text-fg-muted" /> : <Moon size={16} className="text-fg-muted" />}
              {lang === 'vi' ? 'Giao diện' : 'Appearance'}
            </span>
            <span className="text-xs font-bold text-fg-muted">{theme === 'dark' ? (lang === 'vi' ? 'Tối' : 'Dark') : (lang === 'vi' ? 'Sáng' : 'Light')}</span>
          </button>

          <button
            type="button"
            onClick={toggleLang}
            className="w-full flex items-center justify-between px-4 py-3.5 cursor-pointer hover:bg-surface-elevated transition-colors"
          >
            <span className="flex items-center gap-3 text-sm text-fg">
              <Globe size={16} className="text-fg-muted" />
              {lang === 'vi' ? 'Ngôn ngữ' : 'Language'}
            </span>
            <span className="text-xs font-bold text-fg-muted">{lang === 'vi' ? 'Tiếng Việt' : 'English'}</span>
          </button>

          <div className="w-full flex items-center justify-between px-4 py-3.5">
            <span className="flex items-center gap-3 text-sm text-fg">
              <MessageSquare size={16} className="text-fg-muted" />
              {lang === 'vi' ? 'Trợ lý Cursus nổi' : 'Floating Cursus Assistant'}
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={showMascot}
              aria-label={lang === 'vi' ? 'Trợ lý Cursus nổi' : 'Floating Cursus Assistant'}
              onClick={toggleMascot}
              className={`relative w-10 h-6 rounded-full transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent border border-line ${showMascot ? 'bg-accent' : 'bg-surface-elevated'}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${showMascot ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
          </div>

          <div className="w-full flex items-center justify-between px-4 py-3.5">
            <span className="flex items-center gap-3 text-sm text-fg">
              <Bell size={16} className="text-fg-muted" />
              {lang === 'vi' ? 'Thông báo chưa đọc' : 'Unread notifications'}
            </span>
            {unread > 0 ? (
              <button type="button" onClick={markAllNotificationsRead} className="text-xs font-bold text-accent-text-safe cursor-pointer">
                {unread} · {lang === 'vi' ? 'đánh dấu đã đọc' : 'mark read'}
              </button>
            ) : (
              <span className="text-xs font-bold text-fg-muted">{lang === 'vi' ? 'Không có' : 'None'}</span>
            )}
          </div>
        </div>
      </div>

      {/* Assistant memory (student only) — consent + storage management for
          src/services/ai/student_memory_service.py. Turning this on lets the
          assistant's answers eventually draw on remembered facts once that
          integration is deliberately wired up; today it only controls
          whether facts get saved/shown at all. */}
      {user.role === 'student' && (
        <div className="text-left">
          <h2 className="text-xs font-bold uppercase tracking-wider text-fg-muted mb-3">
            {lang === 'vi' ? 'Bộ nhớ Trợ lý Cursus' : 'Cursus Assistant memory'}
          </h2>
          <div className="card divide-y divide-line">
            <div className="w-full flex items-center justify-between px-4 py-3.5">
              <span className="flex items-start gap-3 text-sm text-fg min-w-0">
                <BrainCircuit size={16} className="text-fg-muted shrink-0 mt-0.5" />
                <span className="min-w-0">
                  <span className="block">{lang === 'vi' ? 'Ghi nhớ xuyên phiên trò chuyện' : 'Remember across chat sessions'}</span>
                  <span className="block text-xs text-fg-muted mt-0.5">
                    {lang === 'vi'
                      ? 'Mặc định TẮT. Khi bật, Trợ lý có thể lưu vài sở thích/điểm yếu bạn nhắc tới để tham khảo sau này.'
                      : "Off by default. When on, the Assistant may save a few preferences/weak topics you mention for later reference."}
                  </span>
                </span>
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={Boolean(memoryConsent)}
                aria-label={lang === 'vi' ? 'Ghi nhớ xuyên phiên trò chuyện' : 'Remember across chat sessions'}
                onClick={handleToggleMemoryConsent}
                disabled={memoryConsent === null || memoryBusy}
                className={`relative w-10 h-6 rounded-full transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent border border-line shrink-0 disabled:opacity-50 ${memoryConsent ? 'bg-accent' : 'bg-surface-elevated'}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${memoryConsent ? 'translate-x-4' : 'translate-x-0'}`} />
              </button>
            </div>

            {memoryConsent && (
              <div className="px-4 py-3.5">
                <button
                  type="button"
                  onClick={handleForgetAllMemory}
                  disabled={memoryBusy}
                  className="text-xs font-bold text-danger hover:underline cursor-pointer disabled:opacity-50"
                >
                  {lang === 'vi' ? 'Xoá toàn bộ ghi nhớ' : 'Forget everything'}
                </button>
                {memoryForgetDone && (
                  <p className="text-xs font-semibold text-success mt-2" role="status">
                    {lang === 'vi' ? 'Đã xoá toàn bộ ghi nhớ.' : 'Everything has been forgotten.'}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Danger zone */}
      <div className="text-left">
        <h2 className="text-xs font-bold uppercase tracking-wider text-fg-muted mb-3">
          {lang === 'vi' ? 'Tài khoản' : 'Account'}
        </h2>
        <button
          type="button"
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3.5 rounded-[var(--radius-md)] border border-line text-sm font-semibold text-danger hover:bg-danger/10 hover:border-danger/40 transition-colors cursor-pointer"
        >
          <LogOut size={16} />
          {lang === 'vi' ? 'Đăng xuất' : 'Log out'}
        </button>

        {user.role === 'student' && (
          <div className="mt-3">
            <button
              type="button"
              onClick={handleDeletePersonalData}
              disabled={deleteState.busy}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-[var(--radius-md)] border border-line text-sm font-semibold text-danger hover:bg-danger/10 hover:border-danger/40 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 size={16} />
              {deleteState.busy
                ? lang === 'vi' ? 'Đang xoá...' : 'Deleting...'
                : lang === 'vi' ? 'Yêu cầu xoá toàn bộ dữ liệu của tôi' : 'Request deletion of all my data'}
            </button>
            <p className="text-xs text-fg-muted mt-2">
              {lang === 'vi'
                ? 'Xoá sạch phản tư và lịch sử hỏi đáp của riêng bạn. Số liệu đã gộp ẩn danh cho lớp/trường không bị ảnh hưởng.'
                : "Wipes your own reflections and Q&A chat history. Anonymized class/school-wide aggregates are not affected."}
            </p>
            {deleteState.result && (
              <p className="text-xs font-semibold text-success mt-2" role="status">
                {lang === 'vi'
                  ? `Đã xoá ${deleteState.result.reflectionsDeleted} phản tư, ${deleteState.result.conversationsDeleted} cuộc trò chuyện (${deleteState.result.messagesDeleted} tin nhắn).`
                  : `Deleted ${deleteState.result.reflectionsDeleted} reflection(s), ${deleteState.result.conversationsDeleted} conversation(s) (${deleteState.result.messagesDeleted} message(s)).`}
              </p>
            )}
            {deleteState.error && (
              <p className="text-xs font-semibold text-danger mt-2" role="alert">
                {lang === 'vi' ? 'Có lỗi xảy ra, thử lại sau.' : 'Something went wrong, please try again.'}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
