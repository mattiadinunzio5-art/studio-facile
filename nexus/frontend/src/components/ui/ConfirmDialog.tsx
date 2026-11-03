import { useEffect, useRef } from 'react';
import { Button } from './Button';

/** Conferma esplicita per operazioni irreversibili (policy di supervisione NEXUS). */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Conferma',
  onConfirm,
  onCancel,
  busy = false,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onKeyDown={(e) => e.key === 'Escape' && onCancel()}
    >
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md rounded-lg border border-ink-600 bg-ink-850 p-5">
        <h2 id="confirm-title" className="text-base font-semibold text-paper">{title}</h2>
        <p className="mt-2 text-sm text-steel-300">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button ref={cancelRef} onClick={onCancel} disabled={busy}>Annulla</Button>
          <Button variant="danger" onClick={onConfirm} disabled={busy}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}
