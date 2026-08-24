import React from 'react';
import { RefreshCw, Copy, CheckCheck } from 'lucide-react';
import LandingLogoMark from '../landing/LandingLogoMark';

/**
 * FatalErrorScreen — Root-level React Error Boundary.
 *
 * Catches any unhandled render error that escapes FeatureErrorBoundary.
 * Renders a minimal, trust-building screen that:
 * - Never shows a blank white page to the user
 * - Avoids mascot animations (might be what broke)
 * - Offers hard-refresh and copy-error actions
 * - Is purely class-based (Error Boundaries must be class components)
 *
 * Design references: Vercel's 500 page, Linear's crash reporter.
 *
 * Usage (wrap root in index.jsx / main.jsx):
 *   <FatalErrorScreen>
 *     <App />
 *   </FatalErrorScreen>
 */
export class FatalErrorScreen extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, copied: false };
    this.handleCopy = this.handleCopy.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[FatalErrorScreen] Unhandled render error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  async handleCopy() {
    const { error, errorInfo } = this.state;
    const text = [
      `Cursus — Fatal Error Report`,
      `Time: ${new Date().toISOString()}`,
      `URL: ${window.location.href}`,
      ``,
      `Error: ${error?.message ?? String(error)}`,
      ``,
      `Stack:`,
      error?.stack ?? '(no stack)',
      ``,
      `Component Stack:`,
      errorInfo?.componentStack ?? '(none)',
    ].join('\n');

    try {
      await navigator.clipboard.writeText(text);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2500);
    } catch {
      // Fallback: open a text dialog or just log
      console.log('Error report:\n', text);
    }
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const { error, copied } = this.state;

    return (
      <div className="fatal-error-screen" role="main" aria-labelledby="fatal-err-heading">
        {/* Minimal Cursus brand mark — no animation */}
        <div className="fatal-error-screen__brand" aria-hidden="true">
          <LandingLogoMark size={28} strokeClassName="text-fg" dotClassName="fill-accent" />
          <span className="fatal-error-screen__brand-name">Cursus</span>
        </div>

        {/* Error icon — simple, no mascot to keep things stable */}
        <div className="fatal-error-screen__icon-wrap" aria-hidden="true">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="20" cy="20" r="19" stroke="var(--danger)" strokeWidth="1.5" strokeDasharray="4 3" />
            <path d="M20 12v10" stroke="var(--danger)" strokeWidth="2.5" strokeLinecap="round" />
            <circle cx="20" cy="27" r="1.5" fill="var(--danger)" />
          </svg>
        </div>

        <h1 id="fatal-err-heading" className="fatal-error-screen__heading">
          Cursus gặp lỗi nghiêm trọng
        </h1>
        <p className="fatal-error-screen__desc">
          Có sự cố không mong muốn xảy ra. Dữ liệu của bạn an toàn — làm mới trang thường giải quyết được vấn đề này.
        </p>

        {/* Error message summary (not full stack) */}
        {error?.message && (
          <div className="fatal-error-screen__error-pill" aria-label="Thông báo lỗi">
            <span className="mono">{error.message}</span>
          </div>
        )}

        {/* Actions */}
        <div className="fatal-error-screen__actions">
          <button
            type="button"
            className="btn btn-accent px-6 py-2.5"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={15} aria-hidden="true" />
            Làm mới trang
          </button>

          <button
            type="button"
            className="btn btn-outline px-5 py-2.5"
            onClick={this.handleCopy}
            aria-pressed={copied}
          >
            {copied
              ? <><CheckCheck size={14} aria-hidden="true" /> Đã sao chép</>
              : <><Copy size={14} aria-hidden="true" /> Sao chép báo lỗi</>
            }
          </button>
        </div>

        <p className="fatal-error-screen__footer">
          Nếu sự cố vẫn tiếp tục, vui lòng liên hệ{' '}
          <a href="mailto:support@cursus.edu.vn" className="fatal-error-screen__link">
            support@cursus.edu.vn
          </a>
        </p>
      </div>
    );
  }
}

export default FatalErrorScreen;
