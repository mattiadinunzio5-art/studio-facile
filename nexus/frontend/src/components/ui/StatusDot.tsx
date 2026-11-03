import type { ConnectorStatus } from '../../api/types';

export const CONNECTOR_STATUS_LABEL: Record<ConnectorStatus, string> = {
  unknown: 'Mai verificata',
  reachable: 'Raggiungibile',
  degraded: 'Risponde con errore',
  unreachable: 'Non raggiungibile',
};

const color: Record<ConnectorStatus, string> = {
  unknown: 'bg-steel-500',
  reachable: 'bg-ok',
  degraded: 'bg-warn',
  unreachable: 'bg-bad',
};

export function StatusDot({ status }: { status: ConnectorStatus }) {
  return (
    <span
      className={`inline-block size-2 shrink-0 rounded-full ${color[status]}`}
      role="img"
      aria-label={CONNECTOR_STATUS_LABEL[status]}
    />
  );
}
