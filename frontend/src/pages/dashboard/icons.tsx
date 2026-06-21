// Ícones SVG inline reutilizados no painel (stroke = currentColor).
type IconProps = { className?: string };

function svg(path: React.ReactNode, key: string) {
  return function Icon({ className }: IconProps) {
    return (
      <svg
        className={className}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        data-icon={key}
      >
        {path}
      </svg>
    );
  };
}

export const DollarIcon = svg(
  <>
    <path d="M12 1v22" />
    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
  </>,
  "dollar"
);

export const CalendarIcon = svg(
  <>
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M3 9h18M8 3v4M16 3v4" />
  </>,
  "calendar"
);

export const WarehouseIcon = svg(
  <>
    <path d="M3 9l9-6 9 6v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <path d="M9 21V12h6v9" />
  </>,
  "warehouse"
);

export const AlertIcon = svg(
  <>
    <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
    <path d="M12 9v4M12 17h.01" />
  </>,
  "alert"
);

export const TruckIcon = svg(
  <>
    <path d="M3 7h13l4 4v6H3z" />
    <circle cx="7" cy="17" r="2" />
    <circle cx="17" cy="17" r="2" />
  </>,
  "truck"
);

export const ShipIcon = svg(
  <>
    <path d="M3 14l9-3 9 3-2 6H5z" />
    <path d="M12 11V4l5 2" />
  </>,
  "ship"
);

export const PlaneIcon = svg(
  <path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z" />,
  "plane"
);

export const BarsIcon = svg(
  <path d="M4 19V5M4 19h16M8 16v-5M12 16V8M16 16v-3" />,
  "bars"
);

export const ClockIcon = svg(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </>,
  "clock"
);

export const GearIcon = svg(
  <>
    <path d="M12 4v4M12 16v4M4 12h4M16 12h4" />
    <circle cx="12" cy="12" r="3" />
  </>,
  "gear"
);

export const DotsIcon = svg(
  <>
    <circle cx="12" cy="5" r="1" />
    <circle cx="12" cy="12" r="1" />
    <circle cx="12" cy="19" r="1" />
  </>,
  "dots"
);

export const PlusIcon = svg(<path d="M12 5v14M5 12h14" />, "plus");

export const ExportIcon = svg(
  <>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="M7 10l5 5 5-5" />
    <path d="M12 15V3" />
  </>,
  "export"
);
