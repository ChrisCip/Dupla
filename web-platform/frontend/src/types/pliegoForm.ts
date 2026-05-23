export type PliegoItemEstado = 'PENDIENTE' | 'COMPLETO' | 'INCOMPLETO' | 'EN_REVISION' | 'NO_APLICA'

export type PliegoItemState = {
  estado: PliegoItemEstado
  notas?: string
  file_uuid?: string | null
  file_name?: string | null
}

export type PliegoGaFo01Persisted = {
  schema_version: 1
  item_states: Record<string, PliegoItemState>
  approved?: boolean
  approved_at?: string | null
  approved_by_user_uuid?: string | null
}
