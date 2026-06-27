import { useEffect } from "react";
import { LoadingState } from "../../../components";
import { customsApi, landedCostApi, shipmentsApi, stockApi } from "../../../api";
import { useLogisticsData } from "./useLogisticsData";
import { LogisticsPhaseRail } from "./LogisticsPhaseRail";
import { LogisticsSkuMatrix } from "./LogisticsSkuMatrix";
import { DispatchSection } from "./sections/DispatchSection";
import { ShipmentsSection } from "./sections/ShipmentsSection";
import { TransitSection } from "./sections/TransitSection";
import { EntrepostoSection } from "./sections/EntrepostoSection";
import { CustomsSection } from "./sections/CustomsSection";
import { NationalizationSection } from "./sections/NationalizationSection";
import { StockSection } from "./sections/StockSection";

interface Props {
  importationId: number;
}

export function LogisticsWorkflowPage({ importationId }: Props) {
  const {
    loading,
    error,
    setError,
    reload,
    shipments,
    itemsByShipment,
    entreposto,
    docs,
    taxes,
    lcVersions,
    skuRows,
    dispatchPending,
  } = useLogisticsData(importationId);

  useEffect(() => {
    const hash = window.location.hash;
    if (!hash || loading) return;
    const timer = window.setTimeout(() => {
      document.querySelector(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 150);
    return () => window.clearTimeout(timer);
  }, [loading]);

  const phaseCounts: Record<string, number> = {
    despachar: skuRows.filter((r) => (r.to_dispatch ?? 0) > 0).length,
    embarques: shipments.length,
    transito: shipments.filter((s) => s.status !== "PLANNED").length,
    aduana: docs.length,
    entreposto: entreposto.length,
    nacionalizacao: skuRows.filter((r) => r.quantity_nationalized != null).length,
    estoque: skuRows.filter((r) => (r.quantity_stocked ?? 0) > 0).length,
  };

  const officialDoc = docs.find((d) => d.status === "OFFICIAL");

  async function createShipmentWithItems(
    shipmentNumber: string,
    modal: string,
    allocations: Array<{ importation_item_id: number; quantity: number }>,
  ) {
    setError("");
    const ship = await shipmentsApi.create({
      importation_id: importationId,
      shipment_number: shipmentNumber,
      modal,
    });
    for (const a of allocations) {
      await shipmentsApi.addItem(ship.id, {
        importation_item_id: a.importation_item_id,
        quantity_shipped: a.quantity,
      });
    }
    await reload();
  }

  if (loading) {
    return <LoadingState label="Carregando trâmite logístico..." />;
  }

  return (
    <div className="logistics-workflow">
      {error && <p className="error">{error}</p>}
      <LogisticsPhaseRail counts={phaseCounts} />
      <LogisticsSkuMatrix rows={skuRows} />

      <DispatchSection
        rows={skuRows}
        dispatchPending={dispatchPending}
        onCreateShipment={async (number, modal, allocations) => {
          try {
            await createShipmentWithItems(number, modal, allocations);
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro ao criar embarque");
          }
        }}
      />

      <ShipmentsSection
        shipments={shipments}
        itemsByShipment={itemsByShipment}
        skuRows={skuRows}
        onAddItem={async (shipmentId, itemId, qty) => {
          setError("");
          try {
            await shipmentsApi.addItem(shipmentId, {
              importation_item_id: itemId,
              quantity_shipped: qty,
            });
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro ao alocar item");
          }
        }}
        onChangeModal={async (shipmentId, newModal, comment) => {
          setError("");
          try {
            await shipmentsApi.changeModal(shipmentId, {
              new_modal: newModal,
              reason_code: "MODAL_CHANGE_URGENCY",
              comment,
            });
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro ao alterar modal");
          }
        }}
        onLoadHistory={(id) => shipmentsApi.modalHistory(id)}
      />

      <TransitSection
        shipments={shipments}
        onUpdate={async (shipmentId, data) => {
          setError("");
          try {
            await shipmentsApi.update(shipmentId, data);
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro ao atualizar embarque");
          }
        }}
      />

      <CustomsSection
        docs={docs}
        taxes={taxes}
        onCreateDoc={async (docType, docNumber) => {
          setError("");
          try {
            const staging = await customsApi.createDocument({
              importation_id: importationId,
              document_type: docType,
              document_number: docNumber,
              document_data_json: { source: "ui", staging: true },
            });
            await customsApi.approveDocument(staging.id, {
              official_data_json: { number: docNumber, approved_via: "ui" },
            });
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro ao registrar DI/DUIMP");
          }
        }}
        onCreateTax={async (taxType, amount) => {
          setError("");
          if (!officialDoc) {
            setError("Registre e aprove DI/DUIMP antes do imposto");
            return;
          }
          try {
            await customsApi.createTax({
              importation_id: importationId,
              customs_document_id: officialDoc.id,
              tax_type: taxType,
              amount,
              source_document_attachment_id: 1,
            });
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro ao registrar imposto");
          }
        }}
      />

      <EntrepostoSection
        importationId={importationId}
        rows={skuRows}
        movements={entreposto}
        onCreate={async (data) => {
          setError("");
          try {
            await stockApi.createEntrepostoMovement(data);
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro no entreposto");
          }
        }}
      />

      <NationalizationSection
        rows={skuRows}
        customsDocId={officialDoc?.id ?? null}
        onNationalize={async (itemId, qty) => {
          setError("");
          if (!officialDoc) return;
          try {
            await stockApi.createNationalization({
              importation_id: importationId,
              customs_document_id: officialDoc.id,
              items: [{ importation_item_id: itemId, quantity_nationalized: qty }],
            });
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro ao nacionalizar");
          }
        }}
      />

      <StockSection
        rows={skuRows}
        lcVersions={lcVersions}
        onStockEntry={async (itemId, qty, unitCost) => {
          setError("");
          try {
            const nats = await stockApi.listNationalizations(importationId);
            const nat = nats[0];
            if (!nat) {
              setError("Nacionalize antes da entrada em estoque");
              return;
            }
            await stockApi.createStockEntry({
              nationalization_id: nat.id,
              importation_item_id: itemId,
              quantity_received: qty,
              unit_cost_approved: unitCost || null,
            });
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro na entrada em estoque");
          }
        }}
        onCreateLc={async (method) => {
          setError("");
          try {
            await landedCostApi.createVersion({
              importation_id: importationId,
              version_type: lcVersions.length ? "FINAL" : "INITIAL",
              allocation_method: method,
            });
            await reload();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Erro no landed cost");
          }
        }}
      />
    </div>
  );
}
