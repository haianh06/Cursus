import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import AdminAcademicPanel from './AdminAcademicPanel';
import AdminAiPolicy from './AdminAiPolicy';
import AdminAiUsage from './AdminAiUsage';
import AdminAnalytics from './AdminAnalytics';
import AdminAudit from './AdminAudit';
import AdminCurriculum from './AdminCurriculum';
import AdminDataRequests from './AdminDataRequests';
import AdminInstructor360 from './AdminInstructor360';
import AdminMockLms from './AdminMockLms';
import AdminOverview from './AdminOverview';
import AdminPeopleExplorer from './AdminPeopleExplorer';
import AdminSections from './AdminSections';
import AdminSettingsPanel from './AdminSettingsPanel';
import AdminStudent360 from './AdminStudent360';
import AdminUsers from './AdminUsers';
import { ADMIN_PATHS, LEGACY_ADMIN_REDIRECTS } from './adminRoutes';

function AdminPage({ title, subtitle, children }) {
  return (
    <section className="flex flex-col gap-5 animate-fade-up" aria-labelledby="admin-page-title">
      <header className="admin-page-header border-b border-line pb-4 text-left">
        <h1 id="admin-page-title" className="font-display text-xl font-bold text-fg">{title}</h1>
        <p className="mt-1 text-xs text-fg-muted">{subtitle}</p>
      </header>
      {children}
    </section>
  );
}

function LegacyRedirect({ to }) {
  return <Navigate to={to} replace />;
}

export default function AdminConsole() {
  const { t, lang } = useLanguage();

  return (
    <div className="admin-operations admin-cockpit-main">
      <Routes>
        <Route index element={<Navigate to={ADMIN_PATHS.overview} replace />} />
        <Route path="overview" element={
          <AdminPage title={lang === 'vi' ? 'Tổng quan' : 'Overview'} subtitle={t('admin.subtitleOverview')}>
            <AdminOverview />
          </AdminPage>
        } />
        <Route path="people" element={
          <AdminPage title={t('admin.navPeople')} subtitle={t('admin.subtitlePeople')}>
            <AdminPeopleExplorer />
          </AdminPage>
        } />
        <Route path="data-requests" element={
          <AdminPage title={lang === 'vi' ? 'Yêu cầu dữ liệu' : 'Data Requests'} subtitle={t('admin.subtitleDataRequests')}>
            <AdminDataRequests />
          </AdminPage>
        } />
        <Route path="analytics" element={
          <AdminPage title={t('admin.analyticsTabLabel')} subtitle={t('admin.subtitleAnalytics')}>
            <AdminAnalytics />
          </AdminPage>
        } />
        <Route path="ai-usage" element={
          <AdminPage title={t('admin.navAiUsage')} subtitle={t('admin.subtitleAiUsage')}>
            <AdminAiUsage />
          </AdminPage>
        } />
        <Route path="governance/curriculum" element={
          <AdminPage title={lang === 'vi' ? 'Chương trình học' : 'Curriculum'} subtitle={t('admin.subtitleCourses')}>
            <AdminCurriculum />
          </AdminPage>
        } />
        <Route path="governance/sections" element={
          <AdminPage title={t('admin.sectionsTitle')} subtitle={t('admin.subtitleSections')}>
            <AdminSections />
          </AdminPage>
        } />
        <Route path="governance/academic" element={
          <AdminPage title={lang === 'vi' ? 'Học kỳ & lịch thi' : 'Term & exams'} subtitle={t('admin.subtitleAcademic')}>
            <AdminAcademicPanel />
          </AdminPage>
        } />
        <Route path="governance/ai-policy" element={
          <AdminPage title={lang === 'vi' ? 'Chính sách AI' : 'AI Policy'} subtitle={t('admin.subtitlePolicy')}>
            <AdminAiPolicy />
          </AdminPage>
        } />
        <Route path="governance/edusync" element={
          <AdminPage title="EduSync" subtitle={t('admin.subtitleMockLms')}>
            <AdminMockLms />
          </AdminPage>
        } />
        <Route path="governance/access" element={
          <AdminPage title={t('admin.usersTabLabel')} subtitle={t('admin.subtitleUsers')}>
            <AdminUsers />
          </AdminPage>
        } />
        <Route path="governance/settings" element={
          <AdminPage title={t('admin.settingsTitle')} subtitle={t('admin.subtitleSettings')}>
            <AdminSettingsPanel />
          </AdminPage>
        } />
        <Route path="governance/logs" element={
          <AdminPage title={t('admin.auditTitle')} subtitle={t('admin.subtitleAudit')}>
            <AdminAudit />
          </AdminPage>
        } />
        <Route path="students/:studentId" element={<AdminStudent360 />} />
        <Route path="instructors/:instructorId" element={<AdminInstructor360 />} />
        {LEGACY_ADMIN_REDIRECTS.map(({ from, to }) => (
          <Route key={from} path={from} element={<LegacyRedirect to={to} />} />
        ))}
        <Route path="*" element={<Navigate to={ADMIN_PATHS.overview} replace />} />
      </Routes>
    </div>
  );
}
