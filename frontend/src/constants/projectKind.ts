export type ProjectKindValue = 'RESIDENTIAL' | 'TENDER'

export const PROJECT_KIND_OPTIONS: { value: ProjectKindValue; label: string; description: string }[] = [
  {
    value: 'RESIDENTIAL',
    label: 'Residencial',
    description: 'Flujo completo desde criterios de arranque.',
  },
  {
    value: 'TENDER',
    label: 'Licitación',
    description: 'Inicia en revisión de arquitectura; requiere subir uno o más archivos al crear.',
  },
]

export function projectKindLabel(kind: string | undefined): string {
  if (kind === 'TENDER') return 'Licitación'
  if (kind === 'RESIDENTIAL') return 'Residencial'
  return kind ?? '—'
}
