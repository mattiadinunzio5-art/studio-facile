import { Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ActivityPage } from './pages/Activity';
import { BibliographyPage } from './pages/Bibliography';
import { DocumentDetailPage, DocumentsPage } from './pages/Documents';
import { ResearchArchivePage } from './pages/ResearchArchive';
import { DashboardPage } from './pages/Dashboard';
import { ModulePage } from './pages/ModulePage';
import { EventDetailPage, EventsPage } from './pages/History';
import { TimeMachinePage } from './pages/TimeMachine';
import { GraphPage } from './pages/Graph';
import { BriefingPage, ReportEditorPage, StudioPage } from './pages/Studio';
import { LabPage, SimulationPage } from './pages/Lab';
import { RunDetailPage, WarRoomPage } from './pages/WarRoom';
import { ComparePage, FinancialPage, SeriesDetailPage } from './pages/Financial';
import { NotFoundPage } from './pages/NotFound';
import { NotificationsPage } from './pages/Notifications';
import { ProjectsPage } from './pages/Projects';
import { SearchPage } from './pages/Search';
import { SettingsPage } from './pages/Settings';
import { SourcesPage } from './pages/Sources';
import { AppStateProvider } from './state/AppState';
import { AuthProvider } from './state/Auth';
import { AccountPage, AdminPage } from './pages/Account';

export function App() {
  return (
    <AuthProvider>
    <AppStateProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="modules/:moduleId" element={<ModulePage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="sources" element={<SourcesPage />} />
          <Route path="activity" element={<ActivityPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/:documentId" element={<DocumentDetailPage />} />
          <Route path="bibliography" element={<BibliographyPage />} />
          <Route path="research" element={<ResearchArchivePage />} />
          <Route path="history" element={<EventsPage />} />
          <Route path="history/events/:eventId" element={<EventDetailPage />} />
          <Route path="time-machine" element={<TimeMachinePage />} />
          <Route path="graph" element={<GraphPage />} />
          <Route path="account" element={<AccountPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="studio" element={<StudioPage />} />
          <Route path="studio/reports/:reportId" element={<ReportEditorPage />} />
          <Route path="briefing" element={<BriefingPage />} />
          <Route path="lab" element={<LabPage />} />
          <Route path="lab/simulations/:simId" element={<SimulationPage />} />
          <Route path="war-room" element={<WarRoomPage />} />
          <Route path="war-room/runs/:runId" element={<RunDetailPage />} />
          <Route path="financial" element={<FinancialPage />} />
          <Route path="financial/series/:seriesId" element={<SeriesDetailPage />} />
          <Route path="financial/compare" element={<ComparePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AppStateProvider>
    </AuthProvider>
  );
}
