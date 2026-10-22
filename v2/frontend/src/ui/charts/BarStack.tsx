import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatChartTick, formatMoney, formatQuantity } from "../format";
import { CHART_MARGIN, chartColors } from "./theme";

export type StackSeries = { key: string; label: string; color?: string };
export type ChartValueKind = "money" | "quantity";

export function BarStack({
  data,
  xKey,
  series,
  height = 220,
  stacked = true,
  valueKind = "money",
}: {
  data: Array<Record<string, string | number>>;
  xKey: string;
  series: StackSeries[];
  height?: number;
  stacked?: boolean;
  valueKind?: ChartValueKind;
}) {
  const colors = chartColors();
  const palette = [colors.overdue, colors.m0, colors.m1, colors.m2, colors.week, colors.rest];
  return (
    <div className="dash-chart" style={{ height }} data-testid="chart-bar-stack">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={CHART_MARGIN} barCategoryGap="28%">
          <CartesianGrid stroke={colors.grid} vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: colors.muted, fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: colors.muted, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={56}
            tickFormatter={(v) => formatChartTick(v)}
          />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: `1px solid ${colors.grid}` }}
            formatter={(value, name) => {
              const seriesLabel = series.find((s) => s.key === name)?.label ?? String(name);
              const n = typeof value === "number" ? value : Number(value);
              if (valueKind === "money") {
                const currency = /^[A-Z]{3}$/.test(seriesLabel) ? seriesLabel : undefined;
                const text = formatMoney(Number.isFinite(n) ? n : String(value), currency);
                return [text, currency ? " " : seriesLabel];
              }
              return [formatQuantity(Number.isFinite(n) ? n : String(value)), seriesLabel];
            }}
          />
          <Legend formatter={(value) => series.find((s) => s.key === value)?.label ?? value} />
          {series.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.key}
              stackId={stacked ? "a" : undefined}
              fill={s.color || palette[i % palette.length]}
              radius={i === series.length - 1 ? [4, 4, 0, 0] : 0}
              maxBarSize={36}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
