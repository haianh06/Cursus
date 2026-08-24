import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { listAdminPeople, userFacingApiError } from '../../lib/api';
import AdminAsyncRegion from './AdminAsyncRegion';
import { createRequestGeneration } from './requestGeneration';
import { adminRoleLabel, adminSummaryFieldLabel } from './adminDisplay';

const ROLES = ['', 'STUDENT', 'INSTRUCTOR', 'ADMIN'];

export default function AdminPeopleExplorer() {
  const { t, lang } = useLanguage();
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requests = useRef(createRequestGeneration());

  const load = useCallback(async () => {
    const generation = requests.current.begin();
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await listAdminPeople({ search, role, page, page_size: 25 });
      if (requests.current.isCurrent(generation)) {
        setData(response.data ?? response);
      }
    } catch (err) {
      if (requests.current.isCurrent(generation)) {
        setError({ ...userFacingApiError(err, lang), status: err?.status, code: err?.code });
      }
    } finally {
      if (requests.current.isCurrent(generation)) setLoading(false);
    }
  }, [lang, page, role, search]);

  useEffect(() => {
    load();
  }, [load]);

  const items = data?.items || [];

  return (
    <div className="flex flex-col gap-4">
      <h2 className="font-display text-base font-bold text-fg">{t('admin.navPeople')}</h2>

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          load();
        }}
      >
        <label className="flex flex-col text-xs font-semibold text-fg">
          {t('admin.peopleSearch')}
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="mt-1 min-h-11 rounded-lg border border-line bg-surface px-3 text-xs font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
        </label>
        <label className="flex flex-col text-xs font-semibold text-fg">
          {t('admin.usersRole')}
          <select
            value={role}
            onChange={(event) => {
              setRole(event.target.value);
              setPage(1);
            }}
            className="mt-1 min-h-11 rounded-lg border border-line bg-surface px-3 text-xs font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {ROLES.map((item) => (
              <option key={item || 'all'} value={item}>
                {item ? adminRoleLabel(t, item) : t('admin.usersAllRoles')}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="flex min-h-11 items-center gap-2 rounded-lg border border-accent px-3 text-xs font-semibold text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <Search size={13} aria-hidden="true" />
          {t('admin.peopleSearchAction')}
        </button>
      </form>

      <AdminAsyncRegion
        loading={loading}
        error={error}
        empty={!loading && !error && items.length === 0}
        emptyMessage={t('admin.peopleEmpty')}
        onRetry={load}
      >
        <div className="admin-scroll-x rounded-lg border border-line">
          <table className="w-full min-w-[40rem] text-left text-xs">
            <caption className="sr-only">{t('admin.navPeople')}</caption>
            <thead className="border-b border-line text-fg-secondary">
              <tr>
                <th scope="col" className="px-4 py-3">{t('admin.usersName')}</th>
                <th scope="col" className="px-4 py-3">{t('admin.usersRole')}</th>
                <th scope="col" className="px-4 py-3">{t('admin.usersStatus')}</th>
                <th scope="col" className="px-4 py-3">{t('admin.peopleAcademic')}</th>
                <th scope="col" className="px-4 py-3">{t('admin.peopleOpen')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((person) => (
                <tr key={person.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-fg">{person.full_name}</p>
                    <p className="text-fg-secondary">{person.email}</p>
                  </td>
                  <td className="mono px-4 py-3">{adminRoleLabel(t, person.role)}</td>
                  <td
                    className={`px-4 py-3 font-semibold ${
                      person.is_active ? 'text-success' : 'text-danger'
                    }`}
                  >
                    {person.is_active ? t('admin.usersActive') : t('admin.usersLocked')}
                  </td>
                  <td className="mono px-4 py-3 text-fg-secondary">
                    {Object.entries(person.academic_summary || {})
                    .map(([key, value]) => `${adminSummaryFieldLabel(t, key)}: ${value}`)
                      .join(' · ') || '—'}
                  </td>
                  <td className="px-4 py-3">
                    {person.role === 'ADMIN' ? (
                      <span className="text-fg-secondary">—</span>
                    ) : (
                      <Link
                        to={
                          person.role === 'STUDENT'
                            ? `/students/${person.id}`
                            : `/instructors/${person.id}`
                        }
                        className="inline-flex min-h-11 items-center font-semibold text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      >
                        {t('admin.peopleOpen360')}
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AdminAsyncRegion>

      <div className="flex items-center gap-3 text-xs">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((value) => Math.max(1, value - 1))}
          className="min-h-11 rounded-lg border border-line px-3 font-semibold text-fg disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {t('admin.prevPage')}
        </button>
        <span className="text-fg-secondary">{page}</span>
        <button
          type="button"
          disabled={!data?.meta?.has_next}
          onClick={() => setPage((value) => value + 1)}
          className="min-h-11 rounded-lg border border-line px-3 font-semibold text-fg disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {t('admin.nextPage')}
        </button>
      </div>
    </div>
  );
}
