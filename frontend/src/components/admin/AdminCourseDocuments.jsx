import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, Archive, XCircle, AlertCircle, Eye, Loader2, RefreshCw } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  getAdminCourseDocuments,
  uploadAdminCourseDocument,
  replaceAdminCourseDocument,
  validateAdminCourseDocument,
  publishAdminCourseDocument,
  archiveAdminCourseDocument,
  deleteAdminCourseDocument
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
  const { lang, t } = useLanguage();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // States for individual actions
  const [actionLoading, setActionLoading] = useState({});
  
  // States for publish/archive reason modal
  const [reasonModal, setReasonModal] = useState(null); // { type: 'publish' | 'archive', docId, reason }

  // Upload / replace modal: { mode: 'upload' | 'replace', documentId?, file, docType, submitting, error }
  const [uploadModal, setUploadModal] = useState(null);

  const loadDocs = async () => {
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
  };

  useEffect(() => {
    loadDocs();
  }, [courseCode]);

  const handleAction = async (docId, actionName, actionFn) => {
    setActionLoading(prev => ({ ...prev, [docId]: actionName }));
    try {
      await actionFn();
      await loadDocs();
    } catch (err) {
      alert(`Action failed: ${err.message || err}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [docId]: null }));
    }
  };

  const submitReason = async () => {
    if (!reasonModal.reason || reasonModal.reason.length < 5) {
      alert(lang === 'vi' ? 'Lý do phải dài ít nhất 5 ký tự.' : 'Reason must be at least 5 characters.');
      return;
    }
    
    const { docId, type, reason } = reasonModal;
    setReasonModal(null);
    
    if (type === 'publish') {
      await handleAction(docId, 'publish', () => publishAdminCourseDocument(courseCode, docId, reason));
    } else {
      await handleAction(docId, 'archive', () => archiveAdminCourseDocument(courseCode, docId, reason));
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
      <div className="p-4 bg-danger-soft border-t border-danger/20 text-xs text-danger flex items-start gap-2">
        <AlertCircle size={14} className="mt-0.5" />
        <span>{error}</span>
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
        <button
          className="btn btn-accent text-[10px] px-2.5 py-1.5 rounded-md flex items-center gap-1 cursor-pointer"
          onClick={() => setUploadModal({ mode: 'upload', file: null, docType: 'SYLLABUS', submitting: false, error: null })}
        >
          <Upload size={12} /> {lang === 'vi' ? 'Tải lên tài liệu' : 'Upload document'}
        </button>
      </div>

      {documents.length === 0 ? (
        <p className="text-xs text-fg-muted">{lang === 'vi' ? 'Chưa có tài liệu nào.' : 'No documents found.'}</p>
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
                          className="btn-ghost p-1 rounded hover:text-accent disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Validate' : 'Validate'}
                          onClick={() => handleAction(doc.id, 'validate', () => validateAdminCourseDocument(courseCode, doc.id))}
                          disabled={actionLoading[doc.id]}
                        >
                          {actionLoading[doc.id] === 'validate' ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                        </button>
                      )}
                      
                      {(doc.publication_status === 'DRAFT' || doc.publication_status === 'READY_FOR_REVIEW') && (
                        <button 
                          className="btn-ghost p-1 rounded hover:text-success disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Publish (Bắt đầu áp dụng)' : 'Publish'}
                          onClick={() => setReasonModal({ type: 'publish', docId: doc.id, reason: '' })}
                          disabled={actionLoading[doc.id]}
                        >
                          {actionLoading[doc.id] === 'publish' ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />}
                        </button>
                      )}

                      {doc.publication_status === 'PUBLISHED' && (
                        <button
                          className="btn-ghost p-1 rounded hover:text-warning disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Archive (Lưu trữ)' : 'Archive'}
                          onClick={() => setReasonModal({ type: 'archive', docId: doc.id, reason: '' })}
                          disabled={actionLoading[doc.id]}
                        >
                          {actionLoading[doc.id] === 'archive' ? <Loader2 size={13} className="animate-spin" /> : <Archive size={13} />}
                        </button>
                      )}

                      {(doc.publication_status === 'DRAFT' || doc.publication_status === 'READY_FOR_REVIEW') && (
                        <button
                          className="btn-ghost p-1 rounded hover:text-accent disabled:opacity-50 cursor-pointer"
                          title={lang === 'vi' ? 'Thay thế file' : 'Replace file'}
                          onClick={() => setUploadModal({ mode: 'replace', documentId: doc.id, file: null, submitting: false, error: null })}
                          disabled={actionLoading[doc.id]}
                        >
                          <RefreshCw size={13} />
                        </button>
                      )}

                      <button
                        className="btn-ghost p-1 rounded hover:text-danger disabled:opacity-50 cursor-pointer"
                        title={lang === 'vi' ? 'Xóa' : 'Delete'}
                        onClick={() => {
                          if (confirm(lang === 'vi' ? 'Xác nhận xóa tài liệu này?' : 'Delete this document?')) {
                            handleAction(doc.id, 'delete', () => deleteAdminCourseDocument(courseCode, doc.id));
                          }
                        }}
                        disabled={actionLoading[doc.id]}
                      >
                        {actionLoading[doc.id] === 'delete' ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {uploadModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-surface-card w-full max-w-sm rounded-xl shadow-panel border border-line p-5">
            <h3 className="text-sm font-bold text-fg mb-3">
              {uploadModal.mode === 'replace'
                ? (lang === 'vi' ? 'Thay thế tài liệu' : 'Replace document')
                : (lang === 'vi' ? 'Tải lên tài liệu mới' : 'Upload new document')}
            </h3>

            {uploadModal.mode === 'upload' && (
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

            <div className="mb-4">
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

            {uploadModal.error && (
              <p className="text-[11px] text-danger mb-3 flex items-start gap-1.5">
                <AlertCircle size={12} className="mt-0.5 shrink-0" />
                <span>{uploadModal.error}</span>
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                className="btn btn-ghost text-xs px-3 py-1.5 rounded-lg cursor-pointer"
                onClick={() => setUploadModal(null)}
                disabled={uploadModal.submitting}
              >
                {lang === 'vi' ? 'Hủy' : 'Cancel'}
              </button>
              <button
                className="btn btn-accent text-xs px-3 py-1.5 rounded-lg cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                onClick={submitUpload}
                disabled={!uploadModal.file || uploadModal.submitting}
              >
                {uploadModal.submitting
                  ? (lang === 'vi' ? 'Đang tải lên...' : 'Uploading...')
                  : (lang === 'vi' ? 'Tải lên' : 'Upload')}
              </button>
            </div>
          </div>
        </div>
      )}

      {reasonModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-surface-card w-full max-w-sm rounded-xl shadow-panel border border-line p-5">
            <h3 className="text-sm font-bold text-fg mb-3">
              {reasonModal.type === 'publish' 
                ? (lang === 'vi' ? 'Lý do Publish' : 'Publish Reason') 
                : (lang === 'vi' ? 'Lý do Archive' : 'Archive Reason')}
            </h3>
            <textarea
              className="input text-xs w-full mb-4 resize-none h-24"
              placeholder={lang === 'vi' ? 'Nhập lý do (min 5 ký tự)...' : 'Enter reason (min 5 chars)...'}
              value={reasonModal.reason}
              onChange={e => setReasonModal({ ...reasonModal, reason: e.target.value })}
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button className="btn btn-ghost text-xs px-3 py-1.5 rounded-lg cursor-pointer" onClick={() => setReasonModal(null)}>
                {lang === 'vi' ? 'Hủy' : 'Cancel'}
              </button>
              <button className="btn btn-accent text-xs px-3 py-1.5 rounded-lg cursor-pointer" onClick={submitReason}>
                {lang === 'vi' ? 'Xác nhận' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
