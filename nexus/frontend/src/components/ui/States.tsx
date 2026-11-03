import { CircleAlert, Hourglass, LoaderCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import type { ApiError } from '../../api/client';

export function Loading({ label = 'Caricamento…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-6 text-sm text-steel-400">
      <LoaderCircle className="size-4 animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: ApiError | Error; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-md border border-bad/40 bg-bad/5 p-3 text-sm">
      <CircleAlert className="mt-0.5 size-4 shrink-0 text-bad" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-paper">{error.message}</p>
        {onRetry && (
          <button onClick={onRetry} className="mt-2 text-xs font-medium text-gold-300 hover:underline">
            Riprova
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="py-3 text-sm text-steel-400">{children}</p>;
}

/** Sezione senza dati reali: lo dichiara, con il motivo e la fase prevista. */
export function NotAvailable({ reason, phase }: { reason: string; phase: number }) {
  return (
    <div className="flex items-start gap-3 text-sm" data-testid="not-available">
      <Hourglass className="mt-0.5 size-4 shrink-0 text-gold-400" aria-hidden />
      <div>
        <p className="font-medium text-paper">Non disponibile — previsto in Fase {phase}</p>
        <p className="mt-1 text-steel-400">{reason}</p>
      </div>
    </div>
  );
}
