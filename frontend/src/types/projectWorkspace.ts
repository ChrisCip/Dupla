export type ProjectFileRow = {
  uuid: string
  original_name: string
  mime: string | null
  category: string | null
  folder_uuid: string | null
  description: string | null
  discipline: string | null
  ingest_status: string
  created_at: string
}

export type ProjectFileFolderRow = {
  uuid: string
  name: string
  parent_uuid: string | null
  created_at: string
}

export type RevisionRow = {
  uuid: string
  version: number
  decision: string
  notes: string | null
  created_at: string
}

export type SubcontractLine = {
  uuid: string
  item_label: string
  provider: string | null
  price: string
  currency: string
}

export type SubcontractQuoteRow = {
  uuid: string
  title: string | null
  created_at: string
  lines: SubcontractLine[]
}
