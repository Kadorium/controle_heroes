import { useCallback, useEffect, useState } from "react";
import {
  customsApi,
  landedCostApi,
  shipmentsApi,
  stockApi,
  type CustomsDocument,
  type EntrepostoMovement,
  type LandedCostVersion,
  type QuantityChain,
  type Shipment,
  type ShipmentItem,
  type Tax,
} from "../../../api";
import { useOrderCentral } from "../OrderCentralContext";
import { buildSkuRows, type SkuRow } from "./logisticsUtils";

export function useLogisticsData(importationId: number) {
  const { data: orderCentral, reloadCentral } = useOrderCentral();
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [itemsByShipment, setItemsByShipment] = useState<Record<number, ShipmentItem[]>>({});
  const [chain, setChain] = useState<QuantityChain[]>([]);
  const [entreposto, setEntreposto] = useState<EntrepostoMovement[]>([]);
  const [docs, setDocs] = useState<CustomsDocument[]>([]);
  const [taxes, setTaxes] = useState<Tax[]>([]);
  const [lcVersions, setLcVersions] = useState<LandedCostVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    if (!importationId || Number.isNaN(importationId)) return;
    setLoading(true);
    setError("");
    try {
      const [shipList, chainData, epData, docData, taxData, lcData] = await Promise.all([
        shipmentsApi.list(importationId),
        stockApi.quantityChain(importationId),
        stockApi.listEntrepostoMovements(importationId),
        customsApi.listDocuments(importationId),
        customsApi.listTaxes(importationId),
        landedCostApi.listVersions(importationId),
      ]);
      setShipments(shipList);
      setChain(chainData);
      setEntreposto(epData);
      setDocs(docData);
      setTaxes(taxData);
      setLcVersions(lcData);

      const itemEntries = await Promise.all(
        shipList.map(async (s) => {
          const items = await shipmentsApi.listItems(s.id);
          return [s.id, items] as const;
        }),
      );
      setItemsByShipment(Object.fromEntries(itemEntries));
      await reloadCentral();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar logística");
    } finally {
      setLoading(false);
    }
  }, [importationId, reloadCentral]);

  useEffect(() => {
    reload();
  }, [reload]);

  const models = orderCentral?.models ?? [];
  const skuRows: SkuRow[] = buildSkuRows(models, chain);
  const dispatchPending = orderCentral?.dispatch_pending ?? [];

  return {
    loading,
    error,
    setError,
    reload,
    orderCentral,
    shipments,
    itemsByShipment,
    chain,
    entreposto,
    docs,
    taxes,
    lcVersions,
    skuRows,
    dispatchPending,
  };
}
