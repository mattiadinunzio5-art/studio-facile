import type { ReactNode } from 'react';

const tones = {
  neutral: 'border-ink-600 text-steel-300',
  gold: 'border-gold-500/60 text-gold-300',
  ok: 'border-ok/50 text-ok',
  warn: 'border-warn/50 text-warn',
  bad: 'border-bad/50 text-bad',
} as const;

export type BadgeTone = keyof typeof tones;

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center whitespace-nowrap rounded border px-1.5 py-0.5 text-[11px] font-medium leading-none ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function DemoBadge() {
  return <Badge tone="warn">DEMO</Badge>;
}
