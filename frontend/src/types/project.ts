export type BootstrapCriterion = {
  id: string
  label: string
  required?: boolean
  done?: boolean
}

export type Project = {
  uuid: string
  name: string
  client_name: string | null
  status: string
  workflow_phase: string
  workflow_meta: Record<string, unknown>
  project_bootstrap_criteria: BootstrapCriterion[]
  specifications_document: Record<string, unknown>
}
