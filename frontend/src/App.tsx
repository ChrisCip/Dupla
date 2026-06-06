import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { MainLayout } from './components/MainLayout'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { ChatPage } from './pages/ChatPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { LoginPage } from './pages/LoginPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ProjectWorkspacePage } from './pages/ProjectWorkspacePage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { TaskboardPage } from './pages/TaskboardPage'
import { DashboardPage } from './pages/DashboardPage'
import { TutorialesPage } from './pages/TutorialesPage'
import { FlowsHubPage } from './pages/FlowsHubPage'
import { FlowBoardPage } from './pages/FlowBoardPage'
import { useAuthStore } from './store/authStore'

function RequireAuth() {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <Outlet />
}

function RequireGerencia() {
  const role = useAuthStore((s) => s.role)
  if (role !== 'GERENCIA') return <Navigate to="/app/projects" replace />
  return <Outlet />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/projects" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<MainLayout />}>
          <Route path="/app/projects" element={<ProjectsPage />} />
          <Route path="/app/projects/:projectUuid" element={<ProjectWorkspacePage />} />
          <Route path="/app/chat" element={<ChatPage />} />
          <Route path="/app/tasks" element={<TaskboardPage />} />
          <Route path="/app/tutoriales" element={<TutorialesPage />} />
          <Route element={<RequireGerencia />}>
            <Route path="/app/admin" element={<AdminUsersPage />} />
            <Route path="/app/dashboard" element={<DashboardPage />} />
            <Route path="/app/flows" element={<FlowsHubPage />} />
            <Route path="/app/flows/:flowUuid" element={<FlowBoardPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="/app" element={<Navigate to="/app/projects" replace />} />
      <Route path="*" element={<Navigate to="/app/projects" replace />} />
    </Routes>
  )
}
