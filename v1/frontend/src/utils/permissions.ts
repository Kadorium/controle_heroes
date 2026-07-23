import type { User } from "../api";

export function hasPermission(user: User | null | undefined, permission: string): boolean {
  if (!user?.permissions) return false;
  return user.permissions.includes(permission);
}

export const PERM_USERS_READ = "users:read";
export const PERM_USERS_WRITE = "users:write";
