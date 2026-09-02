import React, { useCallback, useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, Archive, XCircle, AlertCircle, Eye, History, Loader2, RefreshCw, RotateCcw } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import Modal from '../shared/Modal';
import Button from '../shared/Button';
import EmptyState from '../shared/EmptyState';
import ErrorState from '../shared/ErrorState';
import {
  getAdminCourseDocuments,
  getAdminCourseDocumentContent,
  uploadAdminCourseDocument,
  replaceAdminCourseDocument,
  validateAdminCourseDocument,
  publishAdminCourseDocument,
  archiveAdminCourseDocument,
  deleteAdminCourseDocument,
  getAdminCourseDocumentVersions,
  rollbackAdminCourseDocument,
} from '../../lib/api';

const DOC_TYPES = ['SYLLABUS', 'LECTURE', 'FAQ', 'LAB', 'NOTES'];
const DOC_TYPE_LABEL_VI = {
  SYLLABUS: 'Đề cương môn học',
  LECTURE: 'Bài giảng',
  FAQ: 'Hỏi đáp',
  LAB: 'Tài liệu thực hành',
  NOTES: 'Ghi chú',
};
const DOC_TYPE_LABEL_EN = {
  SYLLABUS: 'Syllabus',
  LECTURE: 'Lecture',
  FAQ: 'FAQ',
  LAB: 'Lab material',
  NOTES: 'Notes',
};
function docTypeLabel(lang, value) {
  const table = lang === 'vi' ? DOC_TYPE_LABEL_VI : DOC_TYPE_LABEL_EN;
  return table[value] || value;
}


export default function AdminCourseDocuments({ courseCode }) {
  const { lang } = useLanguage();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // States for individual actions
  const [actionLoading, setActionLoading] = useState({});
  const [actionError, setActionError] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [openHistoryId, setOpenHistoryId] = useState(null);
  const [historyByDocument, setHistoryByDocument] = useState({});
  const [historyLoadingId, setHistoryLoadingId] = useState(null);
  const [openPreviewId, setOpenPreviewId] = useState(null);
  const [previewByDocument, setPreviewByDocument] = useState({});
  const [previewLoadingId, setPreviewLoadingId] = useState(null);
  
  // States for publish/archive reason modal
  const [reasonModal, setReasonModal] = useState(null); // { type: 'publish' | 'archive', docId, reason }

  // Upload / replace modal: { mode: 'upload' | 'replace', documentId?, file, docType, submitting, error }
  const [uploadModal, setUploadModal] = useState(null);

  const loadDocs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAdminCourseDocuments(courseCode);
      setDocuments(data?.documents || []);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [courseCode]);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const handleAction = async (docId, actionName, actionFn) => {
    setActionLoading(prev => ({ ...prev, [docId]: actionName }));
    setActionError(null);
    try {
      await actionFn();
      await loadDocs();
      setHistoryByDocument({});
    } catch (err) {
      setActionError(err.message || String(err));
    } finally {
      setActionLoading(prev => ({ ...prev, [docId]: null }));
    }
  };

  const toggleHistory = async (docId) => {
    if (openHistoryId === docId) {
      setOpenHistoryId(null);
      return;
    }
    setOpenHistoryId(docId);
    if (historyByDocument[docId]) return;
    setHistoryLoadingId(docId);
    setActionError(null);
    try {
      const result = await getAdminCourseDocumentVersions(courseCode, docId);
      setHistoryByDocument((current) => ({ ...current, [docId]: result?.versions || [] }));
    } catch (err) {
      setActionError(err.message || String(err));
    } finally {
      setHistoryLoadingId(null);
    }
  };

  const togglePreview = async (docId) => {
    if (openPreviewId === docId) {
      setOpenPreviewId(null);
      return;
    }
    setOpenPreviewId(docId);
    if (previewByDocument[docId]) return;
    setPreviewLoadingId(docId);
    setActionError(null);
    try {
      const result = await getAdminCourseDocumentContent(courseCode, docId);
      setPreviewByDocument((current) => ({ ...current, [docId]: result }));
    } catch (err) {
      setActionError(err.message || String(err));
      setOpenPreviewId(null);
    } finally {
      setPreviewLoadingId(null);
    }
  };

  const submitReason = async () => {
    if (!reasonModal.reason || reasonModal.reason.length < 5) {
      setReasonModal((current) => ({
        ...current,
        error: lang === 'vi' ? 'Lý do phải dài ít nhất 5 ký tự.' : 'Reason must be at least 5 characters.',
      }));
      return;
    }
    
    const { docId, type, reason } = reasonModal;
    setReasonModal(null);
    
    if (type === 'publish') {
      await handleAction(docId, 'publish', () => publishAdminCourseDocument(courseCode, docId, reason));
    } else if (type === 'archive') {
      await handleAction(docId, 'archive', () => archiveAdminCourseDocument(courseCode, docId, reason));
    } else {
      await handleAction(docId, 'rollback', () => rollbackAdminCourseDocument(courseCode, docId, reason));
    }
  };

  const submitUpload = async () => {
    if (!uploadModal?.file) return;
    setUploadModal((prev) => ({ ...prev, submitting: true, error: null }));
    try {
      if (uploadModal.mode === 'replace') {
        await replaceAdminCourseDocument(courseCode, uploadModal.documentId, uploadModal.file);
      } else {
        await uploadAdminCourseDocument(courseCode, uploadModal.file, uploadModal.docType);
      }
      // Upload/replace runs as a background job (202) -- the new/updated row
      // isn't guaranteed to exist the instant this call returns. One short
      // wait then a normal reload covers local-file-write speed in dev;
      // if it's still mid-flight the admin sees it on their next reload.
      setUploadModal(null);
      setTimeout(loadDocs, 1200);
      await loadDocs();
    } catch (err) {
      setUploadModal((prev) => ({ ...prev, submitting: false, error: err.message || String(err) }));
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center gap-2 text-fg-muted text-xs">
        <Loader2 size={14} className="animate-spin" /> {lang === 'vi' ? 'Đang tải tài liệu...' : 'Loading documents...'}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-surface-elevated border-t border-line">
        <ErrorState
          title={lang === 'vi' ? 'Không tải được tài liệu' : 'Could not load documents'}
          description={error}
          onRetry={loadDocs}
          retryLabel={lang === 'vi' ? 'Thử lại' : 'Retry'}
        />
      </div>
    );
  }

  return (
    <div className="p-4 bg-surface-elevated border-t border-line shadow-inner text-left">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-xs font-bold text-fg flex items-center gap-1.5">
          <FileText size={14} className="text-accent" />
          {lang === 'vi' ? 'Tài liệu giáo trình (Syllabus)' : 'Curriculum Documents'}
        </h4>
        <Button
          size="sm"
          className="text-[10px]"
          onClick={() => setUploadModal({ mode: 'upload', file: null, docType: 'SYLLABUS', submitting: false, error: null })}
        >
          <Upload size={12} /> {lang === 'vi' ? 'Tải lên tài liệu' : 'Upload document'}
        </Button>
      </div>

      {actionError && (
        <div role="alert" className="mb-4 flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-soft p-3 text-xs text-danger">
          <AlertCircle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{actionError}</span>
        </div>
      )}

      {documents.length === 0 ? (
        <EmptyState title={lang === 'vi' ? 'Chưa có tài liệu nào.' : 'No documents found.'} />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="w-full text-left border-collapse whitespace-nowrap">
            <thead>
              <tr className="bg-surface-card border-b border-line text-[10px] uppercase font-bold text-fg-muted tracking-wider">
                <th className="px-3 py-2">ID / File</th>
                <th className="px-3 py-2">{lang === 'vi' ? 'Loại' : 'Type'}</th>
                <th className="px-3 py-2">{lang === 'vi' ? 'Phiên bản' : 'Version'}</th>
                <th className="px-3 py-2">{lang === 'vi' ? 'Trạng thái' : 'Status'}</th>
                <th className="px-3 py-2 text-right">{lang === 'vi' ? 'Hành động' : 'Actions'}</th>
              </tr>
            </thead>
            <tbody>
              {documents.map(doc => (
                <tr key={doc.id} className="border-b border-line last:border-b-0 hover:bg-surface-card/50 transition-colors text-xs">
                  <td className="px-3 py-2">
                    <div className="font-semibold text-fg">{doc.filename || doc.title}</div>
                    <div className="mono text-[10px] text-fg-muted mt-0.5">{doc.id}</div>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-[10px] text-fg-secondary">{docTypeLabel(lang, doc.doc_type)}</span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="mono text-[10px] px-1.5 py-0.5 rounded-md bg-surface-card border border-line text-fg-secondary">
                      {doc.version || 'v1.0'}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`badge ${
                      doc.publication_status === 'PUBLISHED' ? 'badge-success' : 
                      doc.publication_status === 'ARCHIVED' ? 'bg-surface-card text-fg-muted border border-line' : 
                      'badge-primary'
                    } text-[10px] font-bold`}>
                      {doc.publication_status || 'DRAFT'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {doc.publication_status === 'DRAFT' && (
                        <button 
                          className="btn-ghost min-h-10 min-w-10 rounded-md p-2 hover:text-accent disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Validate' : 'Validate'}
                          onClick={() => handleAction(doc.id, 'validate', () => validateAdminCourseDocument(courseCode, doc.id))}
                          disabled={actionLoading[doc.id]}
                        >
                          {actionLoading[doc.id] === 'validate' ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                        </button>
                      )}
                      
                      {(doc.publication_status === 'DRAFT' || doc.publication_status === 'READY_FOR_REVIEW') && (
                        <button 
                          className="btn-ghost min-h-10 min-w-10 rounded-md p-2 hover:text-success disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Publish (Bắt đầu áp dụng)' : 'Publish'}
                          onClick={() => setReasonModal({ type: 'publish', docId: doc.id, reason: '' })}
                          disabled={actionLoading[doc.id]}
                        >
                          {actionLoading[doc.id] === 'publish' ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />}
                        </button>
                      )}

                      {doc.publication_status === 'PUBLISHED' && (
                        <button
                          className="btn-ghost min-h-10 min-w-10 rounded-md p-2 hover:text-warning disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Archive (Lưu trữ)' : 'Archive'}
                          onClick={() => setReasonModal({ type: 'archive', docId: doc.id, reason: '' })}
                          disabled={actionLoading[doc.id]}
                        >
                          {actionLoading[doc.id] === 'archive' ? <Loader2 size={13} className="animate-spin" /> : <Archive size={13} />}
                        </button>
                      )}

                      {(doc.publication_status === 'DRAFT' || doc.publication_status === 'READY_FOR_REVIEW') && (
                        <button
                          className="btn-ghost min-h-10 min-w-10 rounded-md p-2 hover:text-accent disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Thay thế file' : 'Replace file'}
                          onClick={() => setUploadModal({ mode: 'replace', documentId: doc.id, file: null, submitting: false, error: null })}
                          disabled={actionLoading[doc.id]}
                        >
                          <RefreshCw size={13} />
                        </button>
                      )}

                      <button
                        className="btn-ghost min-h-10 min-w-10 rounded-md p-2 hover:text-accent disabled:opacity-50 cursor-pointer"
                        title={lang === 'vi' ? 'Xem trước nội dung' : 'Preview content'}
                        aria-expanded={openPreviewId === doc.id}
                        onClick={() => togglePreview(doc.id)}
                        disabled={actionLoading[doc.id]}
                      >
                        {previewLoadingId === doc.id ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />}
                      </button>

                      <button
                        className="btn-ghost min-h-10 min-w-10 rounded-md p-2 hover:text-accent disabled:opacity-50 cursor-pointer"
                        title={lang === 'vi' ? 'Lịch sử phiên bản' : 'Version history'}
                        aria-expanded={openHistoryId === doc.id}
                        onClick={() => toggleHistory(doc.id)}
                        disabled={actionLoading[doc.id]}
                      >
                        {historyLoadingId === doc.id ? <Loader2 size={13} className="animate-spin" /> : <History size={13} />}
                      </button>

                      {deleteTarget === doc.id ? (
                        <>
                          <Button
                            variant="danger"
                            size="sm"
                            className="text-[10px] font-semibold"
                            onClick={() => {
                              setDeleteTarget(null);
                              handleAction(doc.id, 'delete', () => deleteAdminCourseDocument(courseCode, doc.id));
                            }}
                            disabled={actionLoading[doc.id]}
                          >
                            {lang === 'vi' ? 'Xác nhận xoá' : 'Confirm delete'}
                          </Button>
                          <Button variant="ghost" size="sm" className="text-[10px]" onClick={() => setDeleteTarget(null)}>
                            {lang === 'vi' ? 'Huỷ' : 'Cancel'}
                          </Button>
                        </>
                      ) : (
                        <button
                          className="btn-ghost min-h-10 min-w-10 rounded-md p-2 hover:text-danger disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Xóa' : 'Delete'}
                          onClick={() => setDeleteTarget(doc.id)}
                          disabled={actionLoading[doc.id] || doc.publication_status === 'PUBLISHED' || doc.publication_status === 'ARCHIVED'}
                        >
                          {actionLoading[doc.id] === 'delete' ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {openHistoryId && (
        <section className="mt-4 rounded-lg border border-line bg-surface-card p-4" aria-label={lang === 'vi' ? 'Lịch sử phiên bản' : 'Version history'}>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h5 className="flex items-center gap-2 text-xs font-bold text-fg">
              <History size={14} className="text-accent" aria-hidden="true" />
              {lang === 'vi' ? 'Lịch sử phiên bản' : 'Version history'}
            </h5>
            <Button variant="ghost" size="sm" className="text-[10px]" onClick={() => setOpenHistoryId(null)}>
              {lang === 'vi' ? 'Đóng' : 'Close'}
            </Button>
          </div>
          {historyLoadingId === openHistoryId ? (
            <p role="status" className="flex items-center gap-2 text-xs text-fg-muted">
              <Loader2 size={13} className="animate-spin" aria-hidden="true" />
              {lang === 'vi' ? 'Đang tải lịch sử…' : 'Loading history…'}
            </p>
          ) : (
            <ol className="space-y-2">
              {(historyByDocument[openHistoryId] || []).map((version) => (
                <li key={version.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-surface-elevated p-3">
                  <div>
                    <p className="mono text-xs font-bold text-fg">v{version.version}</p>
                    <p className="mt-1 text-[10px] text-fg-muted">
                      {version.publication_status} · {version.change_reason || (lang === 'vi' ? 'Không có ghi chú' : 'No change note')}
                    </p>
                  </div>
                  {version.publication_status === 'ARCHIVED' && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-[10px]"
                      busy={actionLoading[version.id] === 'rollback'}
                      onClick={() => setReasonModal({ type: 'rollback', docId: version.id, reason: '' })}
                      disabled={actionLoading[version.id]}
                    >
                      {actionLoading[version.id] === 'rollback'
                        ? <Loader2 size={13} className="animate-spin" aria-hidden="true" />
                        : <RotateCcw size={13} aria-hidden="true" />}
                      {lang === 'vi' ? 'Khôi phục' : 'Rollback'}
                    </Button>
                  )}
                </li>
              ))}
            </ol>
          )}
        </section>
      )}

      {openPreviewId && previewByDocument[openPreviewId] && (
        <section className="mt-4 rounded-lg border border-line bg-surface-card p-4" aria-label={lang === 'vi' ? 'Nội dung tài liệu' : 'Document content'}>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h5 className="flex items-center gap-2 text-xs font-bold text-fg">
              <Eye size={14} className="text-accent" aria-hidden="true" />
              {lang === 'vi' ? 'Xem trước nội dung' : 'Content preview'}
            </h5>
            <Button variant="ghost" size="sm" className="text-[10px]" onClick={() => setOpenPreviewId(null)}>
              {lang === 'vi' ? 'Đóng' : 'Close'}
            </Button>
          </div>
          <p className="mb-2 text-[10px] text-fg-muted">
            {previewByDocument[openPreviewId].filename || previewByDocument[openPreviewId].title} · v{previewByDocument[openPreviewId].version}
          </p>
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-line bg-surface-elevated p-3 text-xs leading-relaxed text-fg-secondary">
            {previewByDocument[openPreviewId].content}
          </pre>
          {previewByDocument[openPreviewId].truncated && (
            <p className="mt-2 text-[10px] text-fg-muted">
              {lang === 'vi' ? 'Nội dung đã được rút gọn để xem trước.' : 'Content was truncated for preview.'}
            </p>
          )}
        </section>
      )}

      <Modal
        open={Boolean(uploadModal)}
        onClose={() => setUploadModal(null)}
        lang={lang}
        title={
          uploadModal?.mode === 'replace'
            ? (lang === 'vi' ? 'Thay thế tài liệu' : 'Replace document')
            : (lang === 'vi' ? 'Tải lên tài liệu mới' : 'Upload new document')
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setUploadModal(null)} disabled={uploadModal?.submitting}>
              {lang === 'vi' ? 'Hủy' : 'Cancel'}
            </Button>
            <Button
              busy={uploadModal?.submitting}
              onClick={submitUpload}
              disabled={!uploadModal?.file || uploadModal?.submitting}
            >
              {uploadModal?.submitting
                ? (lang === 'vi' ? 'Đang tải lên...' : 'Uploading...')
                : (lang === 'vi' ? 'Tải lên' : 'Upload')}
            </Button>
          </>
        }
      >
        {uploadModal?.mode === 'upload' && (
          <div className="mb-3">
            <label className="block text-[11px] font-semibold text-fg-secondary mb-1">
              {lang === 'vi' ? 'Loại tài liệu' : 'Document type'}
            </label>
            <select
              className="input text-xs w-full"
              value={uploadModal.docType}
              onChange={(e) => setUploadModal((prev) => ({ ...prev, docType: e.target.value }))}
            >
              {DOC_TYPES.map((value) => (
                <option key={value} value={value}>{docTypeLabel(lang, value)}</option>
              ))}
            </select>
          </div>
        )}

        <div className="mb-1">
          <label className="block text-[11px] font-semibold text-fg-secondary mb-1">
            {lang === 'vi' ? 'File (.md hoặc .txt, tối đa 2MB)' : 'File (.md or .txt, max 2MB)'}
          </label>
          <input
            type="file"
            accept=".md,.txt"
            className="input text-xs w-full"
            onChange={(e) => setUploadModal((prev) => ({ ...prev, file: e.target.files?.[0] || null }))}
          />
        </div>

        {uploadModal?.error && (
          <p className="text-[11px] text-danger mt-3 flex items-start gap-1.5">
            <AlertCircle size={12} className="mt-0.5 shrink-0" />
            <span>{uploadModal.error}</span>
          </p>
        )}
      </Modal>

      <Modal
        open={Boolean(reasonModal)}
        onClose={() => setReasonModal(null)}
        lang={lang}
        title={
          reasonModal?.type === 'publish'
            ? (lang === 'vi' ? 'Lý do xuất bản' : 'Publish reason')
            : reasonModal?.type === 'archive'
              ? (lang === 'vi' ? 'Lý do lưu trữ' : 'Archive reason')
              : (lang === 'vi' ? 'Lý do khôi phục phiên bản' : 'Rollback reason')
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setReasonModal(null)}>
              {lang === 'vi' ? 'Hủy' : 'Cancel'}
            </Button>
            <Button onClick={submitReason} disabled={!reasonModal || reasonModal.reason.trim().length < 5}>
              {lang === 'vi' ? 'Xác nhận' : 'Confirm'}
            </Button>
          </>
        }
      >
        {reasonModal && (
          <>
            <textarea
              className="input text-xs w-full resize-none h-24"
              placeholder={lang === 'vi' ? 'Nhập lý do (min 5 ký tự)...' : 'Enter reason (min 5 chars)...'}
              value={reasonModal.reason}
              onChange={e => setReasonModal({ ...reasonModal, reason: e.target.value, error: null })}
              autoFocus
            />
            {reasonModal.error && <p role="alert" className="mt-3 text-[11px] text-danger">{reasonModal.error}</p>}
          </>
        )}
      </Modal>
    </div>
  );
}
