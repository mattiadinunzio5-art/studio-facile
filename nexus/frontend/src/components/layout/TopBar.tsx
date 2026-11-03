import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, Menu, PanelRight, Search } from 'lucide-react';
import { useAppState } from '../../state/AppState';

export function TopBar({ onMenu, onTogglePanel, panelOpen }: { onMenu: () => void; onTogglePanel: () => void; panelOpen: boolean }) {
  const navigate = useNavigate();
  const { backendOnline, unreadCount } = useAppState();
  const [q, setQ] = useState('');

  function submit(e: FormEvent) {
    e.preventDefault();
    const query = q.trim();
    if (query.length >= 2) navigate(`/search?q=${encodeURIComponent(query)}`);
  }

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b border-ink-700 bg-ink-950/95 px-3 backdrop-blur sm:gap-3 sm:px-4">
      <button className="rounded p-1.5 text-steel-300 hover:bg-ink-800 lg:hidden" onClick={onMenu} aria-label="Apri menu" aria-controls="nexus-sidebar">
        <Menu className="size-5" />
      </button>
      <form onSubmit={submit} role="search" className="min-w-0 flex-1">
        <label className="relative block max-w-xl">
          <span className="sr-only">Ricerca globale</span>
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-steel-500" aria-hidden />
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            minLength={2}
            maxLength={200}
            placeholder="Cerca progetti e moduli…"
            className="w-full rounded-md border border-ink-700 bg-ink-900 py-1.5 pl-8 pr-3 text-sm text-paper placeholder:text-steel-500 focus:border-gold-500 focus:outline-none"
          />
        </label>
      </form>
      <span
        className="hidden items-center gap-1.5 text-xs text-steel-400 sm:flex"
        title={backendOnline === false ? 'Il backend non risponde' : 'Backend collegato'}
      >
        <span className={`size-2 rounded-full ${backendOnline === undefined ? 'bg-steel-500' : backendOnline ? 'bg-ok' : 'bg-bad'}`} aria-hidden />
        {backendOnline === undefined ? 'Connessione…' : backendOnline ? 'Backend online' : 'Backend offline'}
      </span>
      <Link to="/notifications" className="relative rounded p-1.5 text-steel-300 hover:bg-ink-800" aria-label={`Notifiche (${unreadCount} non lette)`}>
        <Bell className="size-5" />
        {unreadCount > 0 && <span className="absolute right-1 top-1 size-2 rounded-full bg-gold-400" aria-hidden />}
      </Link>
      <button
        className={`rounded p-1.5 hover:bg-ink-800 ${panelOpen ? 'text-gold-400' : 'text-steel-300'}`}
        onClick={onTogglePanel}
        aria-label={panelOpen ? 'Chiudi pannello contestuale' : 'Apri pannello contestuale'}
        aria-pressed={panelOpen}
      >
        <PanelRight className="size-5" />
      </button>
    </header>
  );
}
