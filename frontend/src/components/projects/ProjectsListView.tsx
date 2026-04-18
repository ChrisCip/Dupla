import { Link } from 'react-router-dom'

import { Card } from '../Card'
import { WORKFLOW_PHASE_LABELS } from '../../constants/workflowPhases'
import { formatProjectUpdatedAt } from '../../constants/projectsPage'
import { projectKindLabel } from '../../constants/projectKind'
import type { Project } from '../../types/project'

type ProjectsListViewProps = {
  loadingList: boolean
  projects: Project[]
  filteredProjects: Project[]
  projectSearch: string
  role: string | null
  onNavigateProject: (uuid: string) => void
}

export function ProjectsListView({
  loadingList,
  projects,
  filteredProjects,
  projectSearch,
  role,
  onNavigateProject,
}: ProjectsListViewProps) {
  return (
    <Card className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col overflow-hidden p-0">
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 z-10 bg-black/4 text-sm font-semibold uppercase tracking-wide text-ink backdrop-blur-sm md:text-base">
            <tr>
              <th className="px-3 py-3">Nombre</th>
              <th className="px-3 py-3">Cliente</th>
              <th className="hidden px-3 py-3 md:table-cell">Tipo</th>
              <th className="hidden px-3 py-3 sm:table-cell">Fase</th>
              <th className="whitespace-nowrap px-3 py-3">Modif.</th>
              <th className="px-3 py-3" />
            </tr>
          </thead>
          <tbody>
            {loadingList ? (
              <tr>
                <td className="border-l-4 border-l-primary bg-primary/[0.04] px-3 py-3 text-muted" colSpan={6}>
                  Cargando lista de proyectos…
                </td>
              </tr>
            ) : null}
            {!loadingList &&
              filteredProjects.map((p) => (
                <tr
                  key={p.uuid}
                  tabIndex={0}
                  className="cursor-pointer border-t border-black/5 transition-colors duration-150 hover:bg-black/[0.04] focus-visible:bg-black/[0.04] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary/40"
                  onClick={() => onNavigateProject(p.uuid)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onNavigateProject(p.uuid)
                    }
                  }}
                >
                  <td className="max-w-[10rem] truncate px-3 py-2 font-medium text-ink sm:max-w-none">
                    {p.name}
                  </td>
                  <td className="max-w-[7rem] truncate px-3 py-2 text-muted sm:max-w-[9rem]">
                    {p.client_name ?? '—'}
                  </td>
                  <td className="hidden px-3 py-2 text-muted md:table-cell">
                    {projectKindLabel(p.project_kind)}
                  </td>
                  <td className="hidden px-3 py-2 text-muted sm:table-cell">
                    <span className="inline-block max-w-[11rem] truncate rounded bg-black/[0.06] px-2 py-0.5 text-xs font-medium text-ink">
                      {WORKFLOW_PHASE_LABELS[p.workflow_phase] ?? p.workflow_phase}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm tabular-nums text-muted">
                    {formatProjectUpdatedAt(p.updated_at)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      className="du-link text-sm"
                      to={`/app/projects/${p.uuid}`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      Abrir →
                    </Link>
                  </td>
                </tr>
              ))}
            {!loadingList && projects.length === 0 ? (
              <tr>
                <td className="px-4 py-10" colSpan={6}>
                  <div className="mx-auto max-w-md rounded-lg border border-dashed border-black/15 bg-black/[0.02] px-6 py-8 text-center">
                    <p className="text-sm font-medium text-ink">Todavía no hay proyectos</p>
                    <p className="mt-2 text-sm text-muted">
                      {role === 'GERENCIA'
                        ? 'Usa «Nuevo proyecto» para crear el primero. También puedes verlos en el tablero por fase.'
                        : 'Cuando un administrador te dé acceso, el proyecto aparecerá aquí.'}
                    </p>
                  </div>
                </td>
              </tr>
            ) : null}
            {!loadingList && projects.length > 0 && filteredProjects.length === 0 ? (
              <tr>
                <td className="border-t border-black/5 px-4 py-8 text-sm text-muted" colSpan={6}>
                  Ningún proyecto coincide con «{projectSearch.trim()}». Prueba otro término o borra la búsqueda.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
