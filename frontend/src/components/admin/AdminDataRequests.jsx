import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, Check, CheckCircle2, ChevronRight, Clock3, FileText, FileX, Loader2, Play, Search, Trash2, X } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import Modal from '../shared/Modal';
import Button from '../shared/Button';
import EmptyState from '../shared/EmptyState';
import {
  completeDataRequest,
  confirmDeleteDataRequest,
  getAdminDataRequests,
  previewDeleteDataRequest,
  processDataRequest,
  rejectDataRequest
} from '../../lib/api';

/**
 * Custom confirm modal that includes a text area for "admin notes"
 * to satisfy the spec: "cả 2 cần ghi chú lý do ≥10 ký tự".
 */
function ActionWithReasonModal({ open, title, message, confirmLabel, busy, onConfirm, onCancel, requireReason = true, minLength = 10, lang = 'vi' }) {
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (open) setReason('');
  }, [open]);

  const isValid = !requireReason || reason.trim().length >= minLength;

  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      lang={lang}
      footer={
        <>
          <Button variant="outline" size="md" onClick={onCancel}>
            {lang === 'vi' ? 'Huỷ' : 'Cancel'}
          </Button>
          <Button variant="primary" size="md" busy={busy} disabled={!isValid} onClick={() => onConfirm(reason.trim())}>
            {busy ? <Loader2 size={14} className="animate-spin" /> : confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-[13px] text-fg-secondary mb-4">{message}</p>
      {requireReason && (
        <div className="space-y-1.5">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">
            {lang === 'vi' ? `Ghi chú (bắt buộc, ≥${minLength} ký tự)` : `Reason (required, ≥${minLength} chars)`}
          </label>
          <textarea
            autoFocus
            className="input min-h-[80px] py-2 text-[13px]"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={lang === 'vi' ? 'Nhập lý do xử lý...' : 'Enter reasoning...'}
            disabled={busy}
          />
        </div>
      )}
    </Modal>
  );
}

export default function AdminDataRequests() {
  const { lang } = useLanguage();
  const [requests, setRequests] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  // Modal states
  const [actionReq, setActionReq] = useState(null);
  const [actionType, setActionType] = useState(null); // 'process', 'reject', 'complete', 'delete_confirm'
  
  // Delete preview states
  const [previewData, setPreviewData] = useState(null); // { counts, hash }
  const [previewError, setPreviewError] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const load = useCallback(() => {
    setError(null);
    getAdminDataRequests()
      .then(res => setRequests(res.items))
      .catch(err => setError(err.message || String(err)));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (reason) => {
    if (!actionReq || !actionType) return;
    setBusyId(actionReq.id);
    setError(null);
    try {
      if (actionType === 'process') await processDataRequest(actionReq.id, reason);
      else if (actionType === 'reject') await rejectDataRequest(actionReq.id, reason);
      else if (actionType === 'complete') await completeDataRequest(actionReq.id, reason);
      else if (actionType === 'delete_confirm') {
        if (!previewData?.hash) throw new Error("Missing preview hash");
        await confirmDeleteDataRequest(actionReq.id, reason, previewData.hash);
      }
      setActionReq(null);
      setActionType(null);
      setPreviewData(null);
      load();
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusyId(null);
    }
  };

  const handlePreviewDelete = async (req) => {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const res = await previewDeleteDataRequest(req.id);
      setPreviewData({ counts: res.preview, hash: res.hash });
      setActionReq(req);
      setActionType('delete_confirm');
    } catch (err) {
      setPreviewError(err.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const statusBadge = (status) => {
    const map = {
      PENDING: { label: lang === 'vi' ? 'Đang chờ' : 'Pending', cls: 'bg-warning-soft text-warning' },
      IN_PROGRESS: { label: lang === 'vi' ? 'Đang xử lý' : 'In Progress', cls: 'bg-accent-soft text-accent' },
      COMPLETED: { label: lang === 'vi' ? 'Hoàn tất' : 'Completed', cls: 'bg-success-soft text-success' },
      REJECTED: { label: lang === 'vi' ? 'Đã từ chối' : 'Rejected', cls: 'bg-danger-soft text-danger' }
    };
    const c = map[status] || { label: status, cls: 'bg-neutral text-fg' };
    return <span className={`badge text-[10px] ${c.cls}`}>{c.label}</span>;
  };

  const selectedRequest = requests?.find((request) => request.id === selectedId) || requests?.[0] || null;
  const statusCounts = (requests || []).reduce((counts, request) => ({
    ...counts,
    [request.status]: (counts[request.status] || 0) + 1,
  }), {});

  return (
    <div className="flex flex-col gap-6 text-left">
      {error && (
        <p className="flex items-center gap-2 text-[13px] text-danger bg-danger-soft p-3 rounded-lg">
          <AlertCircle size={15} className="shrink-0" /> {error}
        </p>
      )}

      {requests && (
        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label={lang === 'vi' ? 'Tổng hợp yêu cầu dữ liệu' : 'Data request summary'}>
          {[
            { key: 'PENDING', label: lang === 'vi' ? 'Mới' : 'New', icon: FileText, tone: 'text-accent bg-accent-soft' },
            { key: 'IN_PROGRESS', label: lang === 'vi' ? 'Đang xử lý' : 'In progress', icon: Clock3, tone: 'text-warning bg-warning-soft' },
            { key: 'COMPLETED', label: lang === 'vi' ? 'Hoàn tất' : 'Completed', icon: CheckCircle2, tone: 'text-success bg-success-soft' },
            { key: 'REJECTED', label: lang === 'vi' ? 'Từ chối' : 'Rejected', icon: FileX, tone: 'text-danger bg-danger-soft' },
          ].map(({ key, label, icon: Icon, tone }) => (
            <article key={key} className="admin-stat-card">
              <span className={`admin-stat-icon ${tone}`}><Icon size={16} aria-hidden="true" /></span>
              <div><p className="text-[10px] font-bold uppercase tracking-wide text-fg-muted">{label}</p><p className="mono mt-1 text-2xl font-bold text-fg">{statusCounts[key] || 0}</p></div>
            </article>
          ))}
        </section>
      )}

      {/* Delete Preview Modal */}
      {actionType === 'delete_confirm' && previewData && (
        <ActionWithReasonModal
          open={true}
          title={lang === 'vi' ? 'Xác nhận xoá dữ liệu' : 'Confirm Data Deletion'}
          message={
            <div className="space-y-3">
              <p className="font-bold text-danger flex items-center gap-2">
                <AlertTriangle size={15} /> 
                {lang === 'vi' ? 'CẢNH BÁO: Hành động này không thể hoàn tác!' : 'WARNING: This action cannot be undone!'}
              </p>
              <p>{lang === 'vi' ? 'Tóm tắt dữ liệu sẽ bị xoá vĩnh viễn:' : 'Summary of data to be permanently deleted:'}</p>
              <ul className="list-disc pl-5 font-mono text-[11px] bg-danger-soft p-2 rounded">
                <li>Enrollments: {previewData.counts.enrollments}</li>
                <li>Submissions: {previewData.counts.submissions}</li>
                <li>Conversations: {previewData.counts.conversations}</li>
                <li>Plans: {previewData.counts.plans}</li>
                <li>Reflections: {previewData.counts.reflections}</li>
                <li>Risk Signals: {previewData.counts.risk_signals}</li>
              </ul>
              <p className="text-[10px] text-fg-muted mt-2">Hash: {previewData.hash.substring(0, 16)}...</p>
            </div>
          }
          confirmLabel={lang === 'vi' ? 'Xoá vĩnh viễn' : 'Delete permanently'}
          busy={busyId === actionReq?.id}
          onConfirm={handleAction}
          onCancel={() => { setActionReq(null); setActionType(null); setPreviewData(null); }}
          lang={lang}
        />
      )}

      {/* Standard Action Modal */}
      {['process', 'reject', 'complete'].includes(actionType) && (
        <ActionWithReasonModal
          open={true}
          title={
            actionType === 'process' ? (lang === 'vi' ? 'Bắt đầu xử lý' : 'Start Processing') :
            actionType === 'reject' ? (lang === 'vi' ? 'Từ chối yêu cầu' : 'Reject Request') :
            (lang === 'vi' ? 'Hoàn tất yêu cầu' : 'Complete Request')
          }
          message={
            lang === 'vi' 
            ? `Vui lòng nhập ghi chú quản trị cho hành động này đối với yêu cầu của ${actionReq?.requesterEmail}.`
            : `Please enter admin notes for this action on the request from ${actionReq?.requesterEmail}.`
          }
          confirmLabel={lang === 'vi' ? 'Xác nhận' : 'Confirm'}
          busy={busyId === actionReq?.id}
          onConfirm={handleAction}
          onCancel={() => { setActionReq(null); setActionType(null); }}
          lang={lang}
        />
      )}

      <section className="space-y-4">
        <h2 className="flex items-center gap-2 text-sm font-bold text-fg">
          <Search size={16} className="text-accent" /> {lang === 'vi' ? 'Yêu cầu dữ liệu (DSAR)' : 'Data Requests (DSAR)'}
        </h2>
        
        {previewError && <p className="text-[12px] text-danger">{previewError}</p>}

        {!requests ? (
          <div className="flex justify-center p-8"><Loader2 className="animate-spin text-fg-muted" /></div>
        ) : requests.length === 0 ? (
          <EmptyState
            title={lang === 'vi' ? 'Chưa có yêu cầu dữ liệu' : 'No data requests'}
            description={lang === 'vi' ? 'Các yêu cầu truy cập, xuất hoặc xoá dữ liệu sẽ xuất hiện tại đây để quản trị viên xử lý.' : 'Access, export, and deletion requests will appear here for admin review.'}
          />
        ) : (
          <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_21rem]">
          <div className="overflow-x-auto rounded-lg border border-line bg-surface-card">
            <table className="data-table w-full text-[13px]">
              <thead>
                <tr>
                  <th>{lang === 'vi' ? 'Loại' : 'Type'}</th>
                  <th>{lang === 'vi' ? 'Trạng thái' : 'Status'}</th>
                  <th>{lang === 'vi' ? 'Người yêu cầu' : 'Requester'}</th>
                  <th>{lang === 'vi' ? 'Thời gian' : 'Date'}</th>
                  <th className="text-right">{lang === 'vi' ? 'Hành động' : 'Actions'}</th>
                </tr>
              </thead>
              <tbody>
                {requests.map(req => (
                  <tr key={req.id} className={selectedRequest?.id === req.id ? 'admin-selected-row' : ''}>
                    <td className="font-semibold">{req.requestType}</td>
                    <td>{statusBadge(req.status)}</td>
                    <td>{req.requesterEmail}</td>
                    <td>{new Date(req.createdAt).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}</td>
                    <td>
                      <button type="button" className="ml-auto flex min-h-9 items-center gap-1 text-xs font-semibold text-accent" onClick={() => setSelectedId(req.id)}>
                        {lang === 'vi' ? 'Chi tiết' : 'Details'} <ChevronRight size={13} aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <aside className="admin-detail-panel" aria-label={lang === 'vi' ? 'Chi tiết yêu cầu dữ liệu' : 'Data request details'}>
            {selectedRequest && (
              <>
                <div className="flex items-start justify-between gap-3 border-b border-line pb-4">
                  <div><p className="mono text-xs font-bold text-accent">{selectedRequest.id}</p><h3 className="mt-1 font-display text-base font-bold text-fg">{selectedRequest.requestType}</h3></div>
                  {statusBadge(selectedRequest.status)}
                </div>
                <dl className="space-y-3 py-4 text-xs">
                  <div><dt className="text-fg-muted">{lang === 'vi' ? 'Người yêu cầu' : 'Requester'}</dt><dd className="mt-1 break-all font-semibold text-fg">{selectedRequest.requesterEmail}</dd></div>
                  <div><dt className="text-fg-muted">{lang === 'vi' ? 'Ngày gửi' : 'Submitted'}</dt><dd className="mono mt-1 text-fg-secondary">{new Date(selectedRequest.createdAt).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}</dd></div>
                  {selectedRequest.updatedAt && <div><dt className="text-fg-muted">{lang === 'vi' ? 'Cập nhật gần nhất' : 'Last updated'}</dt><dd className="mono mt-1 text-fg-secondary">{new Date(selectedRequest.updatedAt).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}</dd></div>}
                </dl>
                <div className="mt-auto space-y-2 border-t border-line pt-4">
                  {selectedRequest.status === 'PENDING' && (
                    <div className="grid grid-cols-2 gap-2">
                      <button type="button" className="btn btn-outline min-h-10 text-xs text-danger" onClick={() => { setActionReq(selectedRequest); setActionType('reject'); }}><X size={13} />{lang === 'vi' ? 'Từ chối' : 'Reject'}</button>
                      <button type="button" className="btn btn-accent min-h-10 text-xs" onClick={() => { setActionReq(selectedRequest); setActionType('process'); }}><Play size={13} />{lang === 'vi' ? 'Xử lý' : 'Process'}</button>
                    </div>
                  )}
                  {selectedRequest.status === 'IN_PROGRESS' && selectedRequest.requestType !== 'DELETE' && (
                    <button type="button" className="btn btn-accent min-h-10 w-full text-xs" onClick={() => { setActionReq(selectedRequest); setActionType('complete'); }}><Check size={13} />{lang === 'vi' ? 'Hoàn tất yêu cầu' : 'Complete request'}</button>
                  )}
                  {selectedRequest.status === 'IN_PROGRESS' && selectedRequest.requestType === 'DELETE' && (
                    <button type="button" className="btn min-h-10 w-full border border-danger text-xs text-danger hover:bg-danger-soft" onClick={() => handlePreviewDelete(selectedRequest)} disabled={previewLoading}>
                      {previewLoading ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}{lang === 'vi' ? 'Xem trước dữ liệu sẽ xoá' : 'Preview deletion'}
                    </button>
                  )}
                </div>
              </>
            )}
          </aside>
          </div>
        )}
      </section>
    </div>
  );
}
