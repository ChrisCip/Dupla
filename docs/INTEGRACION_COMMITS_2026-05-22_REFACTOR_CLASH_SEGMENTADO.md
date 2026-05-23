# Changelog e integración — 22/23 mayo 2026

Documento para portar cambios al repositorio privado.  
**Origen:** `https://github.com/ChrisCip/Dupla`  
**Branch:** `refactor-clash-segmentado`  
**Autor principal:** enrik03  
**Rango:** 2026-05-22 → 2026-05-23 (hora local UTC-4)

---

## Resumen ejecutivo

En dos jornadas se cerró el ciclo **motor de clashes + app web + PDFs exportables**:

| Área | Qué se entrega |
|------|----------------|
| **Motor (`coordination/`)** | Roles de capa, tolerancias por proyecto, extracción Accore reforzada, fast_compare con telemetría, reporting MD por proyecto, MEP en pipeline |
| **Config** | YAML por proyecto (TORTUGA, SERENA, NASAS): `layer_rules`, `clash_role_matrix`, `tolerances` |
| **App web (`web-platform/`)** | Jobs de clash, pestaña Hallazgos, coordination-service Docker, PDF humano/técnico (ReportLab) |
| **Docs** | Instructivo reunión 22-05, reportes arquitecto consolidados |

**Commit punta de branch:** `493ed55` — incluye monorepo `web-platform/` completo.

---

## Cómo integrar en el repo privado

### Opción A — Merge de branch completa (recomendada si partís del mismo historial)

```bash
git remote add dupla-public https://github.com/ChrisCip/Dupla.git   # si no existe
git fetch dupla-public refactor-clash-segmentado
git checkout <tu-branch-privada>
git merge dupla-public/refactor-clash-segmentado
# resolver conflictos si los hay
```

### Opción B — Cherry-pick por bloques temáticos

Aplicar en orden cronológico (de más antiguo a más reciente):

```bash
git cherry-pick 719f6ee   # inspect script
git cherry-pick 018415a   # Serena artifacts (opcional, muchos MB)
git cherry-pick f688082   # layer roles + tolerances
git cherry-pick a307088   # extraction hardening
git cherry-pick 01ed097   # fast-compare diagnostics
git cherry-pick 22266b8   # TORTUGA config
git cherry-pick 799fd8a   # cohort bands
git cherry-pick b197441   # revision reports
git cherry-pick f789a99   # docs handoff
git cherry-pick 33d171d   # docs reunión (v1 extendida)
git cherry-pick 18b2ac5   # reader profiles MEP
git cherry-pick 0b6798e   # MEP pipeline + reportes MD
git cherry-pick 493ed55   # web-platform completo
```

### Opción C — Solo app web (sin motor Dupla)

Copiar carpeta `web-platform/` del commit `493ed55`. Requiere montar el motor Dupla en Docker (`DUPLA_ROOT=/dupla`).

### Dependencias post-merge

- **Docker:** `cd web-platform && docker compose up --build`
- **Migraciones:** Alembic `031_project_clash_jobs`, `032_clash_job_export_metadata`
- **Python (backend):** `reportlab==4.2.5` en `web-platform/backend/requirements.txt`
- **Smoke dev:** `COORDINATION_SMOKE_MODE=true` en docker-compose

---

## Commits del día (orden cronológico)

### 1. `719f6ee` — feat: add unfiltered layer clash inspection script

**Fecha:** 2026-05-22  
**Archivos:** `coordination/scripts/inspect_layer_clashes.py` (+545 líneas)

Utilidad para censar capas DWG y pares solapados sin límites de producción; exporta formatos para revisión manual e ingestión al clash-brain.

---

### 2. `018415a` — docs: add Serena 18 coordination analysis run artifacts

**Fecha:** 2026-05-22  
**Archivos:** ~60 bajo `analysis_output/serena18_analysis_08_runs/` (+6742 líneas)

Artefactos de corridas Serena 18 (readiness, coordinate audit, primary_incidents, reportes HTML/MD). **Nota:** commit pesado; omitir en cherry-pick si el repo privado no debe incluir outputs de análisis.

---

### 3. `f688082` — feat(coordination): add canonical layer roles and explicit tolerances

**Fecha:** 2026-05-22  
**Archivos clave:**

- `config/clash_role_matrix/{default,nasas09,serena18,tortuga_c40}.yaml`
- `config/layer_rules/{default,nasas09,serena18,tortuga_c40}.yaml`
- `config/tolerances/{default,nasas09,serena18,tortuga_c40}.yaml`
- `coordination/selection/layer_rules.py`
- `coordination/core/tolerances.py`

Comportamiento de clash configurable por proyecto en YAML en lugar de heurísticas hardcodeadas.

---

### 4. `a307088` — feat(extraction): harden accore flow and role-aware clash core

**Fecha:** 2026-05-22  
**Archivos clave:**

- `coordination/core/clash.py`
- `coordination/extraction/from_dwg_accore.py`, `from_dwg_ezdxf.py`, `odafc_bridge.py`
- `coordination/extraction/_geometry_builders.py`

Proveniencia de capas, tolerancias explícitas, extracción DWG/DXF más robusta.

---

### 5. `01ed097` — feat(fast-compare): add readiness diagnostics, telemetry, and regression tests

**Fecha:** 2026-05-22  
**Archivos clave:**

- `coordination/scripts/run_nasas09_project_coordination.py` (+280 líneas)
- `coordination/selection/coordinate_audit.py`
- `coordination/scripts/run_ifc_clash_crosscheck.py` (nuevo)
- Tests: `test_clash_tolerances.py`, `test_layer_rules.py`, `test_dxf_support.py`

Telemetría de pares excluidos, cobertura de roles, cross-check IFC opcional.

---

### 6. `22266b8` — config: expand TORTUGA C40 layer rules and role matrix

**Fecha:** 2026-05-22  
**Archivos:**

- `config/layer_rules/tortuga_c40.yaml`
- `config/clash_role_matrix/tortuga_c40.yaml`

Reglas SLAB/SLAM y pares estructurales para TORTUGA; suprime ruido de detalle.

---

### 7. `799fd8a` — feat(coordinate_audit): support trusted cohort band scheduling

**Fecha:** 2026-05-22  
**Archivos:** `coordination/selection/coordinate_audit.py`, runner

Permite cohortes curadas ARQ/EST con `trust_cohort_bands` sin bloqueo estricto de bandas de coordenadas.

---

### 8. `b197441` — feat(reporting): generate per-project and consolidated architect reports

**Fecha:** 2026-05-22  
**Archivos:**

- `coordination/reporting/revision_report.py` (nuevo, ~488 líneas)
- `coordination/scripts/run_nasas09_project_coordination.py`

Genera `REVISION_CLASHES_ARQUITECTO_{PROJECT}.md` por corrida + consolidado en raíz.

---

### 9. `f789a99` — docs: add clash integration instructive for 22-05-2026 handoff

**Fecha:** 2026-05-22  
**Archivos:**

- `docs/reunion_dupla_22-05-2026_CLASHES_INTEGRACION.md` (primera versión)
- `REVISION_CLASHES_ARQUITECTO_V2.md`

Instructivo de integración Fase 5 y checklist operativo.

---

### 10. `33d171d` — docs: update clash integration handoff for 22-05-2026 meeting

**Fecha:** 2026-05-23  
**Archivos:** `docs/reunion_dupla_22-05-2026_CLASHES_INTEGRACION.md`

Versión ampliada: arquitectura UI+PDF, demo TEST_01, criterios de aceptación, preguntas para reunión.

---

### 11. `18b2ac5` — feat(reporting): extend reader profiles and bot coverage helpers

**Fecha:** 2026-05-23  
**Archivos:**

- `coordination/reporting/reporting.py`
- `coordination/reporting/revision_report.py`
- `coordination/selection/fast_compare.py`
- Tests reporting

Perfil lector **Mecánico**, aliases de disciplina, cobertura en reportes humanos/técnicos.

---

### 12. `0b6798e` — Extend clash pipeline to all MEP disciplines and fix multi-discipline grouping

**Fecha:** 2026-05-23  
**Archivos:**

- `REVISION_CLASHES_ARQUITECTO.md` (consolidado, 679 líneas)
- `aps_integration/NASAS 09/.../REVISION_CLASHES_ARQUITECTO_NASAS_09.md`

Eléctrico, plomería y HVAC en fast_compare; clashes cuando **cualquier par** de disciplinas programadas se solapa (no exige las 5 en el mismo grupo de nivel).

---

### 13. `493ed55` — feat(web-platform): add clash jobs, PDF exports, and Hallazgos UI

**Fecha:** 2026-05-23  
**Alcance:** +482 archivos, ~179k líneas — **monorepo app web completo** bajo `web-platform/`

#### Backend (clashes + PDF)

| Ruta | Descripción |
|------|-------------|
| `web-platform/backend/app/routes/clash.py` | API jobs + export PDF |
| `web-platform/backend/app/services/clash_service.py` | Orquestación jobs, fingerprint CAD |
| `web-platform/backend/app/services/clash_export_service.py` | Generación PDF |
| `web-platform/backend/app/services/clash_reports/` | Módulo PDF ReportLab |
| `web-platform/backend/app/services/clash_reports/normalize.py` | Fallback capas/centro/Z W desde JSON+context+MD |
| `web-platform/backend/app/services/clash_reports/human_pdf.py` | PDF arquitecto |
| `web-platform/backend/app/services/clash_reports/technical_pdf.py` | PDF técnico (índice landscape, sin inventario) |
| `web-platform/backend/alembic/versions/031_*.py`, `032_*.py` | Tablas clash jobs + metadata export |
| `web-platform/backend/tests/test_clash_*.py` | 18 tests |

#### Coordination-service (Docker)

| Ruta | Descripción |
|------|-------------|
| `web-platform/coordination-service/wrapper/run_clash_analysis.py` | Wrapper Dupla |
| `web-platform/coordination-service/adapters/dupla_reports.py` | Artefactos MD/JSON |
| `web-platform/coordination-service/fixtures/smoke_primary_incidents.json` | Fixture smoke enriquecido |

#### Frontend

| Ruta | Descripción |
|------|-------------|
| `web-platform/frontend/src/components/project-workspace/tabs/WorkspaceHallazgosTab.tsx` | UI Hallazgos + botones PDF |
| `web-platform/frontend/src/hooks/useStructuralAnalysisJob.ts` | Poll job |
| `web-platform/frontend/src/api/structuralAnalysis.ts` | Cliente API |

#### Infra

- `web-platform/docker-compose.yml` — backend, frontend, postgres, redis, coordination-service, processor
- `web-platform/frontend/nginx.conf` — resolver Docker DNS (fix 502 tras rebuild)

---

## Mapa de carpetas tras integración

```
Dupla/                          # Motor coordinación (repo público/privado compartido)
├── coordination/               # Detección, reporting, scripts
├── config/                       # layer_rules, clash_role_matrix, tolerances
├── analysis_output/              # Outputs de corridas (opcional)
├── docs/
│   ├── reunion_dupla_22-05-2026_CLASHES_INTEGRACION.md
│   └── INTEGRACION_COMMITS_2026-05-22_REFACTOR_CLASH_SEGMENTADO.md  # este archivo
├── REVISION_CLASHES_ARQUITECTO.md
└── web-platform/                 # App Docker (nuevo en 493ed55)
    ├── backend/
    ├── frontend/
    ├── coordination-service/
    ├── processor/
    └── docker-compose.yml
```

---

## API y rutas nuevas (app web)

| Método | Ruta | Uso |
|--------|------|-----|
| POST | `/api/projects/{id}/folders/{folder_id}/clash/jobs` | Encolar análisis |
| GET | `/api/projects/{id}/clash/jobs/latest` | Último job |
| GET | `.../clash/jobs/latest/exports/human.pdf` | PDF revisión manual |
| GET | `.../clash/jobs/latest/exports/technical.pdf` | PDF auditoría técnica |

---

## Verificación post-integración

```bash
# Motor
cd coordination && python -m pytest tests/test_clash_tolerances.py tests/test_layer_rules.py -q

# App web (Docker)
cd web-platform
docker compose up --build -d backend
docker compose exec backend python -m pytest tests/test_clash_exports.py tests/test_clash_report_normalize.py -q
docker compose exec backend python scripts/generate_sample_clash_pdfs.py
```

**Demo manual:** proyecto Tutorial → carpeta TEST_01 → Hallazgos → Analizar → descargar PDFs.

---

## Notas para el equipo

1. **`web-platform/` es independiente del motor** pero monta `Dupla/` en `/dupla:ro` vía docker-compose (ruta Windows en el YAML; ajustar en Linux/CI).
2. **No commitear** `.env`, `node_modules`, `analysis_output` pesado ni credenciales APS.
3. Los PDFs usan **ReportLab**; el PDF técnico ya no incluye tabla “Inventario analizado”.
4. La normalización de incidencias prioriza: `source_refs` → `coordination_context.layer_pair` → `revision_md`.
5. Branch de referencia actualizada: `origin/refactor-clash-segmentado` @ `493ed55`.

---

## Referencia rápida de hashes

| Hash corto | Título |
|------------|--------|
| `719f6ee` | inspect_layer_clashes script |
| `018415a` | Serena 18 analysis artifacts |
| `f688082` | layer roles + tolerances YAML |
| `a307088` | Accore extraction hardening |
| `01ed097` | fast-compare diagnostics + tests |
| `22266b8` | TORTUGA C40 config |
| `799fd8a` | trusted cohort bands |
| `b197441` | revision_report.py |
| `f789a99` | docs handoff inicial |
| `33d171d` | docs reunión ampliado |
| `18b2ac5` | reader profiles MEP |
| `0b6798e` | MEP pipeline + MD consolidado |
| `493ed55` | **web-platform monorepo** |

---

*Generado para integración en repositorio privado — Dupla / refactor-clash-segmentado — mayo 2026.*
