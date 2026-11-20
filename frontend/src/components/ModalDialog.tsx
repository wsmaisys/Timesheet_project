import React, { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';
import { attachDialogClosedByFallback } from '../lib/dialogFallback';

interface ModalDialogProps {
  open: boolean;
  title: string;
  closedBy?: 'any' | 'closerequest' | 'none';
  onClose: (returnValue?: string) => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const ModalDialog: React.FC<ModalDialogProps> = ({
  open,
  title,
  closedBy = 'closerequest',
  onClose,
  children,
  footer,
}) => {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const detachFallback = attachDialogClosedByFallback(dialog);
    const handleClose = () => {
      const rv = dialog.returnValue;
      dialog.returnValue = '';
      onCloseRef.current(rv);
    };

    dialog.addEventListener('close', handleClose);
    return () => {
      detachFallback();
      dialog.removeEventListener('close', handleClose);
    };
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="app-dialog"
      {...({ closedby: closedBy } as Record<string, string>)}
    >
      <div className="dialog-header">
        <h2 id={titleId} className="card-title">
          {title}
        </h2>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          aria-label={`Close ${title}`}
          onClick={() => dialogRef.current?.close('close-button')}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      <div className="dialog-body">{children}</div>
      {footer ? <div className="dialog-footer">{footer}</div> : null}
    </dialog>
  );
};
