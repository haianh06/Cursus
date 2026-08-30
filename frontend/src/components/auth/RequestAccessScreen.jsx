import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Building2 } from 'lucide-react';
import AuthLayout from './AuthLayout';
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
    <AuthLayout
      title={lang === 'vi' ? 'Triển khai Cursus cho trường của bạn' : 'Bring Cursus to your school'}
      subtitle={lang === 'vi'
        ? 'Đội ngũ Cursus sẽ liên hệ để thiết lập tổ chức, tài khoản quản trị viên đầu tiên và mời giảng viên/sinh viên.'
        : 'Our team will reach out to set up your organization, the first admin account, and invite your teachers/students.'}
      cardWidth={480}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 relative">
        <div className="mb-6">
          <Link to="/" className="link-auth-secondary hover:underline group text-fg-secondary">
            <ArrowLeft size={16} className="icon-arrow" />
            {lang === 'vi' ? 'Về trang chủ' : 'Back to home'}
          </Link>
        </div>

        {success ? (
          <div className="text-center space-y-4 py-4">
            <div className="w-14 h-14 rounded-full bg-success-soft text-success flex items-center justify-center mx-auto">
              <Check size={26} />
            </div>
            <h2 className="font-display text-lg font-bold text-fg">
              {lang === 'vi' ? 'Đã gửi yêu cầu!' : 'Request sent!'}
            </h2>
            <p className="text-sm text-fg-secondary">
              {lang === 'vi'
                ? 'Cảm ơn bạn. Chúng tôi sẽ phản hồi sớm qua email đã cung cấp.'
                : 'Thanks — we\'ll follow up at the email address you provided.'}
            </p>
            <button type="button" onClick={() => navigate('/')} className="btn-auth-primary mt-2" style={{ width: '100%' }}>
              {lang === 'vi' ? 'Về trang chủ' : 'Back to home'}
            </button>
          </div>
        ) : (
          <>
            {errors.form && (
              <div role="alert" className="p-3.5 rounded-xl bg-danger/10 border border-danger/20 text-sm font-semibold text-danger mb-4">
                {errors.form}
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div>
                <label htmlFor="ra-institution" className="block text-sm font-semibold mb-2 text-fg-secondary">
                  {lang === 'vi' ? 'Tên trường / tổ chức' : 'Institution name'}
                </label>
                <div className="relative">
                  <Building2 size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
                  <input id="ra-institution" type="text" className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-4 text-sm text-fg outline-none input-auth-field"
                    value={form.institutionName} disabled={loading} onChange={update('institutionName')} />
                </div>
                {errors.institutionName && <p className="text-sm mt-1.5 font-semibold text-danger">{errors.institutionName}</p>}
              </div>

              <div>
                <label htmlFor="ra-name" className="block text-sm font-semibold mb-2 text-fg-secondary">
                  {lang === 'vi' ? 'Họ tên người liên hệ' : 'Contact name'}
                </label>
                <input id="ra-name" type="text" className="w-full h-[52px] bg-surface border border-line rounded-xl px-4 text-sm text-fg outline-none input-auth-field"
                  value={form.contactName} disabled={loading} onChange={update('contactName')} />
                {errors.contactName && <p className="text-sm mt-1.5 font-semibold text-danger">{errors.contactName}</p>}
              </div>

              <div>
                <label htmlFor="ra-email" className="block text-sm font-semibold mb-2 text-fg-secondary">Email</label>
                <input id="ra-email" type="email" className="w-full h-[52px] bg-surface border border-line rounded-xl px-4 text-sm text-fg outline-none input-auth-field"
                  value={form.email} disabled={loading} onChange={update('email')} />
                {errors.email && <p className="text-sm mt-1.5 font-semibold text-danger">{errors.email}</p>}
              </div>

              <div>
                <label htmlFor="ra-role" className="block text-sm font-semibold mb-2 text-fg-secondary">
                  {lang === 'vi' ? 'Vai trò của bạn' : 'Your role'}
                </label>
                <select id="ra-role" className="w-full h-[52px] bg-surface border border-line rounded-xl px-4 text-sm text-fg outline-none cursor-pointer"
                  value={form.roleInterested} disabled={loading} onChange={update('roleInterested')}>
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>{lang === 'vi' ? r.labelVi : r.labelEn}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="ra-message" className="block text-sm font-semibold mb-2 text-fg-secondary">
                  {lang === 'vi' ? 'Ghi chú (không bắt buộc)' : 'Message (optional)'}
                </label>
                <textarea id="ra-message" rows={3} className="w-full bg-surface border border-line rounded-xl px-4 py-3 text-sm text-fg outline-none input-auth-field resize-none"
                  value={form.message} disabled={loading} onChange={update('message')} />
              </div>

              <button type="submit" className="btn-auth-primary mt-2" disabled={loading} style={{ width: '100%' }}>
                <span className="flex items-center gap-2">
                  {lang === 'vi' ? 'Gửi yêu cầu' : 'Send request'}
                  <ArrowRight size={16} className="icon-arrow" />
                </span>
              </button>
            </form>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
