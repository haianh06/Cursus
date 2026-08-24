import React, { useState, useEffect } from 'react';
import { WifiOff, Wifi } from 'lucide-react';

/**
 * OfflineBanner — monitors network connectivity and surfaces a non-blocking
 * status banner. Auto-dismisses 2.5 s after the connection is restored.
 *
 * Pattern: Linear's connection-lost toast / GitHub's offline banner.
 * Placement: mounted once at root in App.jsx, renders above everything else.
 */
export default function OfflineBanner() {
  const [online, setOnline] = useState(() => navigator.onLine);
  const [visible, setVisible] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);

  useEffect(() => {
    let autoHideTimer = null;

    const handleOffline = () => {
      setOnline(false);
      setReconnecting(false);
      setVisible(true);
      if (autoHideTimer) clearTimeout(autoHideTimer);
    };

    const handleOnline = () => {
      setOnline(true);
      setReconnecting(false);
      // Show "reconnected" state briefly, then slide out
      autoHideTimer = setTimeout(() => setVisible(false), 2500);
    };

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    // If already offline on mount, show immediately
    if (!navigator.onLine) setVisible(true);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
      if (autoHideTimer) clearTimeout(autoHideTimer);
    };
  }, []);

  if (!visible) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={`offline-banner ${online ? 'offline-banner--reconnected' : 'offline-banner--offline'}`}
    >
      <div className="offline-banner__inner">
        {online ? (
          <>
            <span className="offline-banner__icon-wrap offline-banner__icon-wrap--online">
              <Wifi size={12} />
            </span>
            <span className="offline-banner__text">
              Đã kết nối lại — Dữ liệu đang được đồng bộ
            </span>
          </>
        ) : (
          <>
            <span className="offline-banner__icon-wrap offline-banner__icon-wrap--offline">
              <WifiOff size={12} />
            </span>
            <span className="offline-banner__text">
              Không có kết nối mạng — Một số tính năng có thể không hoạt động
            </span>
            <span className="offline-banner__dots" aria-hidden="true">
              <span /><span /><span />
            </span>
          </>
        )}
      </div>
    </div>
  );
}
