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
}

/**
 * Navigazione. I moduli condividono gli id con il registro del backend
 * (core/modules.py), che resta la fonte di verità per stato e contenuti.
 */
export const MODULE_NAV: NavItem[] = [
  { to: '/modules/historical', label: 'Historical Intelligence', icon: Landmark, code: 'A', phase: 3 },
  { to: '/modules/financial', label: 'Financial Intelligence', icon: ChartLine, code: 'B', phase: 4 },
  { to: '/modules/time-machine', label: 'Time Machine', icon: History, code: 'C', phase: 3 },
  { to: '/modules/knowledge-graph', label: 'Knowledge Graph', icon: Network, code: 'D', phase: 3 },
  { to: '/modules/war-room', label: 'Research War Room', icon: Swords, code: 'E', phase: 5 },
  { to: '/modules/economic-lab', label: 'Economic Laboratory', icon: FlaskConical, code: 'F', phase: 6 },
  { to: '/modules/research-studio', label: 'Research Studio', icon: BookOpenText, code: 'G', phase: 7 },
  { to: '/modules/business', label: 'NEXUS Business', icon: Briefcase, code: 'H', phase: 8 },
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
