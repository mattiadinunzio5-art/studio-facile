import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '../api/client';

interface AppState {
  backendOnline: boolean | undefined;
  unreadCount: number;
  refreshUnread: () => Promise<void>;
  panelContent: ReactNode;
  setPanelContent: (node: ReactNode) => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [backendOnline, setBackendOnline] = useState<boolean>();
  const [unreadCount, setUnread] = useState(0);
  const [panelContent, setPanelContent] = useState<ReactNode>(null);

  const refreshUnread = useCallback(async () => {
    try {
      const items = await api.notifications(true);
      setUnread(items.length);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    void refreshUnread();
  }, [refreshUnread]);

  return (
    <Ctx.Provider value={{ backendOnline, unreadCount, refreshUnread, panelContent, setPanelContent }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useAppState deve essere usato dentro AppStateProvider');
  return ctx;
}

/** Imposta il contenuto del pannello contestuale per la pagina corrente. */
export function useContextPanel(node: ReactNode, deps: unknown[]) {
  const { setPanelContent } = useAppState();
  useEffect(() => {
    setPanelContent(node);
    return () => setPanelContent(null);
  }, deps);
}
