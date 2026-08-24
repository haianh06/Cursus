import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  ShieldAlert,
  Users,
  HandHelping,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminInstructorSummary } from '../../lib/api';

/** Instructor 360 — aggregate-only view of one instructor's profile.
 * Spec: docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.4.
 *
 * Deliberately simpler than Student 360: identity + 3 aggregate cards +
 * sections taught. NO raw-data tabs, NO link down to individual students.
 * "đây là số liệu tổng hợp, KHÔNG dùng để suy ra dữ liệu của 1 sinh viên
 * cụ thể trong lớp — cố tình không có link đi sâu xuống từng sinh viên từ đây." */
export default function AdminInstructor360() {
  const { instructorId } = useParams();
  const navigate = useNavigate();
  const { lang } = useLanguage();

  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setSummary(null);
    setError(null);
    getAdminInstructorSummary(instructorId)
      .then(setSummary)
      .catch((err) => setError(err));
  }, [instructorId]);

  if (error) {
    const notFound = error.status === 404;
    return (
      <div className="p-4 md:p-6">
        <button type="button" className="btn-ghost text-[13px] mb-4 inline-flex items-center gap-1.5 cursor-pointer" onClick={() => navigate('/admin')}>
          <ArrowLeft size={14} /> {lang === 'vi' ? 'Quay lại' : 'Back'}
        </button>
        <p className="text-[14px] text-danger">
          {notFound
            ? (lang === 'vi' ? 'Không tìm thấy giảng viên.' : 'Instructor not found.')
            : (lang === 'vi' ? 'Không tải được hồ sơ.' : 'Could not load profile.')}
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 animate-fade-up max-w-[1100px] mx-auto">
      <button type="button" className="btn-ghost text-[13px] w-fit inline-flex items-center gap-1.5 cursor-pointer" onClick={() => navigate('/admin')}>
        <ArrowLeft size={14} /> {lang === 'vi' ? 'Quay lại danh bạ' : 'Back to directory'}
      </button>

      {!summary ? (
        <Loader2 size={18} className="animate-spin text-fg-muted" />
      ) : (
        <>
          {/* Identity card */}
          <section className="card p-5">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <h1 className="font-display text-xl font-bold text-fg">{summary.instructor.fullName}</h1>
                <p className="text-[12px] text-fg-muted mt-0.5">{summary.instructor.email} · <span className="mono">{summary.instructor.role}</span></p>
              </div>
              <span className={`badge text-[10px] ${summary.instructor.isActive ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'}`}>
                {summary.instructor.isActive ? (lang === 'vi' ? 'Đang hoạt động' : 'Active') : (lang === 'vi' ? 'Đã khoá' : 'Locked')}
              </span>
            </div>

            {/* 3 aggregate cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
              <div className="rounded-lg border border-line bg-surface-elevated p-3">
                <p className="text-[11px] font-semibold text-fg-muted uppercase tracking-wide flex items-center gap-1.5">
                  <Users size={12} className="text-accent" />
                  {lang === 'vi' ? 'Sĩ số' : 'Headcount'}
                </p>
                <p className="text-[20px] font-bold text-fg mt-1">{summary.headcount}</p>
                <p className="text-[11px] text-fg-muted">{lang === 'vi' ? 'sinh viên đang ghi danh' : 'enrolled students'}</p>
              </div>
              <div className="rounded-lg border border-line bg-surface-elevated p-3">
                <p className="text-[11px] font-semibold text-fg-muted uppercase tracking-wide flex items-center gap-1.5">
                  <ShieldAlert size={12} className="text-warning" />
                  {lang === 'vi' ? 'Khối lượng rủi ro' : 'Risk load'}
                </p>
                <p className="text-[20px] font-bold text-fg mt-1">{summary.riskLoad.openSignals}</p>
                <p className="text-[11px] text-fg-muted">{lang === 'vi' ? 'tín hiệu chưa xử lý' : 'open signal(s)'}</p>
              </div>
              <div className="rounded-lg border border-line bg-surface-elevated p-3">
                <p className="text-[11px] font-semibold text-fg-muted uppercase tracking-wide flex items-center gap-1.5">
                  <HandHelping size={12} className="text-success" />
                  {lang === 'vi' ? 'Số lần can thiệp' : 'Interventions'}
                </p>
                <p className="text-[20px] font-bold text-fg mt-1">{summary.interventionCount}</p>
                <p className="text-[11px] text-fg-muted">{lang === 'vi' ? 'lần can thiệp đã thực hiện' : 'intervention(s) taken'}</p>
              </div>
            </div>

            {/* Sections taught */}
            {summary.sections.length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] font-semibold text-fg-muted uppercase tracking-wide mb-2">{lang === 'vi' ? 'Lớp phụ trách' : 'Sections taught'}</p>
                <div className="overflow-x-auto">
                  <table className="data-table w-full text-[12px]">
                    <thead>
                      <tr>
                        <th>{lang === 'vi' ? 'Mã lớp' : 'Section'}</th>
                        <th>{lang === 'vi' ? 'Mã môn' : 'Course'}</th>
                        <th>{lang === 'vi' ? 'Tên môn' : 'Name'}</th>
                        <th>{lang === 'vi' ? 'Kỳ' : 'Term'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.sections.map((sec) => (
                        <tr key={sec.sectionCode}>
                          <td className="mono font-semibold">{sec.sectionCode}</td>
                          <td className="mono">{sec.courseCode}</td>
                          <td>{sec.courseName}</td>
                          <td>{sec.term}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Disclaimer — spec mục 3.4 */}
            <p className="text-[11px] text-fg-muted mt-4 italic">
              {lang === 'vi'
                ? 'Đây là số liệu tổng hợp — không dùng để suy ra dữ liệu của 1 sinh viên cụ thể trong lớp.'
                : 'These are aggregate metrics only — not intended to infer data about any specific student.'}
            </p>
          </section>
        </>
      )}
    </div>
  );
}
