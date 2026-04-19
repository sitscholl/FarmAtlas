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
import { useEffect, useState } from 'react'

import { type WaterBalanceSeriesPoint } from '../types/generated/api'

type WaterBalanceChartProps = {
  data: WaterBalanceSeriesPoint[]
  reservedForecastDays?: number
}

type ChartRow = WaterBalanceSeriesPoint & {
  raw_threshold: number | null
  evapotranspiration_negative: number | null
  soil_water_content_observed: number | null
  soil_water_content_forecast: number | null
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

function getLocalIsoDate() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDaysToIsoDate(isoDate: string, days: number) {
  const date = new Date(`${isoDate}T00:00:00`)
  date.setDate(date.getDate() + days)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function extendChartRange(
  data: WaterBalanceSeriesPoint[],
  reservedForecastDays: number,
): WaterBalanceSeriesPoint[] {
  if (data.length === 0 || reservedForecastDays <= 0) {
    return data
  }

  const today = getLocalIsoDate()
  const reservedEndDate = addDaysToIsoDate(today, reservedForecastDays)
  const lastDate = data[data.length - 1]?.date

  if (!lastDate || lastDate >= reservedEndDate) {
    return data
  }

  const paddedData = [...data]
  const lastPoint = data[data.length - 1]
  let nextDate = addDaysToIsoDate(lastDate, 1)
  while (nextDate <= reservedEndDate) {
    paddedData.push({
      date: nextDate,
      precipitation: 0,
      irrigation: 0,
      evapotranspiration: 0,
      incoming: 0,
      net: 0,
      soil_water_content: lastPoint.soil_water_content,
      available_water_storage: lastPoint.available_water_storage,
      water_deficit: lastPoint.water_deficit,
      readily_available_water: lastPoint.readily_available_water,
      safe_ratio: null,
      below_raw: null,
      value_type: null,
      model: null,
    })
    nextDate = addDaysToIsoDate(nextDate, 1)
  }

  return paddedData
}

function buildChartData(data: WaterBalanceSeriesPoint[]): ChartRow[] {
  return data.map((point, index) => {
    const nextPoint = data[index + 1]
    const forecastStartsNext = nextPoint?.value_type === 'forecast'

    return {
      ...point,
      raw_threshold:
        point.readily_available_water === null
          ? null
          : point.available_water_storage - point.readily_available_water,
      evapotranspiration_negative:
        point.evapotranspiration === null || point.evapotranspiration === undefined
          ? null
          : -Math.abs(point.evapotranspiration),
      soil_water_content_observed:
        point.value_type === 'forecast' ? null : point.soil_water_content,
      soil_water_content_forecast:
        point.value_type === 'forecast' || forecastStartsNext
          ? point.soil_water_content
          : null,
    }
  })
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
      entry.dataKey !== 'available_water_storage' &&
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

export default function WaterBalanceChart({
  data,
  reservedForecastDays = 0,
}: WaterBalanceChartProps) {
  const [showTooltip, setShowTooltip] = useState(true)

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return
    }

    const mediaQuery = window.matchMedia('(max-width: 767px), (pointer: coarse)')
    const update = () => setShowTooltip(!mediaQuery.matches)

    update()
    mediaQuery.addEventListener('change', update)
    return () => mediaQuery.removeEventListener('change', update)
  }, [])

  if (data.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
        No water-balance data available.
      </div>
    )
  }

  const displayData = extendChartRange(data, reservedForecastDays)
  const chartData = buildChartData(displayData)
  const hasEvapotranspiration = chartData.some(
    (point) => point.evapotranspiration_negative !== null,
  )
  const hasForecast = chartData.some((point) => point.value_type === 'forecast')
  const today = getLocalIsoDate()
  const hasTodayMarker = chartData.some((point) => point.date === today)
  const latestObserved =
    [...data].reverse().find((point) => point.value_type !== 'forecast') ?? data[data.length - 1]

  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-slate-200/80 bg-white/90 p-3 shadow-sm sm:rounded-3xl sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Wasserbilanz
          </p>
        </div>
      </div>

      <div className="mt-4 overflow-x-auto sm:mt-6">
        <div className="h-[320px] min-w-[40rem] sm:h-[420px] sm:min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 12, right: 8, left: 0, bottom: 0 }}
              barCategoryGap="80%"
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickLine={{ fill: '#64748b' }}
                axisLine={{ stroke: '#cbd5e1' }}
                minTickGap={24}
                height={36}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickLine={{ fill: '#64748b' }}
                axisLine={{ stroke: '#cbd5e1' }}
                width={36}
              />
              <ReferenceLine y={0} stroke="#64748b" strokeWidth={.5} />
              {hasTodayMarker ? (
                <ReferenceLine
                  x={today}
                  stroke="#475569"
                  strokeDasharray="4 4"
                  label={{ value: 'Heute', position: 'top', fill: '#475569', fontSize: 11 }}
                />
              ) : null}
              {showTooltip ? <Tooltip content={<TooltipContent />} /> : null}
              <Legend wrapperStyle={{ paddingTop: 8, fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="soil_water_content_observed"
                stroke="#0f172a"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5 }}
                connectNulls={false}
                name="Bodenwassergehalt"
              />
              {hasForecast ? (
                <Line
                  type="monotone"
                  dataKey="soil_water_content_forecast"
                  stroke="#0f172a"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  dot={false}
                  activeDot={{ r: 5 }}
                  connectNulls={false}
                  name="Bodenwassergehalt Prognose"
                  legendType="none"
                />
              ) : null}
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
                dataKey="available_water_storage"
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
            {formatNumber(latestObserved.soil_water_content)} mm
          </span>
        </p>
      </div>
    </div>
  )
}
