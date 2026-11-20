/* Progressive enhancement light-dismiss fallback for <dialog closedby="any"> */

export function attachDialogClosedByFallback(dialog: HTMLDialogElement): () => void {
  if ('closedBy' in HTMLDialogElement.prototype) {
    return () => {};
  }

  const outside = (e: PointerEvent) => {
    const r = dialog.getBoundingClientRect();
    return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
  };

  let pressedOutside = false;
  const onPointerDown = (e: PointerEvent) => {
    if (dialog.getAttribute('closedby') !== 'any') return;
    pressedOutside = outside(e);
  };
  const onPointerUp = (e: PointerEvent) => {
    if (dialog.getAttribute('closedby') !== 'any') return;
    if (pressedOutside && outside(e)) {
      dialog.close('dismiss');
    }
    pressedOutside = false;
  };

  dialog.addEventListener('pointerdown', onPointerDown);
  dialog.addEventListener('pointerup', onPointerUp);

  return () => {
    dialog.removeEventListener('pointerdown', onPointerDown);
    dialog.removeEventListener('pointerup', onPointerUp);
  };
}
