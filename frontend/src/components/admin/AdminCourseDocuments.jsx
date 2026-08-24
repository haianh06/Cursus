import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, Archive, XCircle, AlertCircle, Eye, Loader2 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  getAdminCourseDocuments,
  validateAdminCourseDocument,
  publishAdminCourseDocument,
  archiveAdminCourseDocument,
  deleteAdminCourseDocument
} from '../../lib/api';


export default function AdminCourseDocuments({ courseCode }) {
  const { lang, t } = useLanguage();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // States for individual actions
  const [actionLoading, setActionLoading] = useState({});
  
  // States for publish/archive reason modal
  const [reasonModal, setReasonModal] = useState(null); // { type: 'publish' | 'archive', docId, reason }

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
          onClick={() => alert('File upload UI not implemented yet in this component. Admin upload is handled by replaceAdminCourseDocument API.')}
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
