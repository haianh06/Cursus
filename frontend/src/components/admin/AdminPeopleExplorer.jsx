import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Mail, Search, ShieldCheck, UserRound } from 'lucide-react';
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
  const [selectedId, setSelectedId] = useState(null);
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
  const selectedPerson = items.find((person) => person.id === selectedId) || items[0] || null;

  return (
    <div className="flex flex-col gap-4">
      <h2 className="sr-only">{t('admin.navPeople')}</h2>

      <form
        className="admin-toolbar flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          load();
        }}
      >
        <label className="flex min-w-[15rem] flex-1 flex-col text-xs font-semibold text-fg">
          {t('admin.peopleSearch')}
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="input mt-1 min-h-11 text-xs font-normal"
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
            className="input mt-1 min-h-11 min-w-40 text-xs font-normal"
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
          className="btn btn-outline flex min-h-11 items-center gap-2 px-4 text-xs"
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
        <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="admin-scroll-x overflow-hidden rounded-lg border border-line bg-surface-card">
          <table className="data-table w-full min-w-[40rem] text-left text-xs">
            <caption className="sr-only">{t('admin.navPeople')}</caption>
            <thead className="border-b border-line text-fg-secondary">
              <tr>
                <th scope="col" className="px-4 py-3">{t('admin.usersName')}</th>
                <th scope="col" className="px-4 py-3">{t('admin.usersRole')}</th>
                <th scope="col" className="px-4 py-3">{t('admin.usersStatus')}</th>
                <th scope="col" className="px-4 py-3">{t('admin.peopleAcademic')}</th>
                <th scope="col" className="whitespace-nowrap px-4 py-3">{t('admin.peopleOpen')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((person) => (
                <tr
                  key={person.id}
                  className={`${selectedPerson?.id === person.id ? 'admin-selected-row' : ''} cursor-pointer`}
                  onClick={() => setSelectedId(person.id)}
                >
                  <td className="px-4 py-3">
                    {person.role === 'ADMIN' ? (
                      <button
                        type="button"
                        className="text-left font-semibold text-fg hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        onClick={() => setSelectedId(person.id)}
                      >
                        {person.full_name}
                      </button>
                    ) : (
                      <Link
                        to={person.role === 'STUDENT' ? `/admin/students/${person.id}` : `/admin/instructors/${person.id}`}
                        className="inline-flex min-h-10 items-center text-left font-semibold text-fg hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      >
                        {person.full_name}
                      </Link>
                    )}
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
                  <td className="whitespace-nowrap px-4 py-3">
                    {person.role === 'ADMIN' ? (
                      <span className="text-fg-secondary">—</span>
                    ) : (
                      <Link
                        to={person.role === 'STUDENT' ? `/admin/students/${person.id}` : `/admin/instructors/${person.id}`}
                        className="inline-flex min-h-10 items-center font-semibold text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      >
                        {lang === 'vi' ? 'Mở hồ sơ 360' : 'Open 360 profile'}
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>

          <aside className="admin-detail-panel" aria-label={lang === 'vi' ? 'Hồ sơ người dùng được chọn' : 'Selected user profile'}>
            {selectedPerson ? (
              <>
                <div className="flex items-start gap-3 border-b border-line pb-4">
                  <span className="admin-avatar" aria-hidden="true">
                    {selectedPerson.full_name?.split(/\s+/).slice(-2).map((part) => part[0]).join('').toUpperCase() || '?'}
                  </span>
                  <div className="min-w-0">
                    <p className="font-display text-base font-bold text-fg">{selectedPerson.full_name}</p>
                    <p className="mt-0.5 truncate text-xs text-fg-muted">{selectedPerson.email}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <span className="badge badge-neutral text-[9px] font-bold">{adminRoleLabel(t, selectedPerson.role)}</span>
                      <span className={`badge text-[9px] font-bold ${selectedPerson.is_active ? 'badge-success' : 'badge-danger'}`}>
                        {selectedPerson.is_active ? t('admin.usersActive') : t('admin.usersLocked')}
                      </span>
                    </div>
                  </div>
                </div>

                <dl className="space-y-3 py-4 text-xs">
                  <div className="flex items-start gap-2">
                    <Mail size={14} className="mt-0.5 shrink-0 text-fg-muted" aria-hidden="true" />
                    <div><dt className="text-fg-muted">Email</dt><dd className="mt-0.5 break-all font-semibold text-fg">{selectedPerson.email}</dd></div>
                  </div>
                  <div className="flex items-start gap-2">
                    <ShieldCheck size={14} className="mt-0.5 shrink-0 text-fg-muted" aria-hidden="true" />
                    <div><dt className="text-fg-muted">{t('admin.usersRole')}</dt><dd className="mt-0.5 font-semibold text-fg">{adminRoleLabel(t, selectedPerson.role)}</dd></div>
                  </div>
                </dl>

                <div className="border-t border-line pt-4">
                  <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.06em] text-fg-muted">{t('admin.peopleAcademic')}</p>
                  <dl className="grid grid-cols-2 gap-2">
                    {Object.entries(selectedPerson.academic_summary || {}).map(([key, value]) => (
                      <div key={key} className="rounded-md border border-line bg-surface-elevated p-2.5">
                        <dt className="text-[9px] uppercase tracking-wide text-fg-muted">{adminSummaryFieldLabel(t, key)}</dt>
                        <dd className="mono mt-1 text-sm font-bold text-fg">{value}</dd>
                      </div>
                    ))}
                  </dl>
                  {selectedPerson.role !== 'ADMIN' && (
                    <Link
                      to={selectedPerson.role === 'STUDENT' ? `/admin/students/${selectedPerson.id}` : `/admin/instructors/${selectedPerson.id}`}
                      className="btn btn-accent mt-4 flex min-h-10 w-full items-center justify-center gap-2 text-xs"
                    >
                      <UserRound size={14} aria-hidden="true" />
                      {t('admin.peopleOpen360')}
                      <ArrowRight size={13} aria-hidden="true" />
                    </Link>
                  )}
                </div>
              </>
            ) : (
              <p className="text-xs text-fg-muted">{t('admin.peopleEmpty')}</p>
            )}
          </aside>
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
