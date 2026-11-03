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
import { RunDetailPage, WarRoomPage } from './pages/WarRoom';
import { ComparePage, FinancialPage, SeriesDetailPage } from './pages/Financial';
import { NotFoundPage } from './pages/NotFound';
import { NotificationsPage } from './pages/Notifications';
import { ProjectsPage } from './pages/Projects';
import { SearchPage } from './pages/Search';
import { SettingsPage } from './pages/Settings';
import { SourcesPage } from './pages/Sources';
import { AppStateProvider } from './state/AppState';

export function App() {
  return (
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
          <Route path="war-room" element={<WarRoomPage />} />
          <Route path="war-room/runs/:runId" element={<RunDetailPage />} />
          <Route path="financial" element={<FinancialPage />} />
          <Route path="financial/series/:seriesId" element={<SeriesDetailPage />} />
          <Route path="financial/compare" element={<ComparePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AppStateProvider>
  );
}
