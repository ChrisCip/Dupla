import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'

import { TutorialesReference } from '../components/tutorials/TutorialesReference'
import { PrimaryButton } from '../components/PrimaryButton'
import {
  startChatTour,
  startProjectsTour,
  startSidebarTour,
  startTasksTour,
  startWorkspaceArchivosTour,
  startWorkspaceDetallesShortcutsTour,
  startWorkspaceTour,
} from '../lib/productTours'
import { useAuthStore } from '../store/authStore'

const cardClass = 'rounded-xl border border-black/10 bg-white p-5 shadow-[var(--shadow-card)]'

export function TutorialesPage() {
  const navigate = useNavigate()
  const role = useAuthStore((s) => s.role)

  const recorridos = useMemo(
    () => [
      {
        id: 'sidebar',
        title: 'Menú lateral',
        description:
          'Te muestra dónde está cada cosa: obras, mensajes, tareas y esta página de ayuda. Verás cómo achicar el menú para ganar espacio. Si tu perfil es de dirección, también aparece Usuarios. Empieza sin cambiar de pantalla.',
        onStart: () => startSidebarTour(role),
      },
      {
        id: 'projects',
        title: 'Proyectos',
        description:
          'Cómo buscar obras, ver la lista o el tablero por fases y abrir una obra. Si puedes crear proyectos, verás también el botón de obra nueva.',
        onStart: () => startProjectsTour(navigate, role),
      },
      {
        id: 'tasks',
        title: 'Tablero de tareas',
        description:
          'Recorre tu tablero Kanban: encabezado, barra de búsqueda y archivadas, y columnas donde movés las tarjetas (solo ves las tareas propias).',
        onStart: () => startTasksTour(navigate),
      },
      {
        id: 'chat',
        title: 'Chat interno',
        description:
          'Dónde están el título del chat, la lista de conversaciones y la caja para escribir mensajes.',
        onStart: () => startChatTour(navigate),
      },
      {
        id: 'workspace',
        title: 'Obra abierta: vista general',
        description:
          'Ejemplo de práctica: parte superior de la obra, lista de secciones a la izquierda y contenido al centro. Sirve de introducción antes de los recorridos de Detalles o Archivos.',
        onStart: () => startWorkspaceTour(navigate),
      },
      {
        id: 'workspace-detalles-shortcuts',
        title: 'Obra abierta: tareas y chat de la obra',
        description:
          'Desde Detalles: acceso al tablero de tareas solo de esa obra y al chat grupal de la obra (no es el mismo acceso que «Chat» en el menú).',
        onStart: () => startWorkspaceDetallesShortcutsTour(navigate),
      },
      {
        id: 'workspace-archivos',
        title: 'Obra abierta: archivos',
        description:
          'La sección Archivos: buscar, subir planos, crear carpetas y el área donde puedes arrastrar archivos. El ejemplo de práctica debe existir en tu cuenta (suele cargarse al iniciar el sistema en pruebas).',
        onStart: () => startWorkspaceArchivosTour(navigate),
      },
    ],
    [navigate, role],
  )

  return (
    <div className="w-full min-w-0 pb-8">
      <header className="mb-6 shrink-0">
        <h1 className="text-2xl font-semibold text-ink md:text-3xl">Tutoriales</h1>
        <p className="mt-2 text-sm text-muted">
          Cada recorrido te guía paso a paso y resalta la zona en pantalla. Puedes salir en cualquier
          momento con Escape o el botón de cerrar. En varios casos la app abre primero la pantalla
          adecuada y luego empieza la guía.
        </p>
      </header>

      <section aria-labelledby="recorridos-heading" className="mb-10">
        <h2 id="recorridos-heading" className="text-lg font-semibold text-ink">
          Recorridos guiados
        </h2>
        <p className="mt-1 text-sm text-muted">
          Elige un tema y pulsa el botón para iniciar. Volverás a esta página con el enlace «Tutoriales»
          en el menú lateral cuando quieras repetir.
        </p>
        <ul className="mt-5 grid list-none gap-4 p-0 sm:grid-cols-2">
          {recorridos.map((r) => (
            <li key={r.id}>
              <div className={`${cardClass} flex h-full flex-col`}>
                <h3 className="text-base font-semibold text-ink">{r.title}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-muted">{r.description}</p>
                <PrimaryButton type="button" className="mt-4 self-start" onClick={r.onStart}>
                  Comenzar recorrido
                </PrimaryButton>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section id="guia-escrita" className="border-t border-black/10 pt-10">
        <h2 className="text-lg font-semibold text-ink">Guía de referencia por escrito</h2>
        <p className="mt-2 text-sm text-muted">
          Textos para consultar cuando quieras, sin seguir el recorrido animado: menú, obras, inicio del
          workspace y cada sección (incluida Hallazgos), avisos y, si aplica, administración de usuarios.
        </p>
        <div className="mt-6">
          <TutorialesReference />
        </div>
      </section>
    </div>
  )
}
