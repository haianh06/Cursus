import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, FlaskConical, CheckCircle2, Star, GraduationCap } from 'lucide-react';
import { startDemoSession } from '../../lib/authClient';
import { useLanguage } from '../../context/LanguageContext';
import CursusAuthHeader from './CursusAuthHeader';
import BrandAsset from '../brand/BrandAsset';

/**
 * Man "Chon vai tro de trai nghiem" — dung lai theo screenshot tham chieu
 * 1672x941. Screenshot la nguon su that cho bo cuc, ty le, khoang cach,
 * typography va mau; moi con so trong file nay va trong
 * src/styles/cursus-brand.css deu doi chieu voi no.
 *
 * Moi card chi gom dung 5 phan: illustration Curi, ten role, mo ta, benefit
 * strip, CTA. Khong them badge phu, KPI, tooltip hay CTA thu hai.
 *
 * `accent` chi cham toi CTA va benefit strip. Curi giu mau teal canonical o
 * ca ba card — do la thu giu ba card khac accent van doc ra la mot san pham.
 */
const ROLE_CARDS = [
  {
    role: 'student',
    asset: 'curi-student.png',
    recommended: true,
    titleVi: 'Sinh viên',
    titleEn: 'Student',
    descVi: 'Kế hoạch học tập theo tuần, nội dung có trích nguồn học liệu, theo dõi tiến độ.',
    descEn: 'Weekly study plans, cited course material, progress tracking.',
    benefitVi: 'Trải nghiệm học tập cá nhân hóa',
    benefitEn: 'A personalised learning experience',
  },
  {
    role: 'instructor',
    asset: 'curi-instructor.png',
    titleVi: 'Giảng viên',
    titleEn: 'Instructor',
    descVi: 'Giám sát lớp học, cảnh báo sinh viên nguy cơ, duyệt can thiệp cơ chế an toàn học thuật.',
    descEn: 'Class oversight, at-risk alerts, academic-integrity guardrail review.',
    benefitVi: 'Quản lý và hỗ trợ hiệu quả',
    benefitEn: 'Manage and support effectively',
  },
  {
    role: 'admin',
    asset: 'curi-admin.png',
    titleVi: 'Quản trị viên',
    titleEn: 'Administrator',
    descVi: 'Quản lý curriculum, mời tài khoản, theo dõi KPI toàn trường.',
    descEn: 'Curriculum management, invitations, school-wide KPIs.',
    benefitVi: 'Vận hành hệ thống toàn diện',
    benefitEn: 'Operate the whole system',
  },
];

/**
 * Diem vao cong khai, khong can tai khoan. Moi card mo mot phien that, ngan
 * han (POST /auth/demo-session) gioi han trong to chuc cach ly "Cursus
 * Sandbox University" — khong bao gio cham du lieu that.
 */
export default function DemoSelectRoleScreen() {
  const navigate = useNavigate();
  const { lang } = useLanguage();
  const vi = lang === 'vi';
  const [loadingRole, setLoadingRole] = useState(null);
  const [error, setError] = useState('');

  async function enterDemo(role) {
    setLoadingRole(role);
    setError('');
    try {
      await startDemoSession(role);
      navigate(`/${role}`, { replace: true });
      window.location.reload();
    } catch (err) {
      setError(err.message || (vi
        ? 'Không thể bắt đầu trải nghiệm sandbox. Vui lòng thử lại.'
        : 'Could not start the sandbox trial. Please try again.'));
      setLoadingRole(null);
    }
  }

  return (
    <div className="cb-page cursus-brand-scope">
      {/* ── Lop trang tri ──────────────────────────────────────────
          Thu tu lop: background -> decorative illustration -> main content
          -> interactive controls. Ca hai nam duoi .cb-content, khong nhan
          chuot, va bi an hoan toan duoi 1200px — decoration bi bo truoc khi
          hy sinh be rong doc duoc cua card.
          Curi ben trai co the tran mot phan ra ngoai mep trai nhu anh tham
          chieu; no duoc dat absolute nen khong lam doi kich thuoc hay vi tri
          cua container chinh. */}
      <div className="cb-decor cb-decor--curi" aria-hidden="true">
        <BrandAsset
          file="curi-welcome.png"
          width={620}
          height={650}
          style={{ width: '100%', height: 'auto', objectFit: 'contain' }}
          note={vi ? 'Curi chào đón — kính tròn, nháy mắt, một cánh vẫy' : 'Welcoming Curi'}
        />
      </div>
      <div className="cb-decor cb-decor--campus" aria-hidden="true">
        <BrandAsset
          file="sandbox-university.png"
          width={1040}
          height={680}
          style={{ width: '100%', height: 'auto', objectFit: 'contain' }}
          note={vi ? 'Toà nhà đại học 3D, nền trong suốt' : 'University building'}
        />
      </div>

      <div className="cb-shell cb-content">
        <CursusAuthHeader showBackLink showLoginLink />

        <main className="cb-main">
          {/* ── Hero ── */}
          <div className="cb-hero">
            <span className="cb-badge">
              <FlaskConical size={18} strokeWidth={1.9} aria-hidden="true" />
              {vi ? 'Sandbox — dữ liệu giả lập' : 'Sandbox — synthetic data'}
            </span>

            <h1 className="cb-h1">
              {vi ? 'Chọn vai trò để trải nghiệm' : 'Pick a role to explore'}
            </h1>

            {/* Ngat dong dat tuong minh: anh tham chieu ngat ngay sau dau
                nhay dong cua "Cursus Sandbox University". Neu de trinh duyet
                tu ngat theo max-width thi diem ngat troi moi khi thuoc do
                font doi (da xay ra khi chuyen Poppins -> Be Vietnam Pro).
                .cb-sub__br bi tat duoi 1200px nen mobile van ngat tu nhien. */}
            <p className="cb-sub">
              {vi ? 'Không cần tạo tài khoản. Bạn sẽ vào “Cursus Sandbox University”'
                  : 'No account needed. You’ll enter “Cursus Sandbox University”'}
              {' '}
              <br className="cb-sub__br" />
              {vi ? '— một tổ chức mẫu tách biệt hoàn toàn khỏi dữ liệu thật.'
                  : '— a sample organization fully isolated from real data.'}
            </p>
          </div>

          {error && <div role="alert" className="cb-form-alert cb-hero-alert">{error}</div>}

          {/* ── Ba role card ── */}
          <div className="cb-role-grid">
            {ROLE_CARDS.map((card) => {
              const busy = loadingRole === card.role;
              const off = loadingRole !== null;
              const title = vi ? card.titleVi : card.titleEn;
              return (
                /* Ca card la vung bam duoc, nhung no la <div> chu khong phai
                   <button>: mot <button> khong duoc chua <h2>/<p>. CTA ben
                   trong moi la control ngu nghia that va la phan tu duy nhat
                   nhan focus, nen moi card dung mot tab stop; click cua no
                   noi bot len handler nay (CTA khong co handler rieng — do la
                   thu giu mot cu click chuot khong goi enterDemo hai lan). */
                <div
                  key={card.role}
                  onClick={() => { if (!off) enterDemo(card.role); }}
                  className={`cb-role-card cursus-brand-scope--${card.role}${card.recommended ? ' cb-role-card--recommended' : ''}${off ? ' cb-role-card--off' : ''}${busy ? ' cb-role-card--busy' : ''}`}
                >
                  {card.recommended && (
                    <span className="cb-role-badge">
                      <Star size={14} strokeWidth={2.2} aria-hidden="true" />
                      {vi ? 'Được đề xuất' : 'Recommended'}
                    </span>
                  )}

                  <span className="cb-role-mascot">
                    <BrandAsset
                      file={card.asset}
                      alt={vi
                        ? `Curi đại diện cho vai trò ${title}`
                        : `Curi representing the ${title} role`}
                      width={420}
                      height={440}
                      className="cb-role-mascot__img"
                    />
                  </span>

                  <h2 className="cb-role-title">{title}</h2>
                  <p className="cb-role-desc">{vi ? card.descVi : card.descEn}</p>

                  <span className="cb-role-benefit">
                    <CheckCircle2 size={20} strokeWidth={1.9} aria-hidden="true" style={{ flexShrink: 0 }} />
                    <span>{vi ? card.benefitVi : card.benefitEn}</span>
                  </span>

                  <button
                    type="button"
                    className="cb-role-cta"
                    disabled={off}
                    aria-busy={busy || undefined}
                  >
                    {busy ? (
                      <>
                        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="cb-spin" aria-hidden="true">
                          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                        </svg>
                        {vi ? 'Đang mở sandbox…' : 'Opening sandbox…'}
                      </>
                    ) : (
                      <>
                        {vi ? `Khám phá vai trò ${title}` : `Explore as ${title}`}
                        <ArrowRight size={19} strokeWidth={2.1} aria-hidden="true" />
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>

          {/* ── Organization CTA ── */}
          <div className="cb-org-cta">
            <GraduationCap size={20} strokeWidth={1.9} aria-hidden="true" style={{ color: 'var(--cb-primary)' }} />
            <span>
              {vi
                ? 'Đại diện trường học, giảng viên hoặc nhà đầu tư?'
                : 'Represent a school, teach, or invest?'}
            </span>
            <Link to="/request-access">
              {vi ? 'Yêu cầu triển khai cho tổ chức của bạn' : 'Request institutional access'}
              <ArrowRight size={18} strokeWidth={2.1} aria-hidden="true" />
            </Link>
          </div>

          {/* Dau cham ket thuc bo cuc, giong anh tham chieu. Day khong phai
              carousel — khong co gi de lat — nen no tro va an voi tro ly. */}
          <div className="cb-pager" aria-hidden="true">
            <i /><i />
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--cb-primary)', opacity: 0.7 }}>
              <path d="M12 21c0-5 3-8 8-9-1 5-4 8-8 9zM12 21c0-5-3-8-8-9 1 5 4 8 8 9z" fill="currentColor" />
              <path d="M12 21v-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <i /><i />
          </div>
        </main>
      </div>
    </div>
  );
}
