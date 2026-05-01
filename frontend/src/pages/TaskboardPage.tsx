import { useSearchParams } from 'react-router-dom'

import { TaskboardView } from '../components/TaskboardView'

export function TaskboardPage() {
  const [searchParams] = useSearchParams()
  const projectFilter = searchParams.get('project_uuid') ?? ''
  const mineRaw = searchParams.get('mine')
  const initialMineOnly = mineRaw === 'true' || mineRaw === '1'
  return (
    <TaskboardView projectUuid={projectFilter} initialMineOnly={initialMineOnly} variant="full" />
  )
}
