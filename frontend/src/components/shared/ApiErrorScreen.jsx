import React, { useState, useEffect, useCallback } from 'react';
import { RotateCcw, ChevronDown, ChevronUp, Wifi, WifiOff, Server, Clock } from 'lucide-react';
import CursusMascot from './CursusMascot';

const AUTO_RETRY_SECONDS = 30;

/**
 * ApiErrorScreen — full-page "server unreachable" state.
 *
 * Design references: Linear's connection-error modal, Vercel's 500 page,
 * Notion's offline screen. Key principles:
 * - Human-readable copy, never raw error codes as primary content.
 * - Auto-retry countdown so users know help is coming.
 * - Technical detail available but collapsed (accordion pattern).
 * - Cursus Assistant mascot in `error` state for brand continuity.
 *
 * Props:
 *   onRetry    — async fn to call when user clicks retry
 *   error      — optional raw Error object (for details accordion)
 *   context    — 'landing' | 'dashboard' (adjusts copy tone)
 */
export default function ApiErrorScreen({ onRetry, error, context = 'dashboard' }) {
  const [retrying, setRetrying] = useState(false);
  const [countdown, setCountdown] = useState(AUTO_RETRY_SECONDS);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const isOnline = navigator.onLine;

  const handleRetry = useCallback(async () => {
    if (retrying) return;
    setRetrying(true);
    setCountdown(AUTO_RETRY_SECONDS);
    setRetryCount((c) => c + 1);
    try {
      await onRetry?.();
    } finally {
      setRetrying(false);
    }
  }, [retrying, onRetry]);

  // Auto-retry countdown
  useEffect(() => {
    if (retrying) return;
    if (countdown <= 0) {
      handleRetry();
      return;
    }
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown, retrying, handleRetry]);

  // Reset countdown when online event fires
  useEffect(() => {
    const handleOnline = () => {
      setCountdown(3); // Fast retry when we know we're back
    };
    window.addEventListener('online', handleOnline);
    return () => window.removeEventListener('online', handleOnline);
  }, []);

  return (
    <div className="api-error-screen" role="main" aria-labelledby="api-error-heading">
      {/* Ambient background glow */}
      <div className="api-error-screen__glow api-error-screen__glow--1" aria-hidden="true" />
      <div className="api-error-screen__glow api-error-screen__glow--2" aria-hidden="true" />

      <div className="api-error-screen__content">
        {/* Mascot */}
        <div className="api-error-screen__mascot-wrap" aria-hidden="true">
          <div className="api-error-screen__mascot-ring" />
          <CursusMascot size={120} state="error" className="api-error-screen__mascot" />
        </div>

        {/* Status pill */}
        <div className="api-error-screen__status-pill">
          <span className="api-error-screen__status-dot" aria-hidden="true" />
          <span>
            {isOnline ? 'Máy chủ Cursus · Đang kiểm tra kết nối' : 'Không có internet'}
          </span>
        </div>

        {/* Heading */}
        <h1 id="api-error-heading" className="api-error-screen__heading">
          {isOnline
            ? 'Không thể kết nối tới máy chủ'
            : 'Mất kết nối mạng'}
        </h1>

        {/* Description */}
        <p className="api-error-screen__desc">
          {isOnline
            ? context === 'landing'
              ? 'Hệ thống Cursus tạm thời không phản hồi. Trang web vẫn hoạt động bình thường.'
              : 'Kiểm tra kết nối mạng hoặc thử lại. Nếu sự cố tiếp tục, hãy liên hệ bộ phận hỗ trợ.'
            : 'Kiểm tra kết nối Wi-Fi hoặc dữ liệu di động. Cursus sẽ tự động kết nối lại khi có mạng.'}
        </p>

        {/* Actions */}
        <div className="api-error-screen__actions">
          <button
            type="button"
            className="btn btn-accent px-6 py-2.5 api-error-screen__retry-btn"
            onClick={handleRetry}
            disabled={retrying}
            aria-busy={retrying}
          >
            <RotateCcw
              size={15}
              className={retrying ? 'spin' : ''}
              aria-hidden="true"
            />
            {retrying ? 'Đang thử lại…' : 'Thử lại ngay'}
          </button>

          {/* Auto-retry badge */}
          {!retrying && (
            <div className="api-error-screen__auto-retry" aria-live="polite">
              <Clock size={11} aria-hidden="true" />
              Tự động thử lại sau {countdown}s
            </div>
          )}
        </div>

        {/* Technical details accordion */}
        {(error || retryCount > 0) && (
          <div className="api-error-screen__details">
            <button
              type="button"
              className="api-error-screen__details-toggle"
              onClick={() => setDetailsOpen((v) => !v)}
              aria-expanded={detailsOpen}
            >
              <span>Chi tiết kỹ thuật</span>
              {detailsOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>

            {detailsOpen && (
              <div className="api-error-screen__details-body animate-fade-up">
                <dl className="api-error-screen__details-list">
                  {error?.message && (
                    <>
                      <dt>Lỗi</dt>
                      <dd className="mono">{error.message}</dd>
                    </>
                  )}
                  <dt>Số lần thử</dt>
                  <dd className="mono">{retryCount}</dd>
                  <dt>Trạng thái mạng</dt>
                  <dd className="mono">{isOnline ? 'Online' : 'Offline'}</dd>
                  <dt>Thời điểm</dt>
                  <dd className="mono">{new Date().toLocaleTimeString('vi-VN')}</dd>
                </dl>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ConnectionBanner — minimal variant for landing page context.
 * Shows a slim banner at the top without replacing the page content.
 */
export function ConnectionBanner({ onRetry }) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    if (retrying) return;
    setRetrying(true);
    try {
      await onRetry?.();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className="connection-banner"
    >
      <div className="connection-banner__inner">
        <Server size={13} className="connection-banner__icon" aria-hidden="true" />
        <span className="connection-banner__text">
          Máy chủ Cursus tạm thời không phản hồi — Trang thông tin vẫn hiển thị bình thường
        </span>
        <button
          type="button"
          className="connection-banner__retry"
          onClick={handleRetry}
          disabled={retrying}
        >
          <RotateCcw size={11} className={retrying ? 'spin' : ''} aria-hidden="true" />
          {retrying ? 'Đang kết nối…' : 'Thử lại'}
        </button>
      </div>
    </div>
  );
}
