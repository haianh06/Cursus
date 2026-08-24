import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, AlertTriangle, BarChart3, Lock, RefreshCw, Info, Award, Download,
  Bell, Megaphone, UserCircle2, ChevronRight,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  exportInstructorReport, getInstructorAlerts, getInstructorAnnouncements,
  getInstructorDashboard, getInstructorKudos,
} from '../../lib/api';
import { riskLevelLabel, isHighRisk, formatDetectedAt } from '../../lib/riskLabels';
import ClassComparisonPanel from './ClassComparisonPanel';

/** Dashboard GV — chi con so lieu thong ke + thong bao can thiet (vi pham/
 *  rui ro cua SV, thong bao moi tu Admin). Cac khoi thao tac chi tiet (Hoat
 *  dong tren lop, Duyet bo on tap, Danh sach nop bai, Sinh vien co nguy co)
 *  da tach sang trang rieng trong sidebar de dashboard khong bi dai. */
export default function InstructorHome() {
  const { t, lang } = useLanguage();

  const [kudos, setKudos] = useState([]);
  const [weeklyRates, setWeeklyRates] = useState([]);
  const [classSize, setClassSize] = useState(0);
  const [primaryCourse, setPrimaryCourse] = useState(null);
  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('ALL');
  const [highRiskCount, setHighRiskCount] = useState(null);
  const [openAlertCount, setOpenAlertCount] = useState(null);
  const [overdueCount, setOverdueCount] = useState(null);
  const [isWeeklyFallback, setIsWeeklyFallback] = useState(false);
  const [isClassSizeFallback, setIsClassSizeFallback] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  // Thong bao gon: top vai case can chu y nhat (khong co nut hanh dong o day —
  // xem/xu ly day du tren trang "Sinh vien co nguy co").
  const [urgentAlerts, setUrgentAlerts] = useState([]);
  const [announcements, setAnnouncements] = useState([]);

  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      const { blob, filename } = await exportInstructorReport(selectedCourseId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err.message);
    } finally {
      setIsExporting(false);
    }
  };

  const loadDashboard = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [dashboard, alertData, kudosData, announcementData] = await Promise.all([
        getInstructorDashboard(selectedCourseId),
        getInstructorAlerts(selectedCourseId),
        getInstructorKudos(selectedCourseId).catch(() => []),
        getInstructorAnnouncements().catch(() => []),
      ]);
      setClassSize(dashboard.classSize);
      setIsClassSizeFallback(Boolean(dashboard.isClassSizeFallback));
      setPrimaryCourse(dashboard.courses?.[0] ?? null);
      setCourses(dashboard.courses);
      setKudos(kudosData);
      setHighRiskCount(dashboard.highRiskCount);
      setOpenAlertCount(dashboard.totalActiveWarnings);
      setOverdueCount(dashboard.overdueCount);
      setWeeklyRates(
        (dashboard.classAvgCompletionByWeek || []).map((rate, index) => ({
          week: `W${index + 1}`,
          rate: Math.round(rate * 100)
        }))
      );
      setIsWeeklyFallback(Boolean(dashboard.isWeeklyFallback));

      // Thong bao "van de cua SV": chua xu ly, uu tien qua han > rui ro cao >
      // moi nhat, chi lay vai dong dau de dashboard khong dai — xem het thi
      // qua trang Risk rieng.
      const unresolved = (Array.isArray(alertData) ? alertData : []).filter((item) => item.status !== 'INTERVENTION_APPROVED');
      const sorted = [...unresolved].sort((a, b) => {
        if (Boolean(b.isOverdue) !== Boolean(a.isOverdue)) return Boolean(b.isOverdue) - Boolean(a.isOverdue);
        const rank = { HIGH: 2, MEDIUM: 1, LOW: 0 };
        return (rank[b.riskLevel] || 0) - (rank[a.riskLevel] || 0);
      });
      setUrgentAlerts(sorted.slice(0, 3));
      setAnnouncements(announcementData);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCourseId]);

  const viewState = isLoading ? 'loading' : loadError ? 'error' : 'success';

  if (viewState === 'loading') {
    return (
      <div className="space-y-6 animate-pulse p-6">
        <div className="h-28 bg-surface-elevated rounded-xl border border-line"></div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80 bg-surface-card rounded-xl border border-line"></div>
          <div className="h-80 bg-surface-card rounded-xl border border-line"></div>
        </div>
      </div>
    );
  }

  if (viewState === 'error') {
    return (
      <div className="p-12 text-center space-y-4 max-w-lg mx-auto bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-2xl my-8 shadow-xl">
        <AlertTriangle className="w-12 h-12 text-red-600 dark:text-red-400 mx-auto" />
        <h3 className="text-lg font-black text-red-900 dark:text-red-200 font-serif-heading">{t('states.errorTitle')}</h3>
        <p className="text-xs text-red-800 dark:text-red-300/90 font-medium">{t('states.errorDesc')}</p>
        {loadError && (
          <p className="text-[11px] text-red-700 dark:text-red-400/90 font-mono-code break-words">{loadError}</p>
        )}
        <button
          onClick={() => loadDashboard()}
          className="px-4 py-2 bg-danger-ink hover:bg-[#7F2F2A] text-white text-xs font-bold rounded-xl inline-flex items-center gap-2 cursor-pointer shadow-md"
        >
          <RefreshCw className="w-4 h-4" /> {t('states.retryBtn')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">

      {/* HEADER CLASS SUMMARY — mã lớp và tên môn lấy từ /instructor/dashboard
          (mảng courses), không còn hardcode "SE1801"/"SSA101" như trước. */}
      <div className="cursus-hero-banner rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 text-white">
        <div className="space-y-1 min-w-0">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 border border-white/20 rounded-full text-xs font-extrabold text-accent backdrop-blur-md font-mono-code">
            <Users className="w-3.5 h-3.5 text-accent" />
            <span>
              {primaryCourse?.code ? (
                <>
                  {`${t('instructor.classLabel')} ${primaryCourse.code} — ${classSize} ${t('instructor.studentsUnit')}`}
                  {isClassSizeFallback && ` (${t('instructor.seedTag')})`}
                </>
              ) : (
                t('instructor.noCourseAssigned')
              )}
            </span>
          </div>
          <h1 className="text-2xl font-black text-white font-serif-heading">{t('instructor.pageTitle')}</h1>
          {primaryCourse?.name && (
            <p className="text-xs text-teal-200 font-bold truncate max-w-md">{primaryCourse.name}</p>
          )}
          <p className="text-xs text-slate-200 font-medium">
            {t('instructor.pageSubtitle')}
          </p>
        </div>

        {courses.length > 1 && (
          <label className="flex items-center gap-2 text-xs font-bold text-white shrink-0">
            <span className="sr-only">{t('instructor.filterLabel')}</span>
            <select
              value={selectedCourseId}
              onChange={(event) => setSelectedCourseId(event.target.value)}
              className="bg-white/10 border border-white/20 rounded-xl px-3 py-1.5 text-xs font-bold text-white backdrop-blur-md cursor-pointer [&>option]:text-[#15181C]"
            >
              <option value="ALL">{t('instructor.allCourses')}</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>{course.code}</option>
              ))}
            </select>
          </label>
        )}

        <div className="p-3 bg-white/10 border border-white/20 rounded-2xl flex items-center gap-2 text-xs text-slate-200 max-w-xs backdrop-blur-md font-medium">
          <Lock className="w-4 h-4 text-[#A7D4B0] shrink-0" />
          <span>{t('instructor.privacyBadge')}</span>
        </div>
      </div>

      {/* SỐ LIỆU THẬT — hai con số duy nhất trong F4 được backend đếm từ bảng
          risk_signals. Các tỷ lệ còn lại (classCompletionRate,
          onTimeSubmissions) hiện vẫn là chuỗi hardcode trong backend nên chưa
          đưa lên đây: bày chúng ra sẽ thành số giả đội lốt số đo thật. */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { key: 'high', label: t('instructor.metricHighRisk'), value: highRiskCount, danger: true },
          { key: 'open', label: t('instructor.metricOpenAlerts'), value: openAlertCount, danger: false },
          { key: 'overdue', label: t('instructor.metricOverdue'), value: overdueCount, danger: true },
        ].map(metric => (
          <div key={metric.key} className="card p-5 space-y-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className={`w-4 h-4 ${metric.danger ? 'text-danger-ink dark:text-red-400' : 'text-accent'}`} />
              <span className="text-xs font-black text-fg">{metric.label}</span>
            </div>
            <div className={`text-3xl font-black font-mono-code ${metric.danger ? 'text-danger-ink dark:text-red-400' : 'text-accent'}`}>
              {metric.value == null ? '—' : metric.value}
            </div>
          </div>
        ))}
      </div>

      {/* Xuất báo cáo lớp — dùng đúng số liệu đã hiện phía trên. */}
      <div className="space-y-1.5">
        <button
          type="button"
          onClick={handleExport}
          disabled={isExporting}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border border-line-strong text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
        >
          <Download className="w-3.5 h-3.5" />
          {isExporting ? t('instructor.exporting') : t('instructor.exportBtn')}
        </button>
        {exportError && (
          <p role="alert" className="text-[11px] font-bold text-red-700 dark:text-red-400">{exportError}</p>
        )}
      </div>

      {/* THÔNG BÁO CẦN THIẾT — case SV cần chú ý (rút gọn, xem đủ ở trang
          riêng) + thông báo mới từ Admin. Rỗng cả hai thì ẩn cả khối, không
          hiện "không có gì" làm rối dashboard. */}
      {(urgentAlerts.length > 0 || announcements.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {urgentAlerts.length > 0 && (
            <div className="card p-6 space-y-3 border-l-4 border-l-danger-ink">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-black text-fg font-serif-heading flex items-center gap-2">
                  <Bell className="w-4 h-4 text-danger-ink dark:text-red-400" />
                  {t('instructor.notificationsStudentTitle')}
                </h2>
                <Link
                  to="/instructor/risks"
                  className="text-[11px] font-black text-accent hover:text-accent-hover inline-flex items-center gap-0.5 cursor-pointer shrink-0"
                >
                  {t('instructor.notificationsViewAll')} <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="space-y-2">
                {urgentAlerts.map((item) => (
                  <Link
                    key={item.id}
                    to={`/instructor/students/${item.studentId}`}
                    className="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-surface-elevated border border-line hover:border-accent/50 transition-colors text-xs"
                  >
                    <span className="font-bold text-fg flex items-center gap-1.5 min-w-0">
                      <UserCircle2 className="w-3.5 h-3.5 shrink-0 opacity-60" />
                      <span className="truncate">{item.studentAlias}</span>
                    </span>
                    <span className="flex items-center gap-1.5 shrink-0">
                      {item.isOverdue && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-black uppercase bg-danger-soft text-danger-ink">
                          {t('instructor.overdueBadge', { days: item.daysOpen })}
                        </span>
                      )}
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase font-mono-code ${
                        isHighRisk(item.riskLevel) ? 'bg-danger-soft text-danger-ink' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                      }`}>
                        {riskLevelLabel(t, item.riskLevel)}
                      </span>
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {announcements.length > 0 && (
            <div className="card p-6 space-y-3 border-l-4 border-l-accent">
              <h2 className="text-sm font-black text-fg font-serif-heading flex items-center gap-2">
                <Megaphone className="w-4 h-4 text-accent" />
                {t('instructor.notificationsAdminTitle')}
              </h2>
              <div className="space-y-2 max-h-[16rem] overflow-y-auto pr-1">
                {announcements.map((item) => (
                  <div key={item.id} className="p-2.5 rounded-xl bg-surface-elevated border border-line">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-black text-xs text-fg truncate">{item.title}</span>
                      <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono-code shrink-0">
                        {formatDetectedAt(item.createdAt, lang)}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1">{item.content}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* F8 — GHI NHẬN TÍCH CỰC. Chỉ hiện khi có SV đạt ngưỡng, không hiện
          trạng thái "chưa có ai" — bảng cảnh báo bên dưới đã đủ để nói "chưa
          có gì bất thường", khối này chỉ nên xuất hiện khi có tin tốt thật. */}
      {kudos.length > 0 && (
        <div className="card p-5 space-y-3 border-l-4 border-l-success-ink">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-success-ink dark:text-emerald-400" />
            <h2 className="text-sm font-black text-fg font-serif-heading">
              {t('instructor.kudosTitle')}
            </h2>
          </div>
          <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
            {kudos.map((item) => (
              <Link
                key={item.studentId}
                to={`/instructor/students/${item.studentId}`}
                title={item.note}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-success-soft dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-700/60 text-xs font-bold text-emerald-900 dark:text-[#A7D4B0] hover:border-emerald-500 transition-colors cursor-pointer"
              >
                <Award className="w-3.5 h-3.5 shrink-0" />
                {item.displayName}
              </Link>
            ))}
          </div>
        </div>
      )}

      <ClassComparisonPanel />

      {/* WEEKLY COMPLETION CHART */}
      <div className="card p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <h2 className="text-base font-black text-fg flex items-center gap-2 font-serif-heading">
            <BarChart3 className="w-5 h-5 text-accent" />
            <span>{t('instructor.chartTitle')}</span>
          </h2>
          <span className="text-xs text-accent font-black font-mono-code">
            {weeklyRates.length
              ? t('instructor.chartCurrent', { rate: weeklyRates[weeklyRates.length - 1].rate })
              : '—'}
          </span>
        </div>

        {(isClassSizeFallback || isWeeklyFallback) && (
          <div className="p-2.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/60 rounded-xl space-y-1.5">
            {isClassSizeFallback && (
              <div className="flex items-start gap-2">
                <Info className="w-3.5 h-3.5 text-amber-700 dark:text-amber-400 shrink-0 mt-px" />
                <span className="text-[11px] font-bold text-amber-900 dark:text-amber-200">
                  {t('instructor.fallbackClassSizeNotice')}
                </span>
              </div>
            )}
            {isWeeklyFallback && (
              <div className="flex items-start gap-2">
                <Info className="w-3.5 h-3.5 text-amber-700 dark:text-amber-400 shrink-0 mt-px" />
                <span className="text-[11px] font-bold text-amber-900 dark:text-amber-200">
                  {t('instructor.fallbackChartNotice')}
                </span>
              </div>
            )}
          </div>
        )}

        {weeklyRates.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400 bg-surface-elevated border border-line rounded-xl font-medium">
            {t('instructor.chartEmpty')}
          </div>
        ) : (
          <div className="space-y-3 pt-2 max-h-[20rem] overflow-y-auto pr-1">
            {weeklyRates.map(item => (
              <div key={item.week} className="space-y-1">
                <div className="flex justify-between text-xs text-fg font-bold">
                  <span>{item.week}</span>
                  <span className="font-mono-code">{item.rate}%</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-3 overflow-hidden border border-slate-300 dark:border-slate-700">
                  <div
                    className={`${item.rate >= 75 ? 'bg-success-ink dark:bg-success-ink' : 'bg-amber-500'} h-full transition-all duration-500`}
                    style={{ width: `${item.rate}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
