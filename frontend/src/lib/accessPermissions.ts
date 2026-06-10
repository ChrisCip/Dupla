import type { UserRole } from '../constants/userRoles'

export function hasElevatedAccess(role: UserRole | null, isTeamLeader: boolean): boolean {
  return role === 'GERENCIA' || isTeamLeader
}

export function canCreateUsers(role: UserRole | null): boolean {
  return role === 'GERENCIA'
}

export function canAssignTeamLeader(role: UserRole | null): boolean {
  return role === 'GERENCIA'
}

export function canMarkControlReview(role: UserRole | null, isTeamLeader: boolean): boolean {
  return role === 'CONTROL' || hasElevatedAccess(role, isTeamLeader)
}

export function canApproveSpecifications(role: UserRole | null, isTeamLeader: boolean): boolean {
  return role === 'ARQUITECTURA' || hasElevatedAccess(role, isTeamLeader)
}
