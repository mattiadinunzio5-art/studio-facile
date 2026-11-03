import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { api } from '../api/client';
import type { CredentialInfo } from '../api/types';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Field, Input } from './ui/Form';
import { ErrorBox, Loading } from './ui/States';

const META: Record<string, { label: string; secret: boolean; url: boolean; model: boolean; note: string }> = {
  fred: { label: 'FRED (St. Louis Fed)', secret: true, url: false, model: false, note: 'Chiave gratuita su fred.stlouisfed.org → My Account → API Keys.' },
  ollama: { label: 'Ollama (modelli locali)', secret: false, url: true, model: true, note: 'Gratuito, gira sul tuo computer. URL predefinito http://127.0.0.1:11434.' },
  'openai-compatible': { label: 'Endpoint compatibile OpenAI', secret: true, url: true, model: true, note: "Qualsiasi servizio con API /chat/completions. I costi dipendono dal fornitore." },
  anthropic: { label: 'Anthropic API', secret: true, url: false, model: true, note: 'Servizio a pagamento: usato solo se configuri tu la chiave.' },
};

function Row({ c, onChange }: { c: CredentialInfo; onChange: () => void }) {
  const m = META[c.provider];
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ secret: '', base_url: c.config.base_url ?? '', model: c.config.model ?? '' });
  const [err, setErr] = useState<string>();
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center gap-2">
        <KeyRound className="size-4 text-steel-500" aria-hidden />
        <span className="flex-1 text-sm text-paper">{m.label}</span>
        <Badge tone={c.configured ? 'ok' : 'neutral'}>{c.configured ? `Configurata ${c.hint}` : 'Non configurata'}</Badge>
        <Button variant="ghost" className="text-xs" onClick={() => setOpen((o) => !o)}>{open ? 'Chiudi' : c.configured ? 'Modifica' : 'Configura'}</Button>
        {c.configured && <Button variant="ghost" className="text-xs hover:text-bad" onClick={async () => { await api.deleteCredential(c.provider); onChange(); }}>Rimuovi</Button>}
      </div>
      <p className="mt-1 text-[11px] text-steel-500">{m.note}{c.config.model && ` Modello: ${c.config.model}.`}</p>
      {open && (
        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {m.secret && <Field label="Chiave API"><Input type="password" autoComplete="off" value={f.secret} onChange={(e) => setF({ ...f, secret: e.target.value })} /></Field>}
          {m.url && <Field label="URL base"><Input value={f.base_url} onChange={(e) => setF({ ...f, base_url: e.target.value })} placeholder={c.provider === 'ollama' ? 'http://127.0.0.1:11434' : 'https://…/v1'} /></Field>}
          {m.model && <Field label="Modello"><Input value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })} /></Field>}
          {err && <p role="alert" className="text-sm text-bad sm:col-span-3">{err}</p>}
          <div className="sm:col-span-3">
            <Button variant="primary" onClick={async () => {
              setErr(undefined);
              try { await api.setCredential({ provider: c.provider, ...f }); setOpen(false); setF({ ...f, secret: '' }); onChange(); } catch (e) { setErr(errorText(e)); }
            }}>Salva</Button>
          </div>
        </div>
      )}
    </li>
  );
}

export function CredentialsPanel() {
  const creds = useAsync(() => api.credentials(), []);
  if (creds.loading && !creds.data) return <Loading />;
  if (creds.error) return <ErrorBox error={creds.error} onRetry={creds.reload} />;
  return (
    <>
      <p className="text-xs text-steel-500">Le chiavi sono cifrate nel database locale e non vengono mai mostrate di nuovo. Tutti i servizi sono facoltativi.</p>
      <ul className="divide-y divide-ink-700">{creds.data?.map((c) => <Row key={c.provider} c={c} onChange={creds.reload} />)}</ul>
    </>
  );
}
