import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export type FieldStatisticBarChartPoint = {
  year: number
  value: number | null
}

type FieldStatisticBarChartProps = {
  title: string
  data: FieldStatisticBarChartPoint[]
  selectedYear: number | null
  digits?: number
}

const BAR_COLOR = '#2563eb'
const SELECTED_BAR_COLOR = '#f59e0b'

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '-'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

export default function FieldStatisticBarChart({
  title,
  data,
  selectedYear,
  digits = 1,
}: FieldStatisticBarChartProps) {
  const hasData = data.some((point) => point.value !== null)

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        <span className="text-xs font-medium text-slate-500">Jahr</span>
      </div>

      {hasData ? (
        <div className="mt-4 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="year"
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickLine={{ stroke: '#cbd5e1' }}
                axisLine={{ stroke: '#cbd5e1' }}
                minTickGap={16}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickFormatter={(value) => formatNumber(Number(value), digits)}
                tickLine={{ stroke: '#cbd5e1' }}
                axisLine={{ stroke: '#cbd5e1' }}
                width={48}
              />
              <Tooltip
                cursor={{ fill: '#f8fafc' }}
                formatter={(value) => [
                  formatNumber(Number(value), digits),
                  title,
                ]}
                labelFormatter={(label) => `Jahr ${label}`}
                contentStyle={{
                  borderColor: '#e2e8f0',
                  borderRadius: 8,
                  boxShadow: '0 8px 20px rgba(15, 23, 42, 0.12)',
                  color: '#0f172a',
                  fontSize: 12,
                }}
              />
              <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={42}>
                {data.map((point) => (
                  <Cell
                    key={point.year}
                    fill={point.year === selectedYear ? SELECTED_BAR_COLOR : BAR_COLOR}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-4 flex h-64 items-center justify-center border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
          Keine Daten
        </div>
      )}
    </div>
  )
}
