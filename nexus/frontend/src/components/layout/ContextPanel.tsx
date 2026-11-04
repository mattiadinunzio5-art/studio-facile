import { X } from 'lucide-react';
import { useAppState } from '../../state/AppState';

export function ContextPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { panelContent } = useAppState();
  if (!open) return null;
  return (
    <>
      <div className="fixed inset-0 z-30 bg-black/50 xl:hidden" onClick={onClose} aria-hidden />
      <aside
        aria-label="Pannello contestuale"
        className="fixed inset-y-0 right-0 z-40 w-80 max-w-[90vw] overflow-y-auto border-l border-ink-700 bg-ink-900 xl:static xl:z-auto xl:max-w-none"
      >
        <div className="flex h-14 items-center justify-between border-b border-ink-700 px-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-steel-300">Contesto</h2>
          <button className="rounded p-1 text-steel-400 hover:text-paper" onClick={onClose} aria-label="Chiudi pannello contestuale">
            <X className="size-4" />
          </button>
        </div>
        <div className="space-y-5 p-4 text-sm">
          {panelContent ?? <p className="text-steel-400">Nessuna informazione contestuale per questa pagina.</p>}
        </div>
      </aside>
    </>
  );
}
