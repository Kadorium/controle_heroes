import type { User } from "../auth/types";

// Compatibility for existing product surfaces; AppShell owns the shared area navigation.
export function ProductAreaNav(_props: { user: User }) { return null; }
