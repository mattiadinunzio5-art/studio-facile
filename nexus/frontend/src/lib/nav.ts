import {
  Activity,
  Bell,
  BookMarked,
  FileText,
  MessageSquareQuote,
  BookOpenText,
  Briefcase,
  ChartLine,
  Database,
  FlaskConical,
  FolderKanban,
  History,
  Landmark,
  LayoutDashboard,
  Network,
  Settings,
  Swords,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  code?: string;
  phase?: number;
  moduleId?: string;
}

/**
 * Navigazione. I moduli condividono gli id con il registro del backend
 * (core/modules.py), che resta la fonte di verità per stato e contenuti.
 */
export const MODULE_NAV: NavItem[] = [
  { to: '/history', label: 'Historical Intelligence', icon: Landmark, code: 'A', moduleId: 'historical' },
  { to: '/financial', moduleId: 'financial', label: 'Financial Intelligence', icon: ChartLine, code: 'B' },
  { to: '/time-machine', label: 'Time Machine', icon: History, code: 'C', moduleId: 'time-machine' },
  { to: '/graph', label: 'Knowledge Graph', icon: Network, code: 'D', moduleId: 'knowledge-graph' },
  { to: '/war-room', moduleId: 'war-room', label: 'Research War Room', icon: Swords, code: 'E' },
  { to: '/lab', moduleId: 'economic-lab', label: 'Economic Laboratory', icon: FlaskConical, code: 'F' },
  { to: '/modules/research-studio', moduleId: 'research-studio', label: 'Research Studio', icon: BookOpenText, code: 'G', phase: 7 },
  { to: '/modules/business', moduleId: 'business', label: 'NEXUS Business', icon: Briefcase, code: 'H', phase: 8 },
];

export const MAIN_NAV: NavItem[] = [{ to: '/', label: 'Dashboard', icon: LayoutDashboard }];

export const ARCHIVE_NAV: NavItem[] = [
  { to: '/documents', label: 'Documenti', icon: FileText },
  { to: '/bibliography', label: 'Bibliografia', icon: BookMarked },
  { to: '/research', label: "Interroga l'archivio", icon: MessageSquareQuote },
];

export const WORKSPACE_NAV: NavItem[] = [
  { to: '/projects', label: 'Progetti', icon: FolderKanban },
  { to: '/sources', label: 'Fonti e connettori', icon: Database },
  { to: '/activity', label: 'Registro attività', icon: Activity },
  { to: '/notifications', label: 'Notifiche', icon: Bell },
  { to: '/settings', label: 'Sistema', icon: Settings },
];

/** Percorso della pagina di un modulo (pagina reale se implementato, altrimenti scheda «in preparazione»). */
export function moduleRoute(id: string): string {
  return MODULE_NAV.find((n) => n.moduleId === id)?.to ?? `/modules/${id}`;
}
