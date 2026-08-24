import React, { useCallback, useEffect, useState } from 'react';
import { ListChecks, CheckCircle2, XCircle, RefreshCw, Save } from 'lucide-react';
import { getInstructorPracticeSets, getInstructorPracticeSet, updatePracticeItem, reviewPracticeSet, regeneratePracticeSet } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';
import ConfirmDialog from '../shared/ConfirmDialog';

const STATUS_FILTERS = ['PENDING_REVIEW', 'PUBLISHED', 'REJECTED', 'DRAFT'];

/** Instructor: review queue for generated practice sets — list pending sets,
 * edit an item's content, then publish or reject the whole set. Backed by
 * /instructor/practice*. */
export default function InstructorPracticeQueuePanel() {
  const { lang } = useLanguage();
  const [statusFilter, setStatusFilter] = useState('PENDING_REVIEW');
  const [sets, setSets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);
  const [editDrafts, setEditDrafts] = useState({});
  const [confirmPublish, setConfirmPublish] = useState(false);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await getInstructorPracticeSets(statusFilter);
      setSets(list || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const openSet = async (setId) => {
    setSelectedId(setId);
    setDetail(null);
    setError(null);
    try {
      const data = await getInstructorPracticeSet(setId);
      setDetail(data);
      const drafts = {};
      (data.items || []).forEach((item) => {
        drafts[item.id] = { prompt: item.prompt, answer: item.answer || '', explanation: item.explanation || '' };
      });
      setEditDrafts(drafts);
    } catch (err) {
      setError(err);
    }
  };

  const saveItem = async (itemId) => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const draft = editDrafts[itemId];
      const updated = await updatePracticeItem(selectedId, itemId, draft);
      setDetail(updated);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const decide = async (decision) => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await reviewPracticeSet(selectedId, decision);
      setDetail(updated);
      await loadList();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const confirmAndPublish = async () => {
    setConfirmPublish(false);
    await decide('PUBLISHED');
  };

  const regenerate = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await regeneratePracticeSet(selectedId);
      setDetail(updated);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card p-5 text-left">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ListChecks size={16} className="text-accent" />
          <h2 className="text-sm font-bold text-fg">{lang === 'vi' ? 'Hàng đợi duyệt bài luyện tập' : 'Practice review queue'}</h2>
        </div>
        <select className="input text-xs w-44" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_FILTERS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-[11px] text-danger mb-3">{error.message}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="divide-y divide-line border border-line rounded-lg overflow-hidden max-h-96 overflow-y-auto">
          {loading ? (
            <p className="text-xs text-fg-muted p-4 text-center">{lang === 'vi' ? 'Đang tải…' : 'Loading…'}</p>
          ) : sets.length === 0 ? (
            <p className="text-xs text-fg-muted p-4 text-center">{lang === 'vi' ? 'Không có bộ nào.' : 'Nothing here.'}</p>
          ) : (
            sets.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => openSet(s.id)}
                className={`w-full text-left p-3 cursor-pointer hover:bg-surface-elevated ${selectedId === s.id ? 'bg-accent-soft' : ''}`}
              >
                <p className="text-xs font-bold text-fg">{s.courseCode} · {lang === 'vi' ? 'Tuần' : 'Week'} {s.weekNumber}</p>
                <p className="text-[11px] text-fg-muted">{s.itemCount} {lang === 'vi' ? 'câu' : 'items'} · {s.status}</p>
              </button>
            ))
          )}
        </div>

        <div className="border border-line rounded-lg p-3 max-h-96 overflow-y-auto">
          {!detail ? (
            <p className="text-xs text-fg-muted text-center py-8">
              {lang === 'vi' ? 'Chọn một bộ để xem chi tiết.' : 'Select a set to review.'}
            </p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-fg">{detail.courseCode} · W{detail.weekNumber}</p>
                <button type="button" className="btn-ghost text-[11px] flex items-center gap-1 cursor-pointer" onClick={regenerate} disabled={busy}>
                  <RefreshCw size={11} className={busy ? 'animate-spin' : ''} /> {lang === 'vi' ? 'Tạo lại' : 'Regenerate'}
                </button>
              </div>
              {(detail.items || []).map((item) => (
                <div key={item.id} className="p-2.5 rounded-lg bg-surface-elevated border border-line space-y-1.5">
                  <p className="text-[10px] font-bold uppercase text-fg-muted">{item.kind}</p>
                  <textarea
                    className="input text-xs w-full"
                    rows={2}
                    value={editDrafts[item.id]?.prompt ?? item.prompt}
                    onChange={(e) => setEditDrafts((p) => ({ ...p, [item.id]: { ...p[item.id], prompt: e.target.value } }))}
                  />
                  {item.kind === 'FLASHCARD' && (
                    <input
                      className="input text-xs w-full"
                      placeholder={lang === 'vi' ? 'Đáp án' : 'Answer'}
                      value={editDrafts[item.id]?.answer ?? item.answer ?? ''}
                      onChange={(e) => setEditDrafts((p) => ({ ...p, [item.id]: { ...p[item.id], answer: e.target.value } }))}
                    />
                  )}
                  <input
                    className="input text-xs w-full"
                    placeholder={lang === 'vi' ? 'Giải thích' : 'Explanation'}
                    value={editDrafts[item.id]?.explanation ?? item.explanation ?? ''}
                    onChange={(e) => setEditDrafts((p) => ({ ...p, [item.id]: { ...p[item.id], explanation: e.target.value } }))}
                  />
                  <button
                    type="button"
                    className="btn btn-outline text-[10px] px-2.5 py-1 rounded-md cursor-pointer flex items-center gap-1"
                    onClick={() => saveItem(item.id)}
                    disabled={busy}
                  >
                    <Save size={10} /> {lang === 'vi' ? 'Lưu câu này' : 'Save item'}
                  </button>
                </div>
              ))}

              {detail.status === 'PENDING_REVIEW' && (
                <div className="flex gap-2 justify-end pt-2 border-t border-line">
                  <button type="button" className="btn btn-outline text-xs px-3.5 py-1.5 rounded-lg cursor-pointer flex items-center gap-1.5" onClick={() => decide('REJECTED')} disabled={busy}>
                    <XCircle size={12} /> {lang === 'vi' ? 'Từ chối' : 'Reject'}
                  </button>
                  <button type="button" className="btn btn-accent text-xs px-3.5 py-1.5 rounded-lg cursor-pointer flex items-center gap-1.5" onClick={() => setConfirmPublish(true)} disabled={busy}>
                    <CheckCircle2 size={12} /> {lang === 'vi' ? 'Xuất bản' : 'Publish'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={confirmPublish}
        lang={lang}
        busy={busy}
        title={lang === 'vi' ? 'Xuất bản bộ luyện tập này?' : 'Publish this practice set?'}
        message={
          lang === 'vi'
            ? 'Sinh viên sẽ thấy bộ luyện tập này ngay lập tức.'
            : 'Students will see this practice set immediately.'
        }
        confirmLabel={lang === 'vi' ? 'Xuất bản' : 'Publish'}
        onCancel={() => setConfirmPublish(false)}
        onConfirm={confirmAndPublish}
      />
    </div>
  );
}
