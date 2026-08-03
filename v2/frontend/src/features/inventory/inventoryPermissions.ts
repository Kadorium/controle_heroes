import type { User } from "../auth/types";

export function canReadInventory(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("inventory:read");
}

export function canWriteInventory(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("inventory:write");
}

export function canAdjustInventory(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("inventory:adjust");
}
