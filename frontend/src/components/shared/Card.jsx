/** Canonical card container — wraps the existing `.card` class (index.css:
 * bg-surface-card, border-line, --radius-md corners, hover elevation) that
 * many pages already re-derive by hand as
 * `rounded-2xl border border-line bg-surface-card p-4` (a raw `rounded-2xl`
 * resolves to Tailwind's own radius scale, not this app's --radius-md
 * token — see Modal.jsx's docstring for the same drift). One call site
 * instead of N slightly-different hand-rolled containers.
 */
export default function Card({ className = '', padding = 'p-4', children, ...rest }) {
  return (
    <div className={`card ${padding} ${className}`} {...rest}>
      {children}
    </div>
  );
}
