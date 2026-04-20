import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import { Link } from 'react-router-dom'

import { formatAllowedProjectExtensionsHint } from '../../constants/projectAllowedFiles'
import { TUTORIAL_PROJECT_PATH } from '../../constants/tutorialProject'
import { TUTORIALS_TOC } from '../../constants/tutorialesToc'
import { WORKFLOW_PHASE_LABELS } from '../../constants/workflowPhases'

const sectionClass = 'space-y-3'
const h3Class = 'text-base font-semibold text-ink'
const pClass = 'text-sm leading-relaxed text-ink'
const listClass = 'list-inside list-disc space-y-1.5 text-sm leading-relaxed text-ink'
const cardClass = 'rounded-xl border border-black/10 bg-white p-5 shadow-[var(--shadow-card)]'
const accordionItemClass =
  'scroll-mt-6 overflow-hidden rounded-xl border border-black/10 bg-white shadow-[var(--shadow-card)]'

function scrollTargetIntoViewSmooth(id: string): void {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  })
}

/** Guía escrita completa (ancla del índice); cada sección va en un acordeón. */
export function TutorialesReference() {
  const extHint = formatAllowedProjectExtensionsHint()
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const toggleSection = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }, [])

  const revealAndScroll = useCallback((id: string) => {
    setExpandedId(id)
    window.history.replaceState(null, '', `#${id}`)
    scrollTargetIntoViewSmooth(id)
  }, [])

  useEffect(() => {
    const applyHash = (hash: string) => {
      const raw = hash.startsWith('#') ? hash.slice(1) : hash
      if (raw && TUTORIALS_TOC.some((t) => t.id === raw)) {
        setExpandedId(raw)
        scrollTargetIntoViewSmooth(raw)
      } else if (!raw) {
        setExpandedId(null)
      }
    }
    applyHash(window.location.hash)
    const onHashChange = () => applyHash(window.location.hash)
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const sectionBodies: Record<string, ReactNode> = {
    navegacion: (
      <div className={sectionClass}>
        <ul className={listClass}>
          <li>
            Usa los enlaces del menú para ir a <strong>Proyectos</strong>, <strong>Chat interno</strong>,{' '}
            <strong>Tablero</strong> y <strong>Tutoriales</strong>. Si tienes perfil de dirección, también
            verás <strong>Usuarios</strong>.
          </li>
          <li>
            El botón <strong>Contraer</strong> deja el menú más estrecho y solo muestra iconos; al volver a
            expandirlo verás otra vez el texto de cada opción.
          </li>
          <li>
            En la parte inferior aparece tu correo, el rol y el contador de <strong>avisos</strong> sin
            leer. Usa <strong>Salir</strong> para cerrar sesión.
          </li>
        </ul>
      </div>
    ),
    proyectos: (
      <div className={sectionClass}>
        <p className={pClass}>
          En <strong>Proyectos</strong> ves la lista o el tablero por etapas. Puedes buscar por nombre,
          cambiar cómo se muestran las obras y abrir una para trabajar dentro de ella.
        </p>
        <h3 className={h3Class}>Crear un proyecto</h3>
        <ul className={listClass}>
          <li>
            Abre el flujo de <strong>Nuevo proyecto</strong> (modal con pasos). Indica un nombre
            reconocible y, si quieres, cliente.
          </li>
          <li>
            <strong>Tipo residencial:</strong> sigue el flujo completo desde criterios de arranque
            (según la fase del proyecto en el tablero).
          </li>
          <li>
            <strong>Tipo licitación:</strong> entra inicialmente en revisión de arquitectura; al crear
            debes adjuntar al menos un archivo permitido ({extHint}) en el paso de archivos.
          </li>
          <li>
            Si tienes perfil de dirección, en el paso de equipo puedes elegir quién más podrá entrar a la
            obra además de quien la crea.
          </li>
        </ul>
        <h3 className={h3Class}>Tablero de proyectos y fases</h3>
        <p className={pClass}>
          En vista tablero, las columnas siguen el orden del flujo (por ejemplo:{' '}
          {WORKFLOW_PHASE_LABELS.BOOTSTRAPPING}, {WORKFLOW_PHASE_LABELS.AWAITING_FILES}, …). Solo se
          permiten saltos a fases <strong>adyacentes</strong> cuando la regla del producto lo permite:
          arrastra una tarjeta de proyecto hacia la columna destino o usa los controles que muestre la
          interfaz.
        </p>
      </div>
    ),
    workspace: (
      <div className={sectionClass}>
        <p className={pClass}>
          Cuando abres una obra desde la lista, entras a la <strong>vista de la obra</strong>: a la
          izquierda tienes las secciones (datos, archivos, etc.) y al centro el contenido. Puedes pasar
          de una sección a otra en cualquier momento; lo que puedas hacer en cada una depende de la etapa
          del proceso y de tu perfil. Si aparece la opción de pantalla completa, úsala cuando necesites más
          espacio.
        </p>
        <p className={pClass}>
          Para practicar sin tocar obras reales, usa el{' '}
          <Link className="font-semibold text-primary underline-offset-2 hover:underline" to={TUTORIAL_PROJECT_PATH}>
            ejemplo «Tutorial · Workspace Dupla»
          </Link>
          , que en entornos de prueba suele crearse al preparar la base de datos e incluye una tarea de
          muestra.
        </p>
      </div>
    ),
    detalles: (
      <div className={sectionClass}>
        <p className={pClass}>
          Resume datos del proyecto (nombre, cliente, fase, etc.) y accesos útiles. Desde aquí puedes
          abrir el <strong>chat del proyecto</strong> si la pantalla lo ofrece, para coordinar con el
          equipo en el contexto de esa obra.
        </p>
      </div>
    ),
    flujo: (
      <div className={sectionClass}>
        <ul className={listClass}>
          <li>Consulta la <strong>fase actual</strong> del proceso de la obra y el siguiente paso previsto.</li>
          <li>
            El <strong>checklist de arranque</strong> (criterios de arranque) se edita aquí cuando
            corresponda; guarda los cambios antes de avanzar.
          </li>
          <li>
            Las acciones de <strong>avanzar fase</strong> u otros cambios dependen de tu perfil y de las
            reglas del proceso; la aplicación te dirá en pantalla si algo falta o si se guardó bien.
          </li>
        </ul>
      </div>
    ),
    archivos: (
      <div className={sectionClass}>
        <p className={pClass}>
          Aquí guardas y organizas los documentos de la obra en carpetas. Solo se admiten ciertos tipos de
          archivo ({extHint}).
        </p>
        <ul className={listClass}>
          <li>
            <strong>Navegación:</strong> entra en carpetas y usa las migas (por ejemplo «Raíz») para
            volver atrás.
          </li>
          <li>
            <strong>Subir:</strong> usa el botón o <strong>arrastra archivos</strong> a la zona punteada;
            se abre un asistente que te guía paso a paso para subir, revisar datos y elegir carpeta.
          </li>
          <li>
            <strong>Crear carpeta:</strong> usa el flujo de la propia pestaña cuando esté disponible
            para organizar planos por disciplina u otro criterio.
          </li>
          <li>
            <strong>Filtros y búsqueda:</strong> filtra por disciplina y busca por texto; puedes
            alternar vista en cuadrícula o lista.
          </li>
          <li>
            <strong>Editar / mover:</strong> abre un archivo para cambiar nombre o descripción; arrastra
            entre carpetas cuando la pantalla lo permita.
          </li>
          <li>
            Si el flujo del proyecto requiere condiciones sobre archivos, puede mostrarse un aviso en
            esta área (mensajes contextuales del flujo).
          </li>
        </ul>
      </div>
    ),
    'entrega-planos': (
      <div className={sectionClass}>
        <p className={pClass}>
          Administración de solicitudes de <strong>entrega de planos (SDP)</strong>: altas, ediciones y
          bajas de filas según los botones disponibles. Los detalles de cada fila (fechas, estados,
          observaciones) siguen el formulario que muestre la aplicación.
        </p>
      </div>
    ),
    revisiones: (
      <div className={sectionClass}>
        <p className={pClass}>
          Registro y decisión sobre <strong>revisiones</strong> del proyecto: revisa el listado,
          aporta notas y utiliza la decisión aprobada / rechazada (u opciones equivalentes) según el
          formulario visible. Los datos concretos dependen del estado del proyecto y de tu rol.
        </p>
      </div>
    ),
    especificaciones: (
      <div className={sectionClass}>
        <p className={pClass}>
          Trabajo con el <strong>pliego / especificaciones</strong>: resumen, campos estructurados y
          guardado. Sincroniza cambios con el botón de guardar cuando proceda; los mensajes de error
          indican campos obligatorios o conflictos de versión.
        </p>
      </div>
    ),
    presupuesto: (
      <div className={sectionClass}>
        <p className={pClass}>
          Aquí se sigue el <strong>presupuesto de la obra</strong> (versiones acordadas, hitos con el
          cliente, etc.). Completa los campos que puedas editar y guarda; verás reflejado el estado del
          trámite presupuestario.
        </p>
      </div>
    ),
    eventos: (
      <div className={sectionClass}>
        <p className={pClass}>
          <strong>Historial de lo ocurrido en la obra</strong>: cambios de fase, archivos, tareas,
          equipo y otros avisos. La lista se va actualizando mientras tengas esta sección abierta.
        </p>
        <ul className={listClass}>
          <li>
            <strong>Paginación:</strong> navega entre páginas cuando haya muchos eventos.
          </li>
          <li>
            <strong>Filtro por tipo:</strong> reduce el listado al tipo de evento que te interese
            (subidas, cambios de fase, tareas, entregas de planos, etc.).
          </li>
          <li>
            <strong>Búsqueda:</strong> escribe palabras clave; la lista se actualiza poco después de que
            termines de teclear para no sobrecargar la aplicación.
          </li>
          <li>
            Cada fila muestra <strong>título</strong>, <strong>fecha</strong>,{' '}
            <strong>quién actuó</strong> (usuario o sistema) y <strong>detalle</strong> en forma de
            etiquetas y valores cuando aplica.
          </li>
        </ul>
      </div>
    ),
    pliegos: (
      <div className={sectionClass}>
        <p className={pClass}>
          Formularios y estado de ítems del <strong>pliego</strong> (incluye integración con datos de
          arquitectura cuando el flujo lo requiera). Completa y guarda los bloques según las secciones
          visibles; respeta las validaciones indicadas en pantalla.
        </p>
      </div>
    ),
    materiales: (
      <div className={sectionClass}>
        <p className={pClass}>
          Listado y edición de <strong>materiales</strong> vinculados al proyecto: altas, cambios y
          bajas según los controles mostrados. Útil para cubicación y trazabilidad documental.
        </p>
      </div>
    ),
    'config-proyecto': (
      <div className={sectionClass}>
        <p className={pClass}>
          Desde la parte superior de la obra puedes abrir <strong>configuración</strong>: nombre, cliente,
          <strong>miembros del equipo</strong> (invitar o quitar según lo que te permita tu perfil) y otros
          datos. Algunos cambios importantes pueden pedir confirmación o perfil de dirección.
        </p>
      </div>
    ),
    tablero: (
      <div className={sectionClass}>
        <p className={pClass}>
          En <strong>Tablero</strong> (menú lateral) ves <strong>todas las tareas del equipo</strong> en
          columnas por estado: mueve tarjetas y ábrelas para ver el detalle.
        </p>
        <ul className={listClass}>
          <li>
            <strong>Nueva tarea:</strong> botón para crear una tarea; si el formulario lo permite,
            puedes asociarla a una obra concreta.
          </li>
          <li>
            <strong>Filtros:</strong> solo lo tuyo, por persona, tareas archivadas y búsqueda de texto en
            el tablero.
          </li>
          <li>
            <strong>Solo una obra:</strong> desde la sección Detalles de esa obra, el enlace «Tablero del
            proyecto» abre este mismo tablero ya filtrado para que solo veas las tareas de esa obra.
          </li>
        </ul>
      </div>
    ),
    chat: (
      <div className={sectionClass}>
        <p className={pClass}>
          En <strong>Chat interno</strong> tienes conversaciones directas, el canal general y grupos.
          El listado izquierdo muestra hilos; al elegir uno ves los mensajes y puedes escribir en la
          parte inferior. Puedes iniciar chat nuevo, conversación de grupo u otras acciones que
          ofrezcan los botones superiores. Un indicador en el menú lateral señala mensajes no leídos.
        </p>
      </div>
    ),
    avisos: (
      <div className={sectionClass}>
        <p className={pClass}>
          Junto a tu nombre en el menú lateral verás <strong>cuántos avisos tienes sin leer</strong>. Son
          avisos del sistema sobre cosas que te incumben. Ábrelos y márcalos como leídos según las opciones
          que ofrezca la pantalla.
        </p>
      </div>
    ),
    admin: (
      <div className={sectionClass}>
        <p className={pClass}>
          Solo quien tiene perfil de <strong>dirección</strong> ve <strong>Usuarios</strong> en el menú.
          Ahí se dan de alta y se editan las cuentas (correo, nombre, contraseña y qué pueden ver en la
          aplicación). El resto de perfiles no usa esta pantalla.
        </p>
      </div>
    ),
  }

  return (
    <>
      <nav aria-label="Índice de la guía escrita" className={`${cardClass} mb-8`}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Guía por secciones</h2>
        <ol className="columns-1 gap-x-8 gap-y-1 text-sm sm:columns-2">
          {TUTORIALS_TOC.map((item, i) => (
            <li key={item.id} className="mb-1 break-inside-avoid">
              <a
                href={`#${item.id}`}
                className="text-primary underline-offset-2 hover:underline"
                onClick={(e) => {
                  e.preventDefault()
                  revealAndScroll(item.id)
                }}
              >
                {i + 1}. {item.label}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <div className="space-y-3">
        {TUTORIALS_TOC.map((item) => {
          const isOpen = expandedId === item.id
          return (
            <div key={item.id} id={item.id} className={accordionItemClass}>
              <h2 className="m-0">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left text-base font-semibold text-ink transition-colors hover:bg-black/3 sm:px-5"
                  aria-expanded={isOpen}
                  aria-controls={`panel-${item.id}`}
                  id={`heading-${item.id}`}
                  onClick={() => {
                    toggleSection(item.id)
                    if (!isOpen) {
                      window.history.replaceState(null, '', `#${item.id}`)
                    } else {
                      window.history.replaceState(null, '', window.location.pathname + window.location.search)
                    }
                  }}
                >
                  <span>{item.label}</span>
                  <ChevronDown
                    className={`h-5 w-5 shrink-0 text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                    aria-hidden
                  />
                </button>
              </h2>
              {isOpen && (
                <div
                  id={`panel-${item.id}`}
                  role="region"
                  aria-labelledby={`heading-${item.id}`}
                  className="border-t border-black/10 px-4 pb-4 pt-1 sm:px-5 sm:pb-5"
                >
                  {sectionBodies[item.id]}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </>
  )
}
