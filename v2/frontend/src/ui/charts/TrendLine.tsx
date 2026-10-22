import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatRate } from "../format";
import { CHART_MARGIN, chartColors } from "./theme";

export function TrendLine({
  data,
  xKey,
  yKey,
  yLabel,
  height = 220,
  fractionDigits = 4,
}: {
  data: Array<Record<string, string | number>>;
  xKey: string;
  yKey: string;
  yLabel?: string;
  height?: number;
  fractionDigits?: number;
}) {
  const colors = chartColors();
  return (
    <div className="dash-chart" style={{ height }} data-testid="chart-trend">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={CHART_MARGIN}>
          <CartesianGrid stroke={colors.grid} vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: colors.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: colors.muted, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
            domain={["auto", "auto"]}
            tickFormatter={(v) => formatRate(v, Math.min(fractionDigits, 2))}
          />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: `1px solid ${colors.grid}` }}
            formatter={(value) => [formatRate(typeof value === "number" ? value : String(value), fractionDigits), yLabel || yKey]}
          />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke={colors.accent}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
