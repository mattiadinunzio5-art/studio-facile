import { Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ActivityPage } from './pages/Activity';
import { DashboardPage } from './pages/Dashboard';
import { ModulePage } from './pages/ModulePage';
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
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AppStateProvider>
  );
}
