import type { User } from "../auth/types";

export function canReadCosting(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("costing:read");
}

export function canWriteCosting(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("costing:write");
}

export function canPublishCosting(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("costing:publish");
}

export function canResolveRecon(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("reconciliation:resolve");
}
