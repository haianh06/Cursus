import { useEffect, useState } from 'react';
import { CourseDetail } from '../components/CourseDetail';
import { ApiError, getCourse } from '../lib/api';
import type { CourseDetail as CourseDetailData, Identity } from '../types';
import { useLanguage } from '../context/LanguageContext';

// Extracted out of App.tsx alongside AssignmentsScreen -- see that file's
// comment for why.
export function AssignmentDetailScreen({ code, identity }: { code: string; identity: Identity }) {
  const { t } = useLanguage();
  const [course, setCourse] = useState<CourseDetailData | null>(null);
  const [error, setError] = useState<'not_found' | 'generic' | null>(null);

  useEffect(() => {
    setCourse(null);
    setError(null);
    getCourse(code)
      .then(setCourse)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? 'not_found' : 'generic'));
  }, [code]);

  if (error) return <p className="max-w-5xl mx-auto px-5 py-10 text-sm text-red-600">{error === 'not_found' ? t('app.courseNotFound') : t('app.courseDataLoadError')}</p>;
  if (!course) return <div className="max-w-5xl mx-auto px-5 py-16 text-center text-sm text-slate-400">{t('app.loading')}</div>;

  return (
    <CourseDetail
      course={course}
      identity={identity}
      onCourseUpdate={setCourse}
    />
  );
}
