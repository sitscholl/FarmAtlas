import { type WaterBalanceSeriesPoint } from '../types/field'

type WaterBalanceChartProps = {
  data: WaterBalanceSeriesPoint[]
}

function buildPath(
  values: number[],
  width: number,
  height: number,
  minValue: number,
  maxValue: number,
) {
  if (values.length === 0) {
    return ''
  }

  const xStep = values.length === 1 ? 0 : width / (values.length - 1)
  const range = Math.max(maxValue - minValue, 1)

  return values
    .map((value, index) => {
      const x = index * xStep
      const y = height - ((value - minValue) / range) * height
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

export default function WaterBalanceChart({ data }: WaterBalanceChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
        No water-balance data available.
      </div>
    )
  }

  const width = 760
  const height = 280
  const storageValues = data.map((point) => point.soil_storage)
  const capacityValues = data.map((point) => point.field_capacity)
  const rawValues = data.map((point) =>
    point.readily_available_water === null
      ? point.field_capacity
      : point.field_capacity - point.readily_available_water,
  )
  const allValues = [...storageValues, ...capacityValues, ...rawValues]
  const minValue = Math.min(...allValues) * 0.92
  const maxValue = Math.max(...allValues) * 1.03

  const storagePath = buildPath(storageValues, width, height, minValue, maxValue)
  const capacityPath = buildPath(capacityValues, width, height, minValue, maxValue)
  const rawPath = buildPath(rawValues, width, height, minValue, maxValue)

  return (
    <div className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Water Balance
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">
            Soil Storage Trend
          </h2>
        </div>
        <div className="flex flex-wrap gap-4 text-sm text-slate-600">
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-sky-500" />
            Soil storage
          </span>
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-400" />
            Field capacity
          </span>
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
            RAW threshold
          </span>
        </div>
      </div>

      <div className="mt-6 overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-[280px] w-full min-w-[640px]"
          role="img"
          aria-label="Water balance line chart"
        >
          {[0, 1, 2, 3].map((gridLine) => {
            const y = (height / 3) * gridLine
            return (
              <line
                key={gridLine}
                x1="0"
                y1={y}
                x2={width}
                y2={y}
                stroke="#e2e8f0"
                strokeWidth="1"
              />
            )
          })}
          <path d={capacityPath} fill="none" stroke="#94a3b8" strokeDasharray="6 6" strokeWidth="2" />
          <path d={rawPath} fill="none" stroke="#f43f5e" strokeDasharray="4 5" strokeWidth="2" />
          <path d={storagePath} fill="none" stroke="#0ea5e9" strokeLinecap="round" strokeWidth="4" />
          {storageValues.map((value, index) => {
            const x = storageValues.length === 1 ? width / 2 : (width / (storageValues.length - 1)) * index
            const y = height - ((value - minValue) / Math.max(maxValue - minValue, 1)) * height
            return (
              <circle
                key={data[index].date}
                cx={x}
                cy={y}
                fill={data[index].below_raw ? '#e11d48' : '#0ea5e9'}
                r="3.5"
              />
            )
          })}
        </svg>
      </div>

      <div className="mt-4 grid gap-3 text-sm text-slate-500 sm:grid-cols-3">
        <p>
          From <span className="font-medium text-slate-700">{data[0].date}</span>
        </p>
        <p>
          To <span className="font-medium text-slate-700">{data[data.length - 1].date}</span>
        </p>
        <p>
          Latest storage{' '}
          <span className="font-medium text-slate-700">
            {data[data.length - 1].soil_storage.toFixed(1)} mm
          </span>
        </p>
      </div>
    </div>
  )
}
