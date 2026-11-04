import { createContext, useCallback, useContext, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { api } from '../api/client';
import type { User } from '../api/types';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Form';
import { errorText } from '../lib/forms';

interface AuthState { mode: 'local' | 'multi'; user: User | null; refresh: () => Promise<void>; logout: () => Promise<void> }
const Ctx = createContext<AuthState>({ mode: 'local', user: null, refresh: async () => {}, logout: async () => {} });
export const useAuth = () => useContext(Ctx);

function LoginScreen({ allowRegistration, onDone }: { allowRegistration: boolean; onDone: () => Promise<void> }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [f, setF] = useState({ email: '', password: '', name: '' });
  const [err, setErr] = useState<string>();
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(undefined);
    try {
      if (mode === 'login') await api.login(f.email, f.password);
      else await api.register(f.email, f.password, f.name);
      await onDone();
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-lg border border-ink-700 bg-ink-900 p-6">
        <div>
          <p className="text-lg font-semibold tracking-[0.3em] text-gold-400">NEXUS</p>
          <h1 className="mt-1 text-sm text-steel-300">{mode === 'login' ? 'Accedi al tuo account' : 'Crea un account'}</h1>
        </div>
        {mode === 'register' && <Field label="Nome"><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} autoComplete="name" /></Field>}
        <Field label="Email"><Input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} autoComplete="email" required /></Field>
        <Field label="Password" hint={mode === 'register' ? 'Almeno 10 caratteri, con lettere e numeri o simboli.' : undefined}>
          <Input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required />
        </Field>
        {err && <p role="alert" className="text-sm text-bad">{err}</p>}
        <Button type="submit" variant="primary" className="w-full" disabled={busy}>{mode === 'login' ? 'Accedi' : 'Registrati'}</Button>
        {allowRegistration && (
          <button type="button" className="w-full text-xs text-gold-300 hover:underline" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
            {mode === 'login' ? 'Non hai un account? Registrati' : 'Hai già un account? Accedi'}
          </button>
        )}
      </form>
    </div>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<{ mode: 'local' | 'multi'; allow_registration: boolean }>();
  const [user, setUser] = useState<User | null>(null);
  const [checked, setChecked] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setUser(await api.me());
    } catch {
      setUser(null);
    } finally {
      setChecked(true);
    }
  }, []);

  useEffect(() => {
    api.authConfig().then(setConfig).catch(() => setConfig({ mode: 'local', allow_registration: false }));
    void refresh();
    const onUnauthorized = () => setUser(null);
    window.addEventListener('nexus:unauthorized', onUnauthorized);
    return () => window.removeEventListener('nexus:unauthorized', onUnauthorized);
  }, [refresh]);

  const logout = useCallback(async () => {
    await api.logout().catch(() => undefined);
    setUser(null);
  }, []);

  const mode = config?.mode ?? 'local';
  if (mode === 'multi' && checked && !user) return <LoginScreen allowRegistration={config?.allow_registration ?? false} onDone={refresh} />;
  return <Ctx.Provider value={{ mode, user, refresh, logout }}>{children}</Ctx.Provider>;
}
