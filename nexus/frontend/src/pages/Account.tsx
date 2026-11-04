import { useState } from 'react';
import { api } from '../api/client';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Field, Input, Select } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useAuth } from '../state/Auth';

const LIMIT_LABEL: Record<string, [string, string]> = {
  projects: ['Progetti', 'max_projects'], documents: ['Documenti', 'max_documents'], storage_mb: ['Spazio (MB)', 'max_storage_mb'],
  series: ['Serie', 'max_series'], ai_runs_today: ['Ricerche AI (24 ore)', 'ai_runs_per_day'],
};

export function AccountPage() {
  const { user, mode, refresh, logout } = useAuth();
  const usage = useAsync(() => api.usage(), []);
  const plans = useAsync(() => api.plans(), []);
  const sessions = useAsync(() => (mode === 'multi' ? api.sessions() : Promise.resolve([])), [mode]);
  const [name, setName] = useState(user?.display_name ?? '');
  const [pw, setPw] = useState({ current: '', next: '' });
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const act = async (fn: () => Promise<unknown>, ok: string) => { setMsg(undefined); try { await fn(); setMsg({ ok: true, text: ok }); } catch (e) { setMsg({ ok: false, text: errorText(e) }); } };

  return (
    <>
      <PageHeader eyebrow="Modulo H" title="Account" description={mode === 'local' ? 'Modalità locale personale: utente unico sul tuo computer, nessun limite.' : 'Profilo, sicurezza, piano e utilizzo.'}
        actions={mode === 'multi' && <Button onClick={logout}>Esci</Button>} />
      {msg && <p role={msg.ok ? 'status' : 'alert'} className={`mb-3 text-sm ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Profilo">
          <p className="mb-3 text-sm text-steel-300">{user?.email} · <Badge>{user?.role}</Badge> <Badge tone="gold">{user?.plan}</Badge></p>
          <div className="flex items-end gap-2">
            <Field label="Nome visualizzato" className="flex-1"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
            <Button disabled={!name.trim()} onClick={() => act(async () => { await api.updateProfile(name.trim()); await refresh(); }, 'Profilo aggiornato.')}>Salva</Button>
          </div>
        </Card>
        <Card title="Piano e utilizzo">
          {usage.loading && <Loading />}
          {usage.error && <ErrorBox error={usage.error} />}
          {usage.data && (
            <>
              <p className="mb-2 text-sm text-paper">{usage.data.plan.name} <span className="text-xs text-steel-500">· {usage.data.plan.price_note}</span></p>
              <ul className="space-y-1 text-sm">
                {Object.entries(LIMIT_LABEL).map(([k, [label, lk]]) => {
                  const limit = usage.data!.plan[lk as keyof typeof usage.data.plan] as number | null;
                  return <li key={k} className="flex justify-between gap-2 text-steel-300"><span>{label}</span><span className="text-paper">{usage.data!.usage[k]} / {limit ?? 'illimitato'}</span></li>;
                })}
              </ul>
            </>
          )}
          {plans.data && <p className="mt-3 text-xs text-steel-500">{plans.data.note}</p>}
        </Card>
        {mode === 'multi' && (
          <>
            <Card title="Cambia password">
              <div className="space-y-2">
                <Field label="Password attuale"><Input type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} /></Field>
                <Field label="Nuova password" hint="Le altre sessioni verranno chiuse."><Input type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} /></Field>
                <Button onClick={() => act(async () => { await api.changePassword(pw.current, pw.next); setPw({ current: '', next: '' }); await sessions.reload(); }, 'Password modificata.')}>Aggiorna password</Button>
              </div>
            </Card>
            <Card title="Sessioni attive">
              <ul className="divide-y divide-ink-700 text-sm">
                {sessions.data?.map((s) => (
                  <li key={s.id} className="flex flex-wrap items-center gap-2 py-2">
                    <span className="min-w-0 flex-1 truncate text-steel-300">{s.user_agent || 'Dispositivo sconosciuto'} · {s.ip}</span>
                    <span className="text-[11px] text-steel-500">{formatDateTime(s.last_seen_at ?? s.created_at)}</span>
                    {s.current ? <Badge tone="ok">Questa sessione</Badge> : <Button variant="ghost" className="text-xs" onClick={() => act(async () => { await api.revokeSession(s.id); await sessions.reload(); }, 'Sessione chiusa.')}>Chiudi</Button>}
                  </li>
                ))}
              </ul>
            </Card>
          </>
        )}
      </div>
    </>
  );
}

export function AdminPage() {
  const users = useAsync(() => api.adminUsers(), []);
  const stats = useAsync(() => api.adminStats(), []);
  const [err, setErr] = useState<string>();
  const update = async (id: number, data: Record<string, unknown>) => { setErr(undefined); try { await api.adminUpdateUser(id, data); await users.reload(); } catch (e) { setErr(errorText(e)); } };
  return (
    <>
      <PageHeader eyebrow="Modulo H" title="Amministrazione" description="Utenti, ruoli, piani e stato degli account. Nessun pagamento reale: i piani si assegnano qui." />
      {stats.data && <p className="mb-4 text-sm text-steel-300">{Object.entries(stats.data).filter(([, v]) => typeof v === 'number').map(([k, v]) => `${k}: ${v}`).join(' · ')}</p>}
      {err && <div className="mb-3"><ErrorBox error={new Error(err)} /></div>}
      {users.loading && !users.data && <Loading />}
      {users.error && <ErrorBox error={users.error} />}
      {users.data && (
        <div className="overflow-x-auto rounded-lg border border-ink-700">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-ink-900 text-[11px] uppercase tracking-wider text-steel-500"><tr><th className="px-3 py-2">Utente</th><th className="px-3 py-2">Ruolo</th><th className="px-3 py-2">Piano</th><th className="px-3 py-2">Utilizzo</th><th className="px-3 py-2">Stato</th></tr></thead>
            <tbody className="divide-y divide-ink-700">
              {users.data.map((u) => (
                <tr key={u.id}>
                  <td className="px-3 py-2"><span className="text-paper">{u.display_name}</span><span className="block text-xs text-steel-500">{u.email} · ultimo accesso {formatDateTime(u.last_login_at)}</span></td>
                  <td className="px-3 py-2">{u.is_local ? u.role : <Select aria-label={`Ruolo di ${u.email}`} className="w-auto py-1" value={u.role} onChange={(e) => update(u.id, { role: e.target.value })}><option value="user">user</option><option value="admin">admin</option></Select>}</td>
                  <td className="px-3 py-2">{u.is_local ? u.plan : <Select aria-label={`Piano di ${u.email}`} className="w-auto py-1" value={u.plan} onChange={(e) => update(u.id, { plan: e.target.value })}><option value="free">free</option><option value="premium">premium</option></Select>}</td>
                  <td className="px-3 py-2 text-xs text-steel-400">{u.usage.projects} progetti · {u.usage.documents} documenti · {u.usage.storage_mb} MB</td>
                  <td className="px-3 py-2">{u.is_local ? <Badge>locale</Badge> : <Button variant="ghost" className="text-xs" onClick={() => update(u.id, { is_active: !u.is_active })}>{u.is_active ? 'Disattiva' : 'Riattiva'}</Button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
