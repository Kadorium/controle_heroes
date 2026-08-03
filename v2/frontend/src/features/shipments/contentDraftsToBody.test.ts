import { describe, expect, it } from "vitest";
import { contentDraftsToBody } from "./ShipmentLogisticsPanels";

describe("contentDraftsToBody", () => {
  it("inclui source_line_reference no payload", () => {
    const body = contentDraftsToBody([
      {
        shipment_item_id: "3",
        contained_quantity: "10",
        source_unit: "PZ",
        source_line_reference: "L1",
        source_ncm: "9403",
        source_description: "Mesa",
        units_per_package: "10",
        unit_net_weight_kg: "0.5",
        unit_gross_weight_kg: "0.6",
        source_total_net_weight_kg: "5",
        source_total_gross_weight_kg: "6",
      },
      {
        shipment_item_id: "",
        contained_quantity: "1",
        source_unit: "PZ",
        source_line_reference: "skip",
        source_ncm: "",
        source_description: "",
        units_per_package: "",
        unit_net_weight_kg: "",
        unit_gross_weight_kg: "",
        source_total_net_weight_kg: "",
        source_total_gross_weight_kg: "",
      },
    ]);
    expect(body).toHaveLength(1);
    expect(body[0]).toMatchObject({
      shipment_item_id: 3,
      source_line_reference: "L1",
      source_ncm: "9403",
      contained_quantity: "10",
    });
  });
});
