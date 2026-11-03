export const toInt = (v: string): number | null => (v.trim() === '' || Number.isNaN(Number(v)) ? null : Math.trunc(Number(v)));
export const toList = (v: string): string[] => v.split(/[,;\n]/).map((x) => x.trim()).filter(Boolean);
export const fromList = (v: string[] | undefined): string => (v ?? []).join(', ');

/** Estrae un messaggio leggibile da un ApiError con dettagli di validazione. */
export function errorText(err: unknown): string {
  const e = err as { message?: string; details?: unknown };
  const details = Array.isArray(e.details) ? (e.details as { msg?: string }[]).map((d) => d.msg).filter(Boolean).join('; ') : '';
  return [e.message ?? String(err), details].filter(Boolean).join(' ');
}
