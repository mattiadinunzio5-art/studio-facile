import { ShieldAlert } from 'lucide-react';
import type { ClaimType, RetrievalHit, Support, VerificationStatus } from '../api/types';
import { Badge, type BadgeTone } from './ui/Badge';

export const SUPPORT: Record<Support, { label: string; tone: BadgeTone }> = {
  strong: { label: 'Supporto forte', tone: 'ok' },
  partial: { label: 'Supporto parziale', tone: 'gold' },
  weak: { label: 'Supporto debole', tone: 'warn' },
  none: { label: 'Nessun supporto', tone: 'bad' },
};

export const CLAIM: Record<ClaimType, { label: string; tone: BadgeTone }> = {
  documented_fact: { label: 'Fatto documentato', tone: 'ok' },
  interpretation: { label: 'Interpretazione', tone: 'gold' },
  hypothesis: { label: 'Ipotesi', tone: 'warn' },
  estimate: { label: 'Stima', tone: 'warn' },
  missing: { label: 'Dato mancante', tone: 'bad' },
};

export const VERIFICATION: Record<VerificationStatus, { label: string; tone: BadgeTone }> = {
  unverified: { label: 'Non verificata', tone: 'warn' },
  verified_user: { label: "Verificata dall'utente", tone: 'ok' },
  verified_registry: { label: 'Verificata su registro', tone: 'ok' },
  not_found: { label: 'Non trovata nel registro', tone: 'bad' },
};

export function InjectionWarning() {
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-warn" title="Il testo contiene frasi simili a istruzioni per un'AI. Viene trattato solo come dato.">
      <ShieldAlert className="size-3.5" aria-hidden /> Possibili istruzioni nel testo (trattate come dato)
    </span>
  );
}

export function PassageCard({ hit, index }: { hit: RetrievalHit; index?: number }) {
  return (
    <article className="rounded-lg border border-ink-700 bg-ink-900 p-3" data-testid="passage">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {index !== undefined && <span className="font-mono text-steel-500">[{index}]</span>}
        <span className="font-medium text-paper">{hit.document_title}</span>
        {hit.locator && <span className="text-steel-400">{hit.locator}</span>}
        <Badge tone={SUPPORT[hit.support].tone}>{SUPPORT[hit.support].label}</Badge>
        {hit.injection_flag && <InjectionWarning />}
      </div>
      <p className="mt-2 whitespace-pre-line text-sm text-steel-300">{hit.text}</p>
      <p className="mt-2 text-[11px] text-steel-500">Fonte: {hit.source_label}</p>
    </article>
  );
}
