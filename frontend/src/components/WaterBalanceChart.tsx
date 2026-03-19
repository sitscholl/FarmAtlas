import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { type WaterBalanceSeriesPoint } from '../types/field'

type WaterBalanceChartProps = {
  data: WaterBalanceSeriesPoint[]
}

type ChartRow = WaterBalanceSeriesPoint & {
  raw_threshold: number | null
  evapotranspiration_negative: number | null
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function buildChartData(data: WaterBalanceSeriesPoint[]): ChartRow[] {
  return data.map((point) => ({
    ...point,
    raw_threshold:
      point.readily_available_water === null
        ? null
        : point.field_capacity - point.readily_available_water,
    evapotranspiration_negative:
      point.evapotranspiration === null || point.evapotranspiration === undefined
        ? null
        : -Math.abs(point.evapotranspiration),
  }))
}

function TooltipContent({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ dataKey?: string; value?: number; color?: string; name?: string }>
  label?: string
}) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const rows = payload.filter(
    (entry) =>
      entry.value !== undefined &&
      entry.dataKey !== 'field_capacity' &&
      entry.dataKey !== 'raw_threshold',
  )

  if (rows.length === 0) {
    return null
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/95 px-4 py-3 shadow-lg">
      <p className="text-sm font-semibold text-slate-900">{label}</p>
      <div className="mt-3 space-y-2">
        {rows.map((entry) => (
          <div key={`${label}-${entry.dataKey}`} className="flex items-center justify-between gap-4 text-sm">
            <span className="flex items-center gap-2 text-slate-600">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: entry.color ?? '#94a3b8' }}
              />
              {entry.name}
            </span>
            <span className="font-medium text-slate-900">
              {formatNumber(
                entry.dataKey === 'evapotranspiration_negative'
                  ? Math.abs(entry.value ?? 0)
                  : entry.value,
              )} mm
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function WaterBalanceChart({ data }: WaterBalanceChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
        No water-balance data available.
      </div>
    )
  }

  const chartData = buildChartData(data)
  const hasEvapotranspiration = chartData.some(
    (point) => point.evapotranspiration_negative !== null,
  )

  return (
    <div className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Wasserbilanz
          </p>
        </div>
      </div>

      <div className="mt-6 h-[420px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 16, right: 18, left: 8, bottom: 12 }}
            barCategoryGap="80%"
          >
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#64748b', fontSize: 12 }}
              tickLine={{ fill: '#64748b' }}
              axisLine={{ stroke: '#cbd5e1' }}
              label={{ value: 'Datum', position: 'insideBottom', offset: -8, fill: '#64748b' }}
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 12 }}
              tickLine={{ fill: '#64748b' }}
              axisLine={{ stroke: '#cbd5e1' }}
              label={{ value: 'Wassergehalt (mm)', angle: -90, fill: '#64748b' }}
            />
            <ReferenceLine y={0} stroke="#64748b" strokeWidth={.5} />
            <Tooltip content={<TooltipContent />} />
            <Legend wrapperStyle={{ paddingTop: 12 }} />
            <Line
              type="monotone"
              dataKey="soil_water_content"
              stroke="#0f172a"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              name="Bodenwassergehalt"
            />
            <Bar
              dataKey="precipitation"
              stackId="incoming"
              fill="#0682b77d"
              name="Niederschlag"
              maxBarSize={10}
            />
            <Bar
              dataKey="irrigation"
              stackId="incoming"
              fill="#259a057a"
              name="Bewaesserung"
              maxBarSize={10}
            />
            {hasEvapotranspiration ? (
              <Bar
                dataKey="evapotranspiration_negative"
                fill="#f59e0b99"
                name="Evapotranspiration"
                maxBarSize={10}
              />
            ) : null}
            <Line
              type="monotone"
              dataKey="field_capacity"
              stroke="#94a3b8"
              strokeDasharray="6 6"
              strokeWidth={1}
              dot={false}
              activeDot={false}
              legendType="none"
            />
            <Line
              type="monotone"
              dataKey="raw_threshold"
              stroke="#f43f5e"
              strokeDasharray="4 5"
              strokeWidth={1}
              dot={false}
              activeDot={false}
              connectNulls={false}
              legendType="none"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 grid justify-items-center gap-3 text-center text-sm text-slate-500 sm:grid-cols-3">
        <p>
          From <span className="font-medium text-slate-700">{data[0].date}</span>
        </p>
        <p>
          To <span className="font-medium text-slate-700">{data[data.length - 1].date}</span>
        </p>
        <p>
          Latest storage{' '}
          <span className="font-medium text-slate-700">
            {formatNumber(data[data.length - 1].soil_water_content)} mm
          </span>
        </p>
      </div>
    </div>
  )
}
