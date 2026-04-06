import { z } from 'zod'

export const adminCreateUserSchema = z
  .object({
    email: z.string().min(1, 'Requerido').email('Correo inválido'),
    password: z.string().min(8, 'Mínimo 8 caracteres').max(128, 'Máximo 128 caracteres'),
    role: z.enum(['MASTER', 'COORDINATOR', 'WORKER']),
    architectureAccess: z.boolean(),
  })
  .refine((d) => d.architectureAccess, {
    message: 'Debe concederse acceso al módulo Arquitectura (o amplía el backend para otros módulos).',
    path: ['architectureAccess'],
  })

export type AdminCreateUserForm = z.infer<typeof adminCreateUserSchema>
