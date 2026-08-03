import type { User } from "../auth/types";

export function canReadLogistics(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("logistics:read");
}

export function canWriteLogistics(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("logistics:write");
}
