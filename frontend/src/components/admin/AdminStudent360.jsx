import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Loader2,
  ShieldAlert,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminStudentSummary, readAdminStudentResource } from '../../lib/api';

/** Student 360 — read-only audited view of one student's raw data.
 * Spec: docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.3.
 *
 * No "Phiên tự học" (self-study sessions) tab -- this branch has no
 * self_study_sessions table (see file docstring on the backend route). */
const TABS = [
  { key: 'plans', resources: ['plans', 'tasks', 'progress-events', 'reminders'] },
  { key: 'coursework', resources: ['assignments', 'submissions'] },
  { key: 'reflection', resources: ['reflections'] },
  { key: 'conversations', resources: ['conversations'] },
  { key: 'risk', resources: ['risk', 'interventions'] },
  { key: 'documents', resources: ['documents'] },
  { key: 'access-history', resources: ['access-history'] },
];

const TAB_LABEL = {
  vi: {
    plans: 'Kế hoạch & công việc',
    coursework: 'Bài tập & bài nộp',
    reflection: 'Phản tư',
    conversations: 'Hội thoại',
    risk: 'Rủi ro & can thiệp',
    documents: 'Tài liệu',
    'access-history': 'Lịch sử truy cập',
  },
  en: {
    plans: 'Plans & tasks',
    coursework: 'Coursework',
    reflection: 'Reflection',
    conversations: 'Conversations',
    risk: 'Risk & interventions',
    documents: 'Documents',
    'access-history': 'Access history',
  },
};

function fieldRows(item) {
  return Object.entries(item).filter(([k]) => k !== 'id');
}

function RawList({ items, lang }) {
  if (items.length === 0) {
    return <p className="text-[12px] text-fg-muted py-4">{lang === 'vi' ? 'Không có dữ liệu.' : 'No records.'}</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.id} className="rounded-lg border border-line bg-surface-card p-3 text-[12px]">
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {fieldRows(item).map(([key, value]) => (
              <span key={key} className="text-fg-secondary">
                <span className="font-semibold text-fg-muted">{key}:</span>{' '}
                {value === null || value === undefined || value === ''
                  ? '—'
                  : typeof value === 'object'
                    ? JSON.stringify(value)
                    : String(value)}
              </span>
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}

function ConversationsList({ items, studentId, lang }) {
  const [openId, setOpenId] = useState(null);
  const [transcript, setTranscript] = useState({});
  const [loadingId, setLoadingId] = useState(null);

  async function toggle(conv) {
    if (openId === conv.id) {
      setOpenId(null);
      return;
    }
    setOpenId(conv.id);
    if (!transcript[conv.id]) {
      setLoadingId(conv.id);
      try {
        const messages = await readAdminStudentResource(studentId, `conversations/${conv.id}`, { pageSize: 25 });
        setTranscript((prev) => ({ ...prev, [conv.id]: messages }));
      } finally {
        setLoadingId(null);
      }
    }
  }

  if (items.length === 0) {
    return <p className="text-[12px] text-fg-muted py-4">{lang === 'vi' ? 'Không có hội thoại nào.' : 'No conversations.'}</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((conv) => (
        <li key={conv.id} className="rounded-lg border border-line bg-surface-card">
          <button
            type="button"
            className="w-full flex items-center justify-between gap-2 p-3 text-left cursor-pointer"
            aria-expanded={openId === conv.id}
            onClick={() => toggle(conv)}
          >
            <span className="text-[13px] font-semibold text-fg">{conv.title}</span>
            <span className="flex items-center gap-2 text-[11px] text-fg-muted">
              {conv.subjectCode} · {new Date(conv.createdAt).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}
              {openId === conv.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          </button>
          {openId === conv.id && (
            <div className="border-t border-line p-3 space-y-2">
              {loadingId === conv.id ? (
                <Loader2 size={14} className="animate-spin text-fg-muted" />
              ) : (
                (transcript[conv.id] || []).map((msg) => (
                  <div key={msg.id} className="text-[12px]">
                    <span className="font-semibold text-fg-muted mono">{msg.sender}</span>{' '}
                    <span className="text-fg-secondary whitespace-pre-wrap">{msg.content}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function AdminStudent360() {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const { lang } = useLanguage();

  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState(null);
  const [tab, setTab] = useState('plans');
  const [tabData, setTabData] = useState({});
  const [tabLoading, setTabLoading] = useState(false);
  const [tabError, setTabError] = useState(null);

  useEffect(() => {
    setSummary(null);
    setSummaryError(null);
    getAdminStudentSummary(studentId)
      .then(setSummary)
      .catch((err) => setSummaryError(err));
  }, [studentId]);

  useEffect(() => {
    const activeTab = TABS.find((t) => t.key === tab);
    if (!activeTab) return;
    let cancelled = false;
    setTabLoading(true);
    setTabError(null);
    setTabData({});
    Promise.all(
      activeTab.resources.map((resource) =>
        readAdminStudentResource(studentId, resource, { pageSize: 25 }).then((items) => [resource, items]),
      ),
    )
      .then((pairs) => {
        if (cancelled) return;
        setTabData(Object.fromEntries(pairs));
      })
      .catch((err) => {
        if (!cancelled) setTabError(err);
      })
      .finally(() => {
        if (!cancelled) setTabLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [studentId, tab]);

  if (summaryError) {
    const notFound = summaryError.status === 404;
    return (
      <div className="p-4 md:p-6">
        <button type="button" className="btn-ghost text-[13px] mb-4 inline-flex items-center gap-1.5 cursor-pointer" onClick={() => navigate('/admin')}>
          <ArrowLeft size={14} /> {lang === 'vi' ? 'Quay lại' : 'Back'}
        </button>
        <p className="text-[14px] text-danger">
          {notFound
            ? (lang === 'vi' ? 'Không tìm thấy sinh viên.' : 'Student not found.')
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
          <section className="card p-5">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <h1 className="font-display text-xl font-bold text-fg">{summary.student.fullName}</h1>
                <p className="text-[12px] text-fg-muted mt-0.5">{summary.student.email} · <span className="mono">{summary.student.role}</span></p>
              </div>
              <span className={`badge text-[10px] ${summary.student.isActive ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'}`}>
                {summary.student.isActive ? (lang === 'vi' ? 'Đang hoạt động' : 'Active') : (lang === 'vi' ? 'Đã khoá' : 'Locked')}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
              <div className="rounded-lg border border-line bg-surface-elevated p-3">
                <p className="text-[11px] font-semibold text-fg-muted uppercase tracking-wide">{lang === 'vi' ? 'Hoạt động' : 'Activity'}</p>
                <p className="text-[13px] text-fg mt-1">{summary.activity.completedTasks}/{summary.activity.totalTasks} {lang === 'vi' ? 'task hoàn thành' : 'tasks completed'}</p>
              </div>
              <div className="rounded-lg border border-line bg-surface-elevated p-3">
                <p className="text-[11px] font-semibold text-fg-muted uppercase tracking-wide">{lang === 'vi' ? 'Rủi ro' : 'Risk'}</p>
                <p className="text-[13px] text-fg mt-1 flex items-center gap-1.5">
                  {summary.riskSummary.openSignals > 0 && <ShieldAlert size={13} className="text-warning" />}
                  {summary.riskSummary.openSignals} {lang === 'vi' ? 'tín hiệu chưa xử lý' : 'open signal(s)'}
                </p>
              </div>
            </div>
            {summary.enrollments.length > 0 && (
              <div className="mt-3">
                <p className="text-[11px] font-semibold text-fg-muted uppercase tracking-wide mb-1">{lang === 'vi' ? 'Lớp đã ghi danh' : 'Enrollments'}</p>
                <p className="text-[12px] text-fg-secondary">{summary.enrollments.map((e) => e.sectionCode).join(' · ')}</p>
              </div>
            )}
            <p className="text-[11px] text-fg-muted mt-3 italic">
              {lang === 'vi'
                ? 'Đây chỉ là số liệu tổng hợp — chọn tab bên dưới để xem dữ liệu gốc.'
                : 'This is aggregate only — pick a tab below to see raw records.'}
            </p>
          </section>

          <div className="tabs-underline" role="tablist" aria-label="Student 360 tabs">
            {TABS.map(({ key }) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={tab === key}
                className="tab-underline-item"
                onClick={() => setTab(key)}
              >
                {TAB_LABEL[lang][key]}
              </button>
            ))}
          </div>

          <section className="card p-5" role="tabpanel">
            {tabLoading ? (
              <Loader2 size={16} className="animate-spin text-fg-muted" />
            ) : tabError ? (
              <p className="text-[12px] text-danger">{lang === 'vi' ? 'Không tải được dữ liệu.' : 'Could not load data.'}</p>
            ) : tab === 'conversations' ? (
              <ConversationsList items={tabData.conversations || []} studentId={studentId} lang={lang} />
            ) : (
              Object.entries(tabData).map(([resource, items]) => (
                <div key={resource} className="mb-4 last:mb-0">
                  <p className="text-[11px] font-bold uppercase tracking-widest text-fg-muted mb-2">{resource}</p>
                  <RawList items={items} lang={lang} />
                </div>
              ))
            )}
          </section>
        </>
      )}
    </div>
  );
}
