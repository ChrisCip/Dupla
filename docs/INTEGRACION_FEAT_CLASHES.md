# Integración de detección de clashes — `feat/clashes-integration`

> Documento para que cualquier colaborador del equipo pueda **bajar la branch, levantar el stack local y validar la pestaña Hallazgos** sin pasos extra. Pensado para correr desde Windows con Docker Desktop, pero las rutas se generalizan vía variable de entorno.

- **Branch:** `feat/clashes-integration`  
- **Base:** `feat/budget-analysis-pricing`  
- **Commits incluidos:** `bb44fb2` + `a1ba8bc`  
- **Repo:** `ChrisCip/DuplaPricingAnalysis`

---

## 1. Resumen ejecutivo

Esta branch añade el **pipeline de detección de clashes** encima del trabajo de presupuesto/pricing existente:

| Capa | Qué se entrega |
|------|----------------|
| **Motor (externo)** | Reutiliza el repo `Dupla` (motor de coordinación) montado en sólo lectura dentro de Docker |
| **Backend FastAPI** | Modelo `ProjectClashJob`, migraciones 031/032, rutas REST `POST/GET /api/projects/{id}/clash/jobs/*`, generación PDF humano y técnico (ReportLab) |
| **Microservicio nuevo** | `coordination-service` (HTTP API) + `coordination-worker` (RQ worker), ambos envuelven el motor Dupla |
| **Frontend React** | Pestaña **Hallazgos** real (no mock): polling cada 5 s, selector de carpeta fuente, inventario CAD, descarga de PDF humano y técnico |
| **Infra** | Dos contenedores nuevos en `docker-compose.yml`, resolver DNS Docker en nginx, restart policy para los workers |

---

## 2. Cómo bajar la branch

```bash
git fetch origin
git checkout feat/clashes-integration
git pull
```

Si tu rama local diverge, hacé `git status` y revisalo antes de tocar nada.

---

## 3. Requisitos previos

| Requisito | Por qué |
|-----------|---------|
| **Docker Desktop** | Levanta todo el stack |
| **Repo `Dupla` clonado localmente** | El microservicio lo monta como `/dupla:ro`. Sin él, los jobs fallan |
| **Archivo `backend/.env`** | Está en `.gitignore`, no se commitea. Contiene credenciales |

### 3.1 Clonar el motor Dupla (sólo una vez)

Por defecto el `docker-compose.yml` busca el repo Dupla en `../Dupla` (un nivel arriba de este repo). La forma más simple:

```bash
# Desde el directorio padre de DuplaPricingAnalysis
git clone https://github.com/ChrisCip/Dupla.git Dupla
git -C Dupla checkout refactor-clash-segmentado
```

Si lo querés en otra ubicación, exportá la variable antes del `docker compose`:

```powershell
# Windows PowerShell
$env:DUPLA_PATH = "C:/ruta/absoluta/a/Dupla"
```

```bash
# bash / zsh
export DUPLA_PATH=/ruta/absoluta/a/Dupla
```

### 3.2 Crear `backend/.env`

Crear el archivo `backend/.env` con las credenciales (pedírselas a quien corresponda — no las pegamos acá):

```dotenv
OPENAI_API_KEY=<sk-proj-...>
CLIENT_ID=<APS client id>
CLIENT_SECRET=<APS client secret>
APS_BUCKET_NAME=dupla_bucket_chris_v2
```

> Si te falta este archivo, `docker compose up` aborta con:
> `env file ... \backend\.env not found`.

---

## 4. Levantar el stack

```bash
docker compose up -d --build
```

Servicios que arrancan (verificá con `docker compose ps`):

| Servicio | Puerto host | Rol |
|----------|------------|-----|
| `postgres` | 5432 | DB principal |
| `redis` | 6379 | Cola RQ y caché |
| `backend` | 8000 | FastAPI + entrypoint que hace `alembic upgrade head` + `seed` + uvicorn |
| `processor` | 8001 | Procesador presupuesto (existente) |
| `processor-worker` | — | Worker de presupuesto (existente) |
| **`coordination-service`** | **8002** | **HTTP API que envuelve el motor Dupla** |
| **`coordination-worker`** | — | **RQ worker para jobs de clash** |
| `frontend` | 5173 | Nginx sirviendo el build de React |

Abrir el navegador en **http://localhost:5173** y entrar con:

| Usuario | Pass | Rol |
|---------|------|-----|
| `master@dupla.demo` | `master123` | GERENCIA |

---

## 5. Cómo usar la pestaña Hallazgos

1. Login → entrar a un proyecto (o crear uno nuevo).
2. Subir archivos `.dwg` a la pestaña **Archivos**, etiquetando cada uno con su disciplina (ARQ, EST, ELC, etc.).
3. Ir a la pestaña **Hallazgos**.
4. En "Información de coordinación":
   - Elegir la **Carpeta fuente** (por ejemplo `Raíz / TEST_01`).
   - El **Inventario** muestra cuántos archivos hay por disciplina.
   - Si el cuadro dice **"Listo para ejecutar análisis de clashes"**, podés correr.
5. Botón **"Ejecutar análisis"** en la cabecera derecha.
6. Estado pasa a **"ANÁLISIS EN CURSO"** y hace polling cada 5 s.
7. Cuando termina, los dos botones de PDF en el footer se habilitan:
   - **PDF revisión arquitecto** (humano, vertical, narrativa)
   - **PDF auditoría técnica** (índice landscape + detalle por incidencia)

### En modo smoke

El compose levanta el `coordination-service` con `COORDINATION_SMOKE_MODE=true`. Eso hace que el motor use el fixture de `coordination-service/fixtures/smoke_primary_incidents.json` en vez de correr el análisis real (que requiere AutoCAD/accore en Windows). Para demo y desarrollo es suficiente.

Para producción se quita esa variable y se monta un host con accore disponible.

---

## 6. Detalle de los commits

### Commit 1 — `bb44fb2`

> **feat(clashes): integrate coordination jobs, PDF exports, and Hallazgos UI**

47 archivos cambiados (+5 175 / −36). Bloques principales:

#### Backend nuevo
- `app/routes/clash.py`
- `app/services/clash_service.py`
- `app/services/clash_export_service.py`
- `app/services/clash_reports/` (módulo PDF ReportLab — 7 archivos)
- `app/models/project_clash_job.py`
- `alembic/versions/031_project_clash_jobs.py`
- `alembic/versions/032_clash_job_export_metadata.py`
- `tests/test_clash_exports.py`, `test_clash_report_formatting.py`, `test_clash_report_normalize.py`
- `scripts/generate_sample_clash_pdfs.py`, `generate_tortuga_verification_pdfs.py`

#### Backend modificado (sólo adiciones)
- `app/main.py` (+2) — registra `clash.router`
- `app/config.py` (+14) — `coordination_url`, `coordination_default_profile`
- `app/models/__init__.py` (+2) — exporta `ProjectClashJob`
- `app/models/project.py` (+8) — columna `coordination_profile` + relación `clash_jobs`
- `requirements.txt` (+1) — `reportlab==4.2.5`
- `tests/conftest.py` — añade `project_clash_jobs` al TRUNCATE

#### Microservicio nuevo
- `coordination-service/` completo: `Dockerfile`, `main.py`, `worker.py`, `wrapper/run_clash_analysis.py`, `adapters/`, `tasks/`, `fixtures/`

#### Frontend nuevo
- `api/structuralAnalysis.ts`
- `hooks/useStructuralAnalysisJob.ts`
- `lib/coordinationInventory.ts`
- `constants/coordinationProfiles.ts`
- `types/clashJob.ts`

#### Frontend modificado
- `components/project-workspace/tabs/WorkspaceHallazgosTab.tsx` — reemplazo completo, deja de usar el mock y conecta con la API real
- `pages/ProjectWorkspacePage.tsx` — pasa la prop `project={project}` a Hallazgos
- `components/project-workspace/ProjectWorkspaceDashboard.tsx` — usa `getProjectFilesCount` para no traer la lista entera

#### Infra
- `docker-compose.yml` (+44) — `coordination-service` + `coordination-worker`, volumen `dupla_coord_outputs`, bind mount `${DUPLA_PATH:-../Dupla}:/dupla:ro`
- `frontend/nginx.conf` — resolver DNS Docker (`127.0.0.11`) para que sobreviva al recreate del backend

---

### Commit 2 — `a1ba8bc`

> **fix(clashes): restore CLASSIFIED_BUCKETS exports and keep workers alive on idle**

Dos fixes detectados al correr el stack la primera vez:

#### Fix backend
- `backend/app/domain/file_discipline.py` (+54)  
  `clash_service.py` importa `CLASSIFIED_BUCKETS`, `DISCIPLINE_BUCKETS`, `DISCIPLINE_LABELS`, `DISCIPLINE_SHORT` y `discipline_bucket()` — el módulo original sólo exponía el enum `FileDiscipline`. Se añaden las constantes y la función **sin tocar los nombres del enum** (siguen siendo `ARQUITECTURA`, `ESTRUCTURA`, etc. para no romper otros módulos del equipo).

#### Fix infra
- `docker-compose.yml` (+2)  
  Se añade `restart: unless-stopped` a `processor-worker` y `coordination-worker`. El worker de RQ se desconecta de Redis después de unos minutos de inactividad (timeout del socket), y antes dejaba los jobs huérfanos. Con el restart policy, Docker lo revive solo y el próximo job se procesa sin intervención manual.

---

## 7. Verificación rápida tras levantar

```bash
# 1. Todos los contenedores arriba
docker compose ps

# 2. Backend sirve docs
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs   # → 200

# 3. Coordination service responde
curl -s http://localhost:8002/health                                 # → {"ok":true}

# 4. Worker escucha la cola
docker compose logs coordination-worker --tail 5
# → "*** Listening on dupla_coordination..."

# 5. Tests del backend
docker compose exec backend pytest tests/test_clash_report_normalize.py tests/test_clash_report_formatting.py -q
```

---

## 8. Troubleshooting

### "Error 502" en la UI

Significa que el frontend (nginx) no puede contactar al backend. Probable causa:

```bash
docker compose logs backend --tail 30
```

- Si hay `ImportError`, revisar que el repo esté en `a1ba8bc` (commit del fix).
- Si hay error de DNS / Postgres, hacer `docker compose down --remove-orphans` y volver a subir.

### "ANÁLISIS EN CURSO" no termina

El worker probablemente se desconectó de Redis. Con `restart: unless-stopped` aplicado debería auto-recuperarse, pero si tarda:

```bash
docker compose restart coordination-worker
docker compose logs coordination-worker --tail 20
```

### `env file ... backend\.env not found`

Falta crear el `.env`. Ver sección **3.2**.

### El motor Dupla no aparece

Verificar que el bind mount `${DUPLA_PATH:-../Dupla}:/dupla:ro` apunte a un repo Dupla real:

```bash
docker compose exec coordination-service ls /dupla
# Debe listar coordination/, config/, etc.
```

Si está vacío, exportá `DUPLA_PATH` con la ruta absoluta correcta y `docker compose up -d --force-recreate coordination-service coordination-worker`.

---

## 9. Endpoints REST nuevos

| Método | Ruta | Uso |
|--------|------|-----|
| `POST` | `/api/projects/{id}/clash/jobs` | Encolar análisis (recibe `folder_uuid`) |
| `GET` | `/api/projects/{id}/clash/jobs/latest` | Estado del último job (polling) |
| `GET` | `.../clash/jobs/latest/exports/human.pdf` | PDF para revisión manual |
| `GET` | `.../clash/jobs/latest/exports/technical.pdf` | PDF de auditoría técnica |
| `GET` | `/api/projects/{id}/coordination/folders` | Carpetas elegibles del proyecto |
| `GET` | `/api/projects/{id}/coordination/inventory` | Conteo CAD por disciplina + blockers |

---

## 10. Próximos pasos sugeridos

- [ ] Configurar la variable `DUPLA_PATH` en `.env.example` cuando exista.
- [ ] Sustituir el mount Windows-style si se va a CI/Linux: usar `..:/dupla:ro` o un volumen llamado.
- [ ] Cuando el motor real esté disponible, desactivar `COORDINATION_SMOKE_MODE` y agregar un host con accore para clash real.
- [ ] Documentar la rotación de credenciales del `.env` (las que están circulando deberían rotarse si se compartieron por chat).

---

*Documento generado automáticamente a partir de los commits `bb44fb2` y `a1ba8bc` en branch `feat/clashes-integration`.*
