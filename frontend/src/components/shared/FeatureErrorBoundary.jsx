import React from 'react';
import { AlertTriangle, RotateCcw, RefreshCw } from 'lucide-react';
import CursusMascot from './CursusMascot';

/**
 * FeatureErrorBoundary — React Error Boundary for scoped widget failures.
 *
 * Wraps individual dashboard sections/cards so one broken component does
 * not crash the entire app. Renders an inline error card with:
 * - Cursus Assistant in `warning` state
 * - Plain-language error message (never a raw stack trace as primary copy)
 * - Retry (remount the subtree) and Reload Page options
 *
 * Design references: shadcn/ui ErrorBoundary, Linear's widget error pattern.
 *
 * Usage:
 *   <FeatureErrorBoundary featureName="Kế hoạch hôm nay">
 *     <TodayPlanCard />
 *   </FeatureErrorBoundary>
 */
export class FeatureErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, resetKey: 0 };
    this.handleRetry = this.handleRetry.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log for Sentry/PostHog when integrated
    console.error(
      `[FeatureErrorBoundary] "${this.props.featureName ?? 'Component'}" threw:`,
      error,
      errorInfo,
    );
    this.setState({ errorInfo });
  }

  handleRetry() {
    this.setState((s) => ({
      hasError: false,
      error: null,
      errorInfo: null,
      resetKey: s.resetKey + 1,
    }));
  }

  render() {
    if (this.state.hasError) {
      return (
        <FeatureErrorCard
          featureName={this.props.featureName}
          error={this.state.error}
          onRetry={this.handleRetry}
          compact={this.props.compact}
        />
      );
    }

    return (
      <React.Fragment key={this.state.resetKey}>
        {this.props.children}
      </React.Fragment>
    );
  }
}

/**
 * FeatureErrorCard — the inline UI rendered when a feature crashes.
 * Can also be used standalone (e.g. API call failed for a specific section).
 */
export function FeatureErrorCard({ featureName, error, onRetry, compact = false }) {
  const [showDetail, setShowDetail] = React.useState(false);

  if (compact) {
    return (
      <div className="feature-error-card feature-error-card--compact" role="alert">
        <AlertTriangle size={14} className="feature-error-card__icon" aria-hidden="true" />
        <span className="feature-error-card__compact-text">
          {featureName ? `${featureName} gặp sự cố` : 'Tính năng này gặp sự cố'}
        </span>
        {onRetry && (
          <button
            type="button"
            className="feature-error-card__retry-sm"
            onClick={onRetry}
          >
            <RotateCcw size={12} aria-hidden="true" />
            Thử lại
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="feature-error-card" role="alert" aria-labelledby="feat-err-heading">
      {/* Mascot — small, warning state */}
      <div className="feature-error-card__mascot-wrap" aria-hidden="true">
        <CursusMascot size={64} state="warning" />
      </div>

      <div className="feature-error-card__body">
        <h3 id="feat-err-heading" className="feature-error-card__heading">
          {featureName ? `${featureName} gặp sự cố` : 'Tính năng này gặp sự cố'}
        </h3>
        <p className="feature-error-card__desc">
          Đã có lỗi xảy ra trong khu vực này. Thử tải lại tính năng hoặc làm mới trang nếu sự cố tiếp tục.
        </p>

        <div className="feature-error-card__actions">
          {onRetry && (
            <button
              type="button"
              className="btn btn-outline text-xs px-4 py-2 cursor-pointer flex items-center gap-1.5"
              onClick={onRetry}
            >
              <RotateCcw size={13} aria-hidden="true" />
              Tải lại tính năng
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost text-xs px-4 py-2 cursor-pointer flex items-center gap-1.5 text-fg-muted"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={13} aria-hidden="true" />
            Làm mới trang
          </button>
        </div>

        {/* Collapsed technical detail */}
        {error && (
          <div className="feature-error-card__detail">
            <button
              type="button"
              className="feature-error-card__detail-toggle"
              onClick={() => setShowDetail((v) => !v)}
              aria-expanded={showDetail}
            >
              {showDetail ? '▾' : '▸'} Chi tiết kỹ thuật
            </button>
            {showDetail && (
              <pre className="feature-error-card__detail-body animate-fade-up">
                {error?.message ?? String(error)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default FeatureErrorBoundary;
