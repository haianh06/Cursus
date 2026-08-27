import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { CourseSummary } from '../types';
import { useLanguage } from '../context/LanguageContext';



/** Grouped by semester, not one flat grid — a real course catalog (Canvas's
 * "All Courses" filter) always organises by term first. Ported from the
 * original app/templates/courses.html, which had the same grouping. */
function groupBySemester(courses: CourseSummary[]): [string, CourseSummary[]][] {
  const bySemester = new Map<string, CourseSummary[]>();
  for (const course of courses) {
    const bucket = bySemester.get(course.semester) ?? [];
    bucket.push(course);
    bySemester.set(course.semester, bucket);
  }
  return Array.from(bySemester.entries()).sort(([a], [b]) => {
    const na = Number(a);
    const nb = Number(b);
    if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
    return a.localeCompare(b);
  });
}

export function CourseList({
  courses,
  onSelectCourse,
}: {
  courses: CourseSummary[];
  onSelectCourse: (code: string) => void;
}) {
  const { t } = useLanguage();
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return courses;
    return courses.filter((c) => `${c.code} ${c.name}`.toLowerCase().includes(q));
  }, [courses, query]);

  const semesters = useMemo(() => groupBySemester(filtered), [filtered]);
  const totalCredits = courses.reduce((sum, c) => sum + c.credit, 0);
  const semesterCount = useMemo(() => new Set(courses.map((c) => c.semester)).size, [courses]);

  return (
    <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
      {/* Global Breadcrumbs (App.tsx) already provides the way back to
          EduSync -- no per-screen duplicate. */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">{t('courseList.heading')}</h1>
        <p className="text-sm text-slate-500 mt-1">
          {t('courseList.subheading')}
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <StatCard label={t('courseList.statCourses')} value={courses.length} />
        <StatCard label={t('courseList.statCredits')} value={totalCredits} />
        <StatCard label={t('courseList.statSemesters')} value={semesterCount} />
      </div>

      <div className="relative max-w-xs">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('courseList.filterPlaceholder')}
          aria-label={t('courseList.filterAriaLabel')}
          className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {semesters.length === 0 && (
        <p className="text-sm text-slate-500 py-8 text-center">{t('courseList.noMatch')}</p>
      )}

      {semesters.map(([semester, coursesInTerm]) => (
        <section key={semester}>
          <h2 className="flex items-baseline gap-2 text-xs font-bold uppercase tracking-wide text-slate-500 border-b border-slate-200 pb-2 mb-3">
            {/^\d+$/.test(semester) ? `${t('courseList.semesterPrefix')} ${semester}` : semester}
            <span className="font-medium normal-case tracking-normal text-slate-400">
              ({coursesInTerm.length} {t('courseList.coursesUnit')})
            </span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {coursesInTerm.map((course) => {
              return (
                <button
                  key={course.code}
                  onClick={() => onSelectCourse(course.code)}
                  className="card block text-left w-full overflow-hidden hover:-translate-y-0.5 transition-transform cursor-pointer group"
                >
                  <div className="h-1 bg-slate-200 group-hover:bg-[var(--accent)] transition-colors" />
                  <div className="p-4 space-y-2">
                    <div className="mono text-xs font-bold tracking-wide text-slate-500 group-hover:text-[var(--accent)] transition-colors">
                      {course.code}
                    </div>
                    <div className="text-sm font-bold text-slate-900 line-clamp-2 min-h-[2.5em] group-hover:text-[var(--accent)] transition-colors">
                      {course.name}
                    </div>
                    <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500 pt-1 border-t border-slate-100">
                      <span>{course.credit} {t('courseList.creditsUnit')}</span>
                      <span className="badge badge-accent">{course.assignmentCount} {t('courseList.assignmentsUnit')}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="card px-4 py-2.5 min-w-[110px]">
      <div className="text-lg font-bold text-slate-900">{value}</div>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}
