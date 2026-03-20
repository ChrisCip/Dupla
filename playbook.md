# Playbook de Ejecución: Plataforma Grupo Dupla - Módulo Arquitectura

## 1. Arquitectura General y Stack Recomendado
Dado el requerimiento de una experiencia tipo "Excel moderno" y gestión de roles, la arquitectura debe priorizar la reactividad en el cliente y la flexibilidad estructural en la base de datos.

* **Frontend:** Next.js (App Router) + TailwindCSS + **TanStack Table** (o Glide Data Grid / Handsontable para manejo de datos masivos estilo Excel) + Zustand (manejo de estado local de los pliegos antes de guardar) + React Hook Form con Zod.
* **Backend:** Node.js (NestJS o Express/Fastify) o Go + Prisma ORM o Drizzle.
* **Base de Datos:** PostgreSQL. Crucial por su soporte robusto para campos `JSONB`, ideal para almacenar las filas dinámicas de "Pliegos" y "Materiales" sin tener que crear esquemas altamente normalizados y rígidos que rompan la flexibilidad del formato tipo Excel.
* **Despliegue:** Dockerizado, ideal para montar en tu VPS privado.

---

## 2. Modelado de Datos (Esquema Híbrido Relacional/Documental)

La clave para modernizar el Excel sin perder su naturaleza es normalizar la estructura del proyecto y los roles, pero usar documentos (`JSONB`) para las filas de datos.

### Tablas Core (Relacional)

```sql
-- Gestión de Acceso
CREATE TABLE Users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE,
    password_hash VARCHAR,
    role VARCHAR(20) CHECK (role IN ('MASTER', 'COORDINATOR', 'WORKER')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE Modules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) -- ej: 'Arquitectura', 'Ingeniería', etc.
);

CREATE TABLE UserModules (
    user_id UUID REFERENCES Users(id),
    module_id INT REFERENCES Modules(id),
    PRIMARY KEY (user_id, module_id)
);

-- Dominio de Negocio
CREATE TABLE Projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    client_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_by UUID REFERENCES Users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Gestión de Pliegos y Materiales (El "Excel" Interno)

En lugar de crear una tabla `PliegoRows` con 20 columnas estáticas, usaremos una tabla de documentos atada al proyecto.

```sql
CREATE TABLE ProjectArchitectureData (
    project_id UUID PRIMARY KEY REFERENCES Projects(id),
    pliegos JSONB NOT NULL DEFAULT '[]',
    materiales JSONB NOT NULL DEFAULT '[]',
    last_updated_by UUID REFERENCES Users(id),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Estructura del JSONB para `pliegos` (Presupuesto / Partidas)
Cada fila en la interfaz de "Pliegos" debe representar un objeto en este array.
```json
[
  {
    "id": "uuid-v4",
    "capitulo": "01. Movimiento de Tierra",
    "partida": "01.01",
    "descripcion": "Excavación a mano para zapatas",
    "unidad": "m3",
    "cantidad": 120.5,
    "precio_unitario": 450.00,
    "subtotal": 54225.00, 
    "notas": "Terreno rocoso"
  }
]
```

#### Estructura del JSONB para `materiales` (Cubicación / Insumos)
```json
[
  {
    "id": "uuid-v4",
    "categoria": "Acero",
    "descripcion": "Varilla corrugada 3/8\"",
    "unidad": "qq",
    "cantidad_estimada": 50,
    "desperdicio_porcentaje": 5,
    "cantidad_total": 52.5,
    "costo_estimado": 3200.00,
    "proveedor_sugerido": "Ferretería Ochoa"
  }
]
```
*(Nota: Valores como `subtotal` o `cantidad_total` pueden calcularse en el frontend/backend, pero guardarlos en el JSONB facilita la generación de reportes estáticos posteriores).*

---

## 3. Playbook del Backend (APIs y Lógica)

### Middleware y Seguridad
1.  **Auth Guard:** Validar JWT.
2.  **Master Guard:** Middleware específico que rechace cualquier request a `POST /api/users` o `POST /api/modules/assign` si el rol del token no es `MASTER`.
3.  **Module Access Guard:** Antes de cargar un proyecto, verificar si el usuario tiene acceso al módulo 1 (Arquitectura).

### Endpoints Críticos
* `POST /api/projects`: Crea el registro en `Projects` y una entrada vacía en `ProjectArchitectureData`.
* `GET /api/projects/:id/architecture`: Retorna los JSONB de pliegos y materiales.
* `PUT /api/projects/:id/architecture`: Sobrescribe o actualiza (usando `jsonb_set` en Postgres) los arrays completos o filas específicas.

**Estrategia de Guardado:** Implementar **Optimistic UI** en el frontend y hacer *debounced autosaves* (ej: cada 3 segundos después del último teclazo) usando llamadas `PATCH` con las diferencias (deltas), o enviando el array completo si el payload es manejable.

---

## 4. Playbook del Frontend (La Experiencia "Excel")

El éxito del proyecto recae en no hacer formularios de validación tediosos, sino grillas de datos interactables.

### Componente: Data Grid (El reemplazo del Excel)
Usa **TanStack Table** por su modo *headless*. Te permite construir la tabla de HTML y manejar estados complejos (ordenamiento, filtrado, edición inline).

1.  **Edición Inline (Cell Editing):**
    * Cada celda (ej: "Cantidad", "Precio") es un componente `input` estilizado para parecer texto plano hasta que recibe foco.
    * Navegación por teclado (Flechas, Enter, Tab) implementada a nivel de la tabla para saltar entre celdas igual que en Excel.
2.  **Fórmulas Computadas en Tiempo Real:**
    * Usa el store local (Zustand) para recalcular la columna "Subtotal" automáticamente cuando el usuario modifica "Cantidad" o "Precio", sin esperar la respuesta del servidor.
3.  **Filas Dinámicas:**
    * Botones persistentes al final de la tabla: "+ Agregar Fila", "+ Agregar Capítulo".
    * Atajo de teclado (ej: `Shift + Enter`) para agregar una fila rápidamente debajo de la actual.
4.  **Gestión de Pliegos vs Materiales:**
    * Implementa un sistema de Pestañas (Tabs) en la parte superior: `[ Detalles del Proyecto ] | [ Pliegos ] | [ Materiales ]`.
    * Cada tab renderiza una instancia diferente del Data Grid con sus respectivas columnas.

### Flujo Crítico UI
1.  **Master Dashboard:** Vista principal con tabla de `Usuarios`. Modal para invitar usuario y checkboxes para asignar `[x] Módulo Arquitectura`.
2.  **Worker/Coordinator Dashboard:** Lista de Proyectos. Botón "Nuevo Proyecto".
3.  **Workspace del Proyecto (Módulo 1):**
    * El usuario entra, ve los Tabs.
    * Se dirige a "Pliegos". Carga el JSONB desde el backend.
    * Comienza a tipear directamente en la grilla. El sistema muestra un indicador de "Guardando..." y "Guardado" en la esquina superior (Autosave).
    * Si un cálculo matemático de materiales se cruza con pliegos, el estado global de React propaga el cambio en la vista inmediatamente.