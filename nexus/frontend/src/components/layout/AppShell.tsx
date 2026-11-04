import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { ContextPanel } from './ContextPanel';

const PANEL_KEY = 'nexus.panelOpen';

function readPanelPref(): boolean {
  try {
    const v = localStorage.getItem(PANEL_KEY);
    if (v !== null) return v === '1';
  } catch {
    /* storage non disponibile */
  }
  return typeof window !== 'undefined' && window.matchMedia?.('(min-width: 1280px)').matches === true;
}

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(readPanelPref);
  const location = useLocation();

  useEffect(() => setMenuOpen(false), [location.pathname]);

  function togglePanel() {
    setPanelOpen((v) => {
      try {
        localStorage.setItem(PANEL_KEY, v ? '0' : '1');
      } catch {
        /* ignora */
      }
      return !v;
    });
  }

  return (
    <div className="flex h-full overflow-hidden">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setMenuOpen(true)} onTogglePanel={togglePanel} panelOpen={panelOpen} />
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
              <Outlet />
            </div>
          </main>
          <ContextPanel open={panelOpen} onClose={togglePanel} />
        </div>
      </div>
    </div>
  );
}
