/** UX Foundation — façade (barrel). Exports públicos + primitives V0/VF. */

export { PageHeader, ContextBreadcrumb } from "./PageHeader";
export { KpiStrip } from "./KpiStrip";
export { StatusBadge } from "./StatusBadge";
export { MoneyDisplay, FxDisplay } from "./MoneyDisplay";
export { EmptyState, ErrorState, LoadingState } from "./Feedback";
export { FilterBar } from "./FilterBar";
export type { ActiveFilterChip } from "./FilterBar";
export { DetailDrawer } from "./DetailDrawer";
export { Button } from "./Button";
export { FilterChip } from "./FilterChip";
export { OperationalTable } from "./OperationalTable";
export {
  filterVisibleColumns,
  layoutModeFromWidth,
  type ColumnVisibility,
  type ColumnPriority,
  type LayoutMode,
  type OperationalColumnDef,
} from "./tableColumns";
export { ConfirmationModal } from "./ConfirmationModal";
export { EntityRef } from "./EntityRef";
export { RowLink } from "./RowLink";
export { SectionCard } from "./SectionCard";
export { SummaryGrid } from "./SummaryGrid";
export { FormField } from "./FormField";
export { TextInput } from "./TextInput";
export { SelectField } from "./SelectField";
export { MoneyInput, parseMoneyInput } from "./MoneyInput";
export { RateInput } from "./RateInput";
export { DateInput } from "./DateInput";
export { FileUpload } from "./FileUpload";
export { DocumentActions } from "./DocumentActions";
export { Notice } from "./Notice";
export { PaginationSummary } from "./PaginationSummary";
export { RowAction } from "./RowAction";
export { AuditDocumentsBlock } from "./AuditDocumentsBlock";
export type { AuditEntry, DocumentEntry } from "./AuditDocumentsBlock";
export type { SummaryItem } from "./SummaryGrid";
export type { SelectOption } from "./SelectField";
export {
  formatMoney,
  formatRate,
  formatDateOnly,
  formatDateTime,
  formatQuantity,
  compactQuantityWire,
  FORMAT_ABSENCE,
} from "./format";
export {
  statusLabel,
  statusSemantics,
  resolveStatus,
  type StatusEntity,
  type StatusSemantics,
} from "./statusLabels";
export {
  invoiceTypeLabel,
  pendencyLabel,
  formatPendencies,
  discountTypeLabel,
  cockpitAlertLabel,
  auditActionLabel,
  roleLabel,
} from "./domainLabels";
