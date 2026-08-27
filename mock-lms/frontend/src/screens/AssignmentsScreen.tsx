import { useEffect, useState } from 'react';
import { CourseList } from '../components/CourseList';
import { listCourses } from '../lib/api';
import type { CourseSummary } from '../types';
import { useLanguage } from '../context/LanguageContext';

// Extracted out of App.tsx so every route has a consistent screens/*.tsx
// entry point (App.tsx previously defined this and AssignmentDetailScreen
// inline, the only two routes that didn't -- see App.tsx's RouteView).
export function AssignmentsScreen({ onNavigate }: { onNavigate: (path: string) => void }) {
  const { t } = useLanguage();
  const [courses, setCourses] = useState<CourseSummary[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    listCourses().then(setCourses).catch(() => setError(true));
  }, []);

  if (error) return <p className="max-w-5xl mx-auto px-5 py-10 text-sm text-red-600">{t('app.coursesLoadError')}</p>;
  if (!courses) return <div className="max-w-5xl mx-auto px-5 py-16 text-center text-sm text-slate-400">{t('app.loading')}</div>;

  return (
    <CourseList
      courses={courses}
      onSelectCourse={(code) => onNavigate(`/courses/assignments/${encodeURIComponent(code)}`)}
    />
  );
}
