const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function focusableElements(dialog) {
  if (!dialog?.querySelectorAll) return [];
  return Array.from(dialog.querySelectorAll(FOCUSABLE_SELECTOR)).filter((element) => (
    !element.disabled
    && !element.hidden
    && element.tabIndex !== -1
    && element.getAttribute?.('aria-hidden') !== 'true'
  ));
}

export function focusFirstInDialog(dialog) {
  const first = focusableElements(dialog)[0];
  if (!first) return false;
  first.focus();
  return true;
}

export function trapModalFocus(event, dialog, activeElement = document.activeElement) {
  if (event.key !== 'Tab') return false;
  const elements = focusableElements(dialog);
  if (!elements.length) {
    event.preventDefault();
    return true;
  }
  const first = elements[0];
  const last = elements[elements.length - 1];
  const outside = !dialog.contains(activeElement);
  if ((event.shiftKey && (activeElement === first || outside)) || (!event.shiftKey && activeElement === last)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
    return true;
  }
  return false;
}
