import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, BookOpen, ListChecks, X } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminCourseCurriculum } from '../../lib/api';

// A curated subset of the raw syllabus `meta` keys, with Vietnamese labels —
// deliberately NOT a 1:1 dump of every key (some, like "Syllabus ID"/
// "IsActive", are internal bookkeeping, not useful to an Admin reading this
// screen). Every key here has been confirmed present in the real parsed
// data (docs/EVALUATION_2_KETLUAN.md research, 22/08) before being listed;
// a subject missing one just skips that row rather than showing blank.
const META_FIELDS = [
  ['NoCredit', 'Số tín chỉ'],
  ['Degree Level', 'Bậc đào tạo'],
  ['Time Allocation', 'Phân bổ thời gian'],
  ['Pre-Requisite', 'Môn tiên quyết'],
  ['Scoring Scale', 'Thang điểm'],
  ['MinAvgMarkToPass', 'Điểm TB tối thiểu để qua môn'],
  ['DecisionNo MM/dd/yyyy', 'Số quyết định'],
  ['ApprovedDate', 'Ngày phê duyệt'],
];

function MetaGrid({ meta }) {
  const rows = META_FIELDS.filter(([key]) => meta[key]);
  if (rows.length === 0) return null;
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-2.5">
      {rows.map(([key, label]) => (
        <div key={key} className="flex flex-col">
          <dt className="text-[10px] font-bold uppercase tracking-widest text-fg-muted">{label}</dt>
          <dd className="text-xs text-fg-secondary mt-0.5">{meta[key]}</dd>
        </div>
      ))}
    </dl>
  );
}

function ProseBlock({ title, text }) {
  if (!text) return null;
  return (
    <div>
      <h3 className="text-[10px] font-bold uppercase tracking-widest text-fg-muted mb-1.5">{title}</h3>
      <p className="text-xs text-fg-secondary leading-relaxed whitespace-pre-line">{text}</p>
    </div>
  );
}

export default function AdminCourseCurriculumModal({ code, courseName, onClose }) {
  const { lang } = useLanguage();
  const [state, setState] = useState({ loading: false, error: null, data: null });
  const panelRef = useRef(null);
  const firstRef = useRef(null);
  const restoreRef = useRef(null);

  useEffect(() => {
    if (!code) return;
    setState({ loading: true, error: null, data: null });
    let cancelled = false;
    getAdminCourseCurriculum(code)
      .then((data) => !cancelled && setState({ loading: false, error: null, data }))
      .catch((err) => !cancelled && setState({ loading: false, error: err, data: null }));
    return () => {
      cancelled = true;
    };
  }, [code]);

  useEffect(() => {
    if (!code) return undefined;
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
  }, [code, onClose]);

  if (!code) return null;

  const { loading, error, data } = state;
  const isNotFound = error && (error.status === 404 || error.code === 'HTTP_404');

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="curriculum-modal-title"
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-3xl max-h-[85vh] flex flex-col rounded-2xl border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-line shrink-0">
          <div className="text-left min-w-0">
            <h2 id="curriculum-modal-title" className="font-display text-sm font-bold text-fg truncate">
              <span className="mono text-accent-text-safe">{code}</span> — {courseName}
            </h2>
            <p className="text-[10px] text-fg-muted mt-0.5">
              {lang === 'vi' ? 'Đọc trực tiếp từ syllabus đã phân tích' : 'Read directly from the parsed syllabus'}
            </p>
          </div>
          <button
            ref={firstRef}
            type="button"
            className="btn-ghost w-9 h-9 shrink-0 inline-flex items-center justify-center rounded-lg cursor-pointer text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={onClose}
            aria-label={lang === 'vi' ? 'Đóng' : 'Close'}
          >
            <X size={15} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6 text-left">
          {loading && <p className="text-xs text-fg-muted">{lang === 'vi' ? 'Đang tải…' : 'Loading…'}</p>}

          {!loading && isNotFound && (
            <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-surface-elevated border border-line">
              <AlertCircle size={14} className="shrink-0 mt-0.5 text-fg-muted" />
              <p className="text-xs text-fg-secondary leading-relaxed">
                {lang === 'vi'
                  ? 'Môn này chưa có dữ liệu chương trình chi tiết (CLO/Session) — có thể được thêm thủ công qua form "Thêm môn học", không có file syllabus thật đi kèm.'
                  : 'No detailed curriculum data (CLO/Session) for this course — it may have been added manually via the "Add course" form, with no real syllabus file behind it.'}
              </p>
            </div>
          )}

          {!loading && error && !isNotFound && (
            <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-danger-soft border border-danger/20">
              <AlertCircle size={14} className="shrink-0 mt-0.5 text-danger" />
              <p className="text-xs text-danger leading-relaxed">{error.message}</p>
            </div>
          )}

          {!loading && data && (
            <>
              <MetaGrid meta={data.meta} />
              <ProseBlock title={lang === 'vi' ? 'Mô tả môn học' : 'Description'} text={data.meta.Description} />
              <ProseBlock title={lang === 'vi' ? 'Nhiệm vụ sinh viên' : 'Student tasks'} text={data.meta.StudentTasks} />
              <ProseBlock title={lang === 'vi' ? 'Công cụ hỗ trợ' : 'Tools'} text={data.meta.Tools} />
              <ProseBlock
                title={lang === 'vi' ? 'Chính sách chấm điểm (nguyên văn syllabus)' : 'Grading policy (verbatim from syllabus)'}
                text={data.meta.Note}
              />

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <ListChecks size={14} className="text-accent" />
                  <h3 className="text-xs font-bold text-fg">
                    {lang === 'vi' ? 'Chuẩn đầu ra môn học (CLO)' : 'Course Learning Outcomes (CLO)'}
                  </h3>
                  <span className="mono text-[10px] text-fg-muted">{data.clo_count}</span>
                </div>
                {data.clos.length === 0 ? (
                  <p className="text-xs text-fg-muted">{lang === 'vi' ? 'Không có dữ liệu CLO.' : 'No CLO data.'}</p>
                ) : (
                  <div className="card overflow-hidden">
                    <table className="data-table">
                      <tbody>
                        {data.clos.map((clo) => (
                          <tr key={clo.code}>
                            <td className="mono font-bold text-accent-text-safe w-16 align-top shrink-0">
                              {clo.code}
                            </td>
                            <td className="text-fg-secondary">{clo.text}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen size={14} className="text-accent" />
                  <h3 className="text-xs font-bold text-fg">
                    {lang === 'vi' ? 'Lịch trình buổi học (Session)' : 'Session schedule'}
                  </h3>
                  <span className="mono text-[10px] text-fg-muted">{data.session_count}</span>
                </div>
                {data.sessions.length === 0 ? (
                  <p className="text-xs text-fg-muted">{lang === 'vi' ? 'Không có dữ liệu buổi học.' : 'No session data.'}</p>
                ) : (
                  <div className="card overflow-hidden">
                    <div className="overflow-x-auto max-h-[320px] overflow-y-auto">
                      <table className="data-table">
                        <thead className="sticky top-0 bg-surface-card">
                          <tr>
                            <th scope="col" className="w-14">#</th>
                            <th scope="col">{lang === 'vi' ? 'Nội dung' : 'Topic'}</th>
                            <th scope="col">{lang === 'vi' ? 'Tài liệu' : 'Materials'}</th>
                            <th scope="col">{lang === 'vi' ? 'Nhiệm vụ sinh viên' : 'Student task'}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.sessions.map((session) => (
                            <tr key={session.number ?? session.topic}>
                              <td className="mono font-bold text-fg align-top">{session.number ?? '—'}</td>
                              <td className="text-fg-secondary align-top whitespace-pre-line">{session.topic || '—'}</td>
                              <td className="text-fg-muted align-top whitespace-pre-line">{session.materials || '—'}</td>
                              <td className="text-fg-muted align-top whitespace-pre-line">{session.task || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
