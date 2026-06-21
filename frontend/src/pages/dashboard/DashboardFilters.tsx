import {
  MODAL_OPTIONS,
  PERIOD_OPTIONS,
  VIEW_OPTIONS,
  type ModalFilter,
  type PeriodFilter,
  type DashboardView,
} from "../../hooks/useDashboardFilters";
import { GearIcon } from "./icons";

interface Props {
  view: DashboardView;
  modal: ModalFilter;
  period: PeriodFilter;
  onView: (v: DashboardView) => void;
  onModal: (m: ModalFilter) => void;
  onPeriod: (p: PeriodFilter) => void;
  onCustomize: () => void;
}

export function DashboardFilters({
  view,
  modal,
  period,
  onView,
  onModal,
  onPeriod,
  onCustomize,
}: Props) {
  return (
    <div className="filterbar">
      <span className="filterbar__lbl">Ver</span>
      {VIEW_OPTIONS.map((opt) => (
        <button
          key={opt.id}
          className={`chip${view === opt.id ? " chip--on" : ""}`}
          onClick={() => onView(opt.id)}
        >
          {opt.label}
        </button>
      ))}

      <div className="seg" style={{ marginLeft: 8 }}>
        {MODAL_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            className={modal === opt.id ? "on" : ""}
            onClick={() => onModal(opt.id)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="filterbar__spacer" />

      <div className="seg">
        {PERIOD_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            className={period === opt.id ? "on" : ""}
            onClick={() => onPeriod(opt.id)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <button className="cfgbtn" onClick={onCustomize}>
        <GearIcon className="ico" /> Personalizar
      </button>
    </div>
  );
}
