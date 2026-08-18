/** Nationalization + inventory API helpers (I5-4). Local types until generate:api. */

async function parseError(res: Response, fallback: string): Promise<never> {
  let msg = fallback;
  let code: string | undefined;
  try {
    const body = await res.json();
    msg = body?.message || body?.detail || fallback;
    code = body?.error || body?.code;
  } catch {
    /* ignore */
  }
  const err = new Error(msg) as Error & { status?: number; code?: string };
  err.status = res.status;
  err.code = code;
  throw err;
}

export type NationalizationItem = {
  id: number;
  doganale_line_id: number | null;
  invoice_item_id: number | null;
  shipment_item_id: number | null;
  product_id: number | null;
  quantity: string;
  notes: string | null;
};

export type Nationalization = {
  id: number;
  process_id: number;
  reference: string | null;
  status: string;
  version: number;
  notes: string | null;
  confirmed_at: string | null;
  reversed_at: string | null;
  created_at: string | null;
  items: NationalizationItem[];
};

export type GoodsReceiptLine = {
  id: number;
  product_id: number;
  quantity: string;
  nationalization_item_id: number | null;
  shipment_item_id: number | null;
  notes: string | null;
};

export type GoodsReceipt = {
  id: number;
  location_id: number;
  location_code: string | null;
  location_type: string | null;
  process_id: number | null;
  nationalization_id: number | null;
  receipt_type: string;
  status: string;
  version: number;
  notes: string | null;
  received_at: string | null;
  created_at: string | null;
  lines: GoodsReceiptLine[];
};

export type StockLocation = {
  id: number;
  code: string;
  name: string;
  location_type: string;
  active: boolean;
};

export type InventoryMovement = {
  id: number;
  location_id: number;
  location_code?: string | null;
  location_type?: string | null;
  location_name?: string | null;
  product_id: number;
  product_sku?: string | null;
  product_description?: string | null;
  quantity_delta: string;
  movement_type: string;
  receipt_line_id: number | null;
  nationalization_item_id: number | null;
  reversal_of_id: number | null;
  reason: string | null;
  created_at: string | null;
};

export type SkuPosition = {
  product_id: number;
  available_qty: string;
  bonded_qty: string;
  quarantine_qty: string;
  cleared_not_received_qty: string;
  in_clearance_qty: string;
  in_transit_qty: string;
  future_order_qty: string | null;
  future_order_qty_note: string | null;
  etas: Array<Record<string, unknown>>;
  balances: Array<Record<string, unknown>>;
};

export type ClearanceResidual = {
  source_kind: string;
  shipment_item_id: number | null;
  invoice_item_id: number | null;
  allocated_qty: string;
  nationalized_qty: string;
  residual_qty: string;
  product_id: number | null;
  product_sku: string | null;
  product_name: string | null;
  shipped_qty: string | null;
};

export async function listClearanceResiduals(processId: number): Promise<ClearanceResidual[]> {
  const res = await fetch(`/api/import-processes/${processId}/clearance-residuals`, {
    credentials: "include",
  });
  if (!res.ok) await parseError(res, "Erro ao listar residual de nacionalização");
  return res.json();
}

export async function listNationalizations(processId: number): Promise<Nationalization[]> {
  const res = await fetch(`/api/import-processes/${processId}/nationalizations`, {
    credentials: "include",
  });
  if (!res.ok) await parseError(res, "Erro ao listar liberações");
  return res.json();
}

export async function createNationalization(
  processId: number,
  body: { reference?: string; notes?: string },
): Promise<Nationalization> {
  const res = await fetch(`/api/import-processes/${processId}/nationalizations`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) await parseError(res, "Erro ao criar liberação");
  return res.json();
}

export async function addNationalizationItems(
  processId: number,
  natId: number,
  body: {
    expected_version: number;
    items: Array<{
      quantity: string;
      product_id?: number | null;
      invoice_item_id?: number | null;
      shipment_item_id?: number | null;
      doganale_line_id?: number | null;
      notes?: string | null;
    }>;
  },
): Promise<Nationalization> {
  const res = await fetch(
    `/api/import-processes/${processId}/nationalizations/${natId}/items`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) await parseError(res, "Erro ao adicionar itens");
  return res.json();
}

export async function confirmNationalization(
  processId: number,
  natId: number,
  expected_version: number,
): Promise<Nationalization> {
  const res = await fetch(
    `/api/import-processes/${processId}/nationalizations/${natId}/confirm`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_version }),
    },
  );
  if (!res.ok) await parseError(res, "Erro ao confirmar liberação");
  return res.json();
}

export async function reverseNationalization(
  processId: number,
  natId: number,
  expected_version: number,
): Promise<Nationalization> {
  const res = await fetch(
    `/api/import-processes/${processId}/nationalizations/${natId}/reverse`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_version }),
    },
  );
  if (!res.ok) await parseError(res, "Erro ao reverter liberação");
  return res.json();
}

export type ReceiptResidual = {
  nationalization_id: number;
  nationalization_item_id: number;
  product_id: number | null;
  product_sku: string | null;
  product_name: string | null;
  nationalized_qty: string;
  received_qty: string;
  residual_qty: string;
};

export async function listReceiptResiduals(processId: number): Promise<ReceiptResidual[]> {
  const res = await fetch(`/api/inventory/processes/${processId}/receipt-residuals`, {
    credentials: "include",
  });
  if (!res.ok) await parseError(res, "Erro ao listar residual recebível");
  return res.json();
}

export async function listLocations(): Promise<StockLocation[]> {
  const res = await fetch("/api/inventory/locations", { credentials: "include" });
  if (!res.ok) await parseError(res, "Erro ao listar localizações");
  return res.json();
}

export async function listReceipts(processId?: number): Promise<GoodsReceipt[]> {
  const q = processId != null ? `?process_id=${processId}` : "";
  const res = await fetch(`/api/inventory/receipts${q}`, { credentials: "include" });
  if (!res.ok) await parseError(res, "Erro ao listar recebimentos");
  return res.json();
}

export async function createReceipt(body: {
  location_code?: string;
  location_id?: number;
  from_location_code?: string;
  process_id?: number;
  nationalization_id?: number;
  receipt_type: string;
  notes?: string;
}): Promise<GoodsReceipt> {
  const res = await fetch("/api/inventory/receipts", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) await parseError(res, "Erro ao criar recebimento");
  return res.json();
}

export async function addReceiptLines(
  receiptId: number,
  body: {
    expected_version: number;
    lines: Array<{
      product_id: number;
      quantity: string;
      nationalization_item_id?: number | null;
      shipment_item_id?: number | null;
    }>;
  },
): Promise<GoodsReceipt> {
  const res = await fetch(`/api/inventory/receipts/${receiptId}/lines`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) await parseError(res, "Erro ao adicionar linhas");
  return res.json();
}

export async function confirmReceipt(
  receiptId: number,
  expected_version: number,
): Promise<GoodsReceipt> {
  const res = await fetch(`/api/inventory/receipts/${receiptId}/confirm`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expected_version }),
  });
  if (!res.ok) await parseError(res, "Erro ao confirmar recebimento");
  return res.json();
}

export async function reverseReceipt(
  receiptId: number,
  expected_version: number,
): Promise<GoodsReceipt> {
  const res = await fetch(`/api/inventory/receipts/${receiptId}/reverse`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expected_version }),
  });
  if (!res.ok) await parseError(res, "Erro ao reverter recebimento");
  return res.json();
}

export async function listMovements(query?: {
  product_id?: number;
  limit?: number;
}): Promise<InventoryMovement[]> {
  const params = new URLSearchParams();
  if (query?.product_id != null) params.set("product_id", String(query.product_id));
  if (query?.limit != null) params.set("limit", String(query.limit));
  const qs = params.toString();
  const res = await fetch(`/api/inventory/movements${qs ? `?${qs}` : ""}`, {
    credentials: "include",
  });
  if (!res.ok) await parseError(res, "Erro ao listar movimentos");
  return res.json();
}

export async function getSkuPosition(productId: number): Promise<SkuPosition> {
  const res = await fetch(`/api/inventory/sku/${productId}/position`, {
    credentials: "include",
  });
  if (!res.ok) await parseError(res, "Erro ao carregar posição SKU");
  return res.json();
}
