import { describe, expect, it } from "vitest";
import { filterVisibleColumns, layoutModeFromWidth, type OperationalColumnDef } from "./tableColumns";

type Row = { id: string };

const COLS: OperationalColumnDef<Row>[] = [
  {
    id: "a",
    header: "A",
    visibility: "always",
    priority: 0,
    minWidth: "4rem",
    cell: () => "a",
  },
  {
    id: "b",
    header: "B",
    visibility: "standard",
    priority: 1,
    minWidth: "4rem",
    cell: () => "b",
  },
  {
    id: "c",
    header: "C",
    visibility: "wide",
    priority: 2,
    minWidth: "4rem",
    cell: () => "c",
  },
];

describe("tableColumns", () => {
  it("filterVisibleColumns respeita modos semânticos", () => {
    expect(filterVisibleColumns(COLS, "compact").map((c) => c.id)).toEqual(["a"]);
    expect(filterVisibleColumns(COLS, "standard").map((c) => c.id)).toEqual(["a", "b"]);
    expect(filterVisibleColumns(COLS, "wide").map((c) => c.id)).toEqual(["a", "b", "c"]);
  });

  it("layoutModeFromWidth usa thresholds", () => {
    expect(layoutModeFromWidth(400, 832, 1152)).toBe("compact");
    expect(layoutModeFromWidth(900, 832, 1152)).toBe("standard");
    expect(layoutModeFromWidth(1200, 832, 1152)).toBe("wide");
  });
});
