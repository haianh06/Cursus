/** Canonical button — wraps the existing `.btn` + `.btn-primary/.btn-outline/
 * .btn-ghost` classes (index.css) plus a `danger` variant that used to be
 * hand-rolled inline per call site (see ConfirmDialog.jsx's old confirm
 * button). One call site instead of N pages each re-deriving the same
 * padding/radius/focus-ring combination, which is how radius/color drift
 * crept in across the app. No new CSS — same visual language as before.
 */
const VARIANT_CLASS = {
  primary: 'btn-accent',
  outline: 'btn-outline',
  ghost: 'btn-ghost',
  danger: 'text-danger border border-danger bg-danger-soft hover:opacity-90',
};

const SIZE_CLASS = {
  sm: 'text-xs px-3 min-h-8',
  md: 'text-[13px] px-4 min-h-10',
  lg: 'text-sm px-5 min-h-11',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  busy = false,
  disabled = false,
  className = '',
  children,
  ...rest
}) {
  return (
    <button
      type="button"
      disabled={disabled || busy}
      className={`btn ${VARIANT_CLASS[variant] ?? VARIANT_CLASS.primary} ${SIZE_CLASS[size] ?? SIZE_CLASS.md} cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
