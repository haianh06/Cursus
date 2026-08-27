import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Loader2,
  ShieldAlert,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminStudentSummary, readAdminStudentResource, userFacingApiError } from '../../lib/api';
import AdminAsyncRegion from './AdminAsyncRegion';
import { ADMIN_STUDENT_RAW_TABS, describeAdminRawItem } from './adminSensitiveResources';
import { createRequestGeneration } from './requestGeneration';

/** Student 360 — read-only audited view of one student's raw data.
 * Spec: docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.3.
 *
 * Includes the audited self-study sessions tab backed by the existing
 * self_study_sessions table. */
const TAB_LABEL = {
  vi: {
    plans: 'Kế hoạch & công việc',
    sessions: 'Phiên tự học',
    coursework: 'Bài tập & bài nộp',
    reflection: 'Phản tư',
    conversations: 'Hội thoại',
    risk: 'Rủi ro & can thiệp',
    documents: 'Tài liệu',
    'access-history': 'Lịch sử truy cập',
  },
  en: {
    plans: 'Plans & tasks',
    sessions: 'Self-study sessions',
    coursework: 'Coursework',
    reflection: 'Reflection',
    conversations: 'Conversations',
    risk: 'Risk & interventions',
    documents: 'Documents',
    'access-history': 'Access history',
  },
};

const RESOURCE_LABEL = {
  vi: {
    plans: 'Kế hoạch tuần', tasks: 'Công việc', 'progress-events': 'Sự kiện tiến độ', reminders: 'Nhắc nhở',
    sessions: 'Các phiên tự học', assignments: 'Bài tập', submissions: 'Bài nộp', reflections: 'Phản tư',
    risk: 'Tín hiệu rủi ro', interventions: 'Can thiệp', documents: 'Tài liệu', 'access-history': 'Lượt truy cập',
  },
  en: {
    plans: 'Weekly plans', tasks: 'Tasks', 'progress-events': 'Progress events', reminders: 'Reminders',
    sessions: 'Self-study sessions', assignments: 'Assignments', submissions: 'Submissions', reflections: 'Reflections',
    risk: 'Risk signals', interventions: 'Interventions', documents: 'Documents', 'access-history': 'Access events',
  },
};

function RawList({ resource, items, lang }) {
  if (items.length === 0) {
    return <p className="text-[12px] text-fg-muted py-4">{lang === 'vi' ? 'Không có dữ liệu.' : 'No records.'}</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((item) => describeAdminRawItem(resource, item, lang)).filter(Boolean).map((entry) => (
        <li key={entry.id} className="rounded-lg border border-line bg-surface-card p-3 text-[12px]">
          <p className="font-semibold text-fg">{entry.title}</p>
          <dl className="mt-2 grid gap-2 sm:grid-cols-2">
            {entry.rows.map((row) => (
              <div key={row.field} className={row.field === 'content' || row.field === 'recommendedAction' ? 'sm:col-span-2' : ''}>
                <dt className="text-[10px] font-semibold uppercase tracking-wide text-fg-muted">{row.label}</dt>
                <dd className="mt-0.5 whitespace-pre-wrap text-fg-secondary">{row.value}</dd>
              </div>
            ))}
          </dl>
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
  const summaryRequests = useRef(createRequestGeneration());
  const tabRequests = useRef(createRequestGeneration());

  const loadSummary = useCallback(async () => {
    const generation = summaryRequests.current.begin();
    setSummary(null);
    setSummaryError(null);
    try {
      const result = await getAdminStudentSummary(studentId);
      if (summaryRequests.current.isCurrent(generation)) setSummary(result);
    } catch (err) {
      if (summaryRequests.current.isCurrent(generation)) {
        setSummaryError({ ...userFacingApiError(err, lang), status: err?.status, code: err?.code });
      }
    }
  }, [lang, studentId]);

  const loadTab = useCallback(async () => {
    const activeTab = ADMIN_STUDENT_RAW_TABS.find((candidate) => candidate.key === tab);
    if (!activeTab) return;
    const generation = tabRequests.current.begin();
    setTabLoading(true);
    setTabError(null);
    setTabData({});
    try {
      const pairs = await Promise.all(activeTab.resources.map((resource) =>
        readAdminStudentResource(studentId, resource, { pageSize: 25 }).then((items) => [resource, items]),
      ));
      if (tabRequests.current.isCurrent(generation)) setTabData(Object.fromEntries(pairs));
    } catch (err) {
      if (tabRequests.current.isCurrent(generation)) {
        setTabError({ ...userFacingApiError(err, lang), status: err?.status, code: err?.code });
      }
    } finally {
      if (tabRequests.current.isCurrent(generation)) setTabLoading(false);
    }
  }, [lang, studentId, tab]);

  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadTab(); }, [loadTab]);

  if (summaryError) {
    const notFound = summaryError.status === 404;
    return (
      <div className="p-4 md:p-6">
        <button type="button" className="btn-ghost text-[13px] mb-4 inline-flex items-center gap-1.5 cursor-pointer" onClick={() => navigate('/admin/people')}>
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
      <button type="button" className="btn-ghost text-[13px] w-fit inline-flex items-center gap-1.5 cursor-pointer" onClick={() => navigate('/admin/people')}>
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
            {ADMIN_STUDENT_RAW_TABS.map(({ key }) => (
              <button
                key={key}
                id={`admin-student-tab-${key}`}
                type="button"
                role="tab"
                aria-selected={tab === key}
                aria-controls={`admin-student-panel-${key}`}
                className="tab-underline-item"
                onClick={() => setTab(key)}
              >
                {TAB_LABEL[lang][key]}
              </button>
            ))}
          </div>

          <section
            id={`admin-student-panel-${tab}`}
            className="card p-5"
            role="tabpanel"
            aria-labelledby={`admin-student-tab-${tab}`}
          >
            <AdminAsyncRegion
              loading={tabLoading}
              error={tabError}
              onRetry={loadTab}
              label={TAB_LABEL[lang][tab]}
            >
              {tab === 'conversations' ? (
                <ConversationsList items={tabData.conversations || []} studentId={studentId} lang={lang} />
              ) : (
                Object.entries(tabData).map(([resource, items]) => (
                  <div key={resource} className="mb-4 last:mb-0">
                    <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-fg-muted">
                      {RESOURCE_LABEL[lang][resource] || resource}
                    </p>
                    <RawList resource={resource} items={items} lang={lang} />
                  </div>
                ))
              )}
            </AdminAsyncRegion>
          </section>
        </>
      )}
    </div>
  );
}
