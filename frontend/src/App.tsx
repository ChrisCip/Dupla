import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { useAuthStore } from './store/authStore'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { ProjectWorkspacePage } from './pages/ProjectWorkspacePage'

function RequireAuth() {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <Outlet />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/app" element={<DashboardPage />} />
        <Route path="/app/projects/:projectUuid" element={<ProjectWorkspacePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  )
}
