import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Check, Building2 } from 'lucide-react';
import AuthCardLayout from './AuthCardLayout';
import { requestOrgAccess } from '../../lib/authClient';
import { useLanguage } from '../../context/LanguageContext';

const ROLES = [
  { value: '', labelVi: 'Chưa chắc / khác', labelEn: 'Not sure / other' },
  { value: 'admin', labelVi: 'Quản trị viên / Phòng đào tạo', labelEn: 'Admin / Academic office' },
  { value: 'instructor', labelVi: 'Giảng viên', labelEn: 'Instructor' },
  { value: 'student', labelVi: 'Sinh viên', labelEn: 'Student' },
];

export default function RequestAccessScreen() {
  const navigate = useNavigate();
  const { lang } = useLanguage();

  const [form, setForm] = useState({ institutionName: '', contactName: '', email: '', roleInterested: '', message: '' });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const update = (field) => (e) => {
    setForm((p) => ({ ...p, [field]: e.target.value }));
    setErrors((p) => ({ ...p, [field]: undefined, form: undefined }));
  };

  function validate() {
    const e = {};
    if (!form.institutionName.trim()) e.institutionName = lang === 'vi' ? 'Bắt buộc.' : 'Required.';
    if (!form.contactName.trim()) e.contactName = lang === 'vi' ? 'Bắt buộc.' : 'Required.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = lang === 'vi' ? 'Email không hợp lệ.' : 'Invalid email.';
    return e;
  }

  async function handleSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }

    setLoading(true);
    try {
      await requestOrgAccess(form);
      setSuccess(true);
    } catch (err) {
      setErrors({ form: err.message || (lang === 'vi' ? 'Không thể gửi yêu cầu. Vui lòng thử lại.' : 'Could not send request. Please try again.') });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCardLayout
      heroTitle={lang === 'vi' ? 'Triển khai Cursus cho trường của bạn' : 'Bring Cursus to your school'}
      heroSub={lang === 'vi'
        ? 'Đội ngũ Cursus sẽ liên hệ để thiết lập tổ chức, tài khoản quản trị viên đầu tiên và mời giảng viên/sinh viên.'
        : 'Our team will reach out to set up your organization, the first admin account, and invite your teachers/students.'}
    >
      {success ? (
        <div className="text-center" style={{ padding: '8px 0' }}>
          <div className="clp-successicon">
            <Check size={26} strokeWidth={2.5} aria-hidden="true" />
          </div>
          <h2 className="clp-cardheading">
            {lang === 'vi' ? 'Đã gửi yêu cầu!' : 'Request sent!'}
          </h2>
          <p className="clp-cardsub">
            {lang === 'vi'
              ? 'Cảm ơn bạn. Chúng tôi sẽ phản hồi sớm qua email đã cung cấp.'
              : "Thanks — we'll follow up at the email address you provided."}
          </p>
          <button type="button" onClick={() => navigate('/')} className="clp-submit" style={{ marginTop: 28 }}>
            {lang === 'vi' ? 'Về trang chủ' : 'Back to home'}
          </button>
        </div>
      ) : (
        <>
          <h2 className="clp-cardheading">
            {lang === 'vi' ? 'Yêu cầu quyền truy cập cho tổ chức' : 'Request access for your organization'}
          </h2>

          {errors.form && <div role="alert" className="clp-alert">{errors.form}</div>}

          <form onSubmit={handleSubmit} className="clp-form" noValidate>
            <div className="clp-field">
              <label htmlFor="ra-institution" className="clp-label">
                {lang === 'vi' ? 'Tên trường / tổ chức' : 'Institution name'}
              </label>
              <div className="clp-inputwrap">
                <span className="clp-inputicon"><Building2 size={18} strokeWidth={2} aria-hidden="true" /></span>
                <input
                  id="ra-institution"
                  type="text"
                  className="clp-input"
                  value={form.institutionName}
                  disabled={loading}
                  aria-invalid={!!errors.institutionName}
                  onChange={update('institutionName')}
                  autoFocus
                />
              </div>
              {errors.institutionName && <p className="clp-fielderr">{errors.institutionName}</p>}
            </div>

            <div className="clp-field">
              <label htmlFor="ra-name" className="clp-label">
                {lang === 'vi' ? 'Họ tên người liên hệ' : 'Contact name'}
              </label>
              <input
                id="ra-name"
                type="text"
                className="clp-input clp-input--noicon"
                value={form.contactName}
                disabled={loading}
                aria-invalid={!!errors.contactName}
                onChange={update('contactName')}
              />
              {errors.contactName && <p className="clp-fielderr">{errors.contactName}</p>}
            </div>

            <div className="clp-field">
              <label htmlFor="ra-email" className="clp-label">Email</label>
              <input
                id="ra-email"
                type="email"
                className="clp-input clp-input--noicon"
                value={form.email}
                disabled={loading}
                aria-invalid={!!errors.email}
                onChange={update('email')}
              />
              {errors.email && <p className="clp-fielderr">{errors.email}</p>}
            </div>

            <div className="clp-field">
              <label htmlFor="ra-role" className="clp-label">
                {lang === 'vi' ? 'Vai trò của bạn' : 'Your role'}
              </label>
              <select
                id="ra-role"
                className="clp-select"
                value={form.roleInterested}
                disabled={loading}
                onChange={update('roleInterested')}
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{lang === 'vi' ? r.labelVi : r.labelEn}</option>
                ))}
              </select>
            </div>

            <div className="clp-field">
              <label htmlFor="ra-message" className="clp-label">
                {lang === 'vi' ? 'Ghi chú (không bắt buộc)' : 'Message (optional)'}
              </label>
              <textarea
                id="ra-message"
                rows={3}
                className="clp-textarea"
                value={form.message}
                disabled={loading}
                onChange={update('message')}
              />
            </div>

            <button type="submit" className="clp-submit" disabled={loading}>
              {loading ? (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                  </svg>
                  {lang === 'vi' ? 'Đang gửi…' : 'Sending…'}
                </>
              ) : (
                <>
                  {lang === 'vi' ? 'Gửi yêu cầu' : 'Send request'}
                  <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
                </>
              )}
            </button>
          </form>
        </>
      )}
    </AuthCardLayout>
  );
}
