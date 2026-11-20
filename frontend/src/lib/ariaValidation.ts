/* Synchronizes programmatic ARIA error states (aria-invalid, aria-describedby, live region)
   with CSS :user-invalid so screen readers only hear errors after interaction. */

let initialized = false;
let announcer: HTMLDivElement | null = null;
let announceTimer: ReturnType<typeof setTimeout> | undefined;
let announcedField: Element | null = null;
const flagged = new WeakSet<Element>();
const announced = new WeakSet<Element>();
const dirtyState = new WeakMap<Element, { hasInteracted: boolean; hasBlurred: boolean }>();

function getOrCreateAnnouncer(): HTMLDivElement {
  if (announcer && document.body.contains(announcer)) {
    return announcer;
  }
  const el = document.createElement('div');
  el.setAttribute('aria-live', 'polite');
  el.classList.add('visually-hidden');
  document.body.append(el);
  announcer = el;
  return el;
}

function linkError(el: HTMLElement, shown: boolean): void {
  const errorId = el.dataset.error;
  if (!errorId) return;
  const ids = (el.getAttribute('aria-describedby') || '')
    .split(/\s+/)
    .filter((id) => id && id !== errorId);
  if (shown) ids.push(errorId);
  if (ids.length) {
    el.setAttribute('aria-describedby', ids.join(' '));
  } else {
    el.removeAttribute('aria-describedby');
  }
}

function spokenText(node: HTMLElement): string {
  const copy = node.cloneNode(true) as HTMLElement;
  copy.querySelectorAll('[aria-hidden="true"]').forEach((n) => n.remove());
  copy.querySelectorAll('[role="img"][aria-label]').forEach((n) => {
    n.replaceWith(`${n.getAttribute('aria-label')}: `);
  });
  return (copy.textContent || '').replace(/\s+/g, ' ').trim();
}

function announceError(el: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement): void {
  const errorId = el.dataset.error;
  if (!errorId) return;
  const errorEl = document.getElementById(errorId);
  if (!errorEl) return;
  const label = el.labels?.[0] ? `${spokenText(el.labels[0])}: ` : '';
  const live = getOrCreateAnnouncer();
  clearTimeout(announceTimer);
  live.textContent = '';
  announcedField = el;
  announceTimer = setTimeout(() => {
    live.textContent = label + spokenText(errorEl);
  }, 500);
}

export function syncControlAria(target: EventTarget | null, announce = false): void {
  if (!(target instanceof HTMLElement)) return;
  if (!target.matches('input, select, textarea')) return;
  const el = target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

  const supportsUserInvalid = typeof CSS !== 'undefined' && CSS.supports?.('selector(:user-invalid)');
  let isInvalid = false;

  if (supportsUserInvalid) {
    isInvalid = el.matches(':user-invalid');
  } else {
    const state = dirtyState.get(el);
    isInvalid = Boolean(state?.hasBlurred && !el.validity.valid);
    el.classList.toggle('user-invalid-fallback', isInvalid);
    el.classList.toggle('user-valid-fallback', Boolean(state?.hasBlurred && el.validity.valid));
  }

  if (isInvalid) {
    if (announce && !announced.has(el)) {
      announceError(el);
      announced.add(el);
    }
    el.setAttribute('aria-invalid', 'true');
    linkError(el, true);
    flagged.add(el);
  } else if (flagged.has(el) || el.getAttribute('aria-invalid') !== 'true') {
    el.setAttribute('aria-invalid', 'false');
    linkError(el, false);
    flagged.delete(el);
    announced.delete(el);
    if (announcedField === el && announcer) {
      clearTimeout(announceTimer);
      announcer.textContent = '';
    }
  }
}

export function initGlobalAriaValidation(): void {
  if (initialized || typeof document === 'undefined') return;
  initialized = true;
  getOrCreateAnnouncer();

  document.addEventListener(
    'blur',
    (e) => {
      if (e.target instanceof HTMLElement && e.target.matches('input, select, textarea')) {
        const state = dirtyState.get(e.target) || { hasInteracted: false, hasBlurred: false };
        state.hasBlurred = true;
        dirtyState.set(e.target, state);
      }
      syncControlAria(e.target, true);
    },
    true,
  );

  document.addEventListener('input', (e) => {
    if (e.target instanceof HTMLElement && e.target.matches('input, select, textarea')) {
      const state = dirtyState.get(e.target) || { hasInteracted: false, hasBlurred: false };
      state.hasInteracted = true;
      dirtyState.set(e.target, state);
      if (e.target.hasAttribute('aria-invalid')) {
        syncControlAria(e.target, false);
      }
    }
  });

  document.addEventListener(
    'change',
    (e) => {
      if (e.target instanceof HTMLElement && e.target.matches('input, select, textarea')) {
        const state = dirtyState.get(e.target) || { hasInteracted: false, hasBlurred: false };
        state.hasInteracted = true;
        state.hasBlurred = true;
        dirtyState.set(e.target, state);
      }
      syncControlAria(e.target, true);
    },
    true,
  );

  document.addEventListener(
    'invalid',
    (e) => {
      if (e.target instanceof HTMLElement) {
        dirtyState.set(e.target, { hasInteracted: true, hasBlurred: true });
        announced.add(e.target);
        syncControlAria(e.target, false);
      }
    },
    true,
  );

  document.addEventListener(
    'reset',
    (e) => {
      const form = e.target;
      if (form instanceof HTMLFormElement) {
        setTimeout(() => {
          Array.from(form.elements).forEach((el) => {
            dirtyState.delete(el);
            el.classList.remove('user-invalid-fallback', 'user-valid-fallback');
            syncControlAria(el, false);
          });
        });
      }
    },
    true,
  );
}
