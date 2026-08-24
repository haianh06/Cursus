import React from 'react';
import CursusMascot from './CursusMascot';

/**
 * EmptyState — centered column, calm/static (no float loop) mascot,
 * heading + muted description + one optional primary action.
 * Per docs/frontend/03: never just blank space.
 */
export default function EmptyState({ title, description, actionLabel, onAction, icon }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 px-6 text-center">
      {icon || <CursusMascot size={40} animate={false} />}
      <div className="flex flex-col gap-1 max-w-sm">
        <h3 className="text-[16px] font-bold text-fg font-display">{title}</h3>
        {description && <p className="text-sm text-fg-muted leading-relaxed">{description}</p>}
      </div>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="btn btn-accent text-xs px-4 py-2 mt-1 cursor-pointer"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
