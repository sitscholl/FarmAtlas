import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts'
import { useMemo, useState } from 'react'

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

type TooltipRow = {
  key: string
  label: string
  color: string
  value: number | null
  unit?: string
  digits?: number
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return '-'
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
      kc: lastPoint.kc ?? null,
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

function buildTooltipRows(point: ChartRow): TooltipRow[] {
  return [
    {
      key: 'soil_water_content',
      label: 'Bodenwassergehalt',
      color: '#0f172a',
      value: point.soil_water_content_observed ?? point.soil_water_content_forecast,
      unit: 'mm',
    },
    {
      key: 'precipitation',
      label: 'Niederschlag',
      color: '#0682b77d',
      value: point.precipitation ?? null,
      unit: 'mm',
    },
    {
      key: 'irrigation',
      label: 'Bewaesserung',
      color: '#259a057a',
      value: point.irrigation ?? null,
      unit: 'mm',
    },
    {
      key: 'evapotranspiration_negative',
      label: 'Evapotranspiration',
      color: '#f59e0b99',
      value:
        point.evapotranspiration_negative === null
          ? null
          : Math.abs(point.evapotranspiration_negative),
      unit: 'mm',
    },
    {
      key: 'kc',
      label: 'Kc',
      color: '#94a3b8',
      value: point.kc ?? null,
      digits: 2,
    },
  ]
}

export default function WaterBalanceChart({
  data,
  reservedForecastDays = 0,
}: WaterBalanceChartProps) {
  const displayData = extendChartRange(data, reservedForecastDays)
  const chartData = buildChartData(displayData)
  const hasEvapotranspiration = chartData.some(
    (point) => point.evapotranspiration_negative !== null,
  )
  const hasKc = chartData.some((point) => point.kc !== null && point.kc !== undefined)
  const hasForecast = chartData.some((point) => point.value_type === 'forecast')
  const today = getLocalIsoDate()
  const hasTodayMarker = chartData.some((point) => point.date === today)
  const latestObserved =
    [...data].reverse().find((point) => point.value_type !== 'forecast') ?? data[data.length - 1] ?? null
  const defaultActiveDate = latestObserved?.date ?? chartData[chartData.length - 1]?.date ?? null
  const [activeDate, setActiveDate] = useState<string | null>(defaultActiveDate)

  const activePoint = useMemo(() => {
    const fallbackPoint = chartData.find((point) => point.date === defaultActiveDate) ?? chartData[chartData.length - 1] ?? null
    if (activeDate === null) {
      return fallbackPoint
    }
    return chartData.find((point) => point.date === activeDate) ?? fallbackPoint
  }, [activeDate, chartData, defaultActiveDate])

  const activeRows = activePoint === null ? [] : buildTooltipRows(activePoint)

  if (data.length === 0 || activePoint === null) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
        No water-balance data available.
      </div>
    )
  }

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
        <div className="h-[320px] w-full min-w-[40rem] sm:h-[420px] sm:min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 12, right: 8, left: 0, bottom: 0 }}
              barCategoryGap="80%"
              onMouseMove={(state: unknown) => {
                const nextDate =
                  (state as { activeLabel?: string } | undefined)?.activeLabel ??
                  (state as { activePayload?: Array<{ payload?: ChartRow }> } | undefined)?.activePayload?.[0]?.payload?.date

                if (nextDate && nextDate !== activeDate) {
                  setActiveDate(nextDate)
                }
              }}
              onMouseLeave={() => {
                if (defaultActiveDate !== activeDate) {
                  setActiveDate(defaultActiveDate)
                }
              }}
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
              {hasKc ? (
                <YAxis
                  yAxisId="kc"
                  orientation="right"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickLine={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#cbd5e1' }}
                  width={36}
                  domain={[0, 'auto']}
                />
              ) : null}
              <ReferenceLine y={0} stroke="#64748b" strokeWidth={.5} />
              <ReferenceLine
                x={activePoint.date}
                stroke="#94a3b8"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
              {hasTodayMarker ? (
                <ReferenceLine
                  x={today}
                  stroke="#475569"
                  strokeDasharray="4 4"
                  label={{ value: 'Heute', position: 'top', fill: '#475569', fontSize: 11 }}
                />
              ) : null}
              <Legend wrapperStyle={{ paddingTop: 8, fontSize: '12px' }} />
              {hasKc ? (
                <Line
                  yAxisId="kc"
                  type="monotone"
                  dataKey="kc"
                  stroke="#94a3b8"
                  strokeWidth={1.5}
                  strokeOpacity={0.65}
                  dot={false}
                  activeDot={false}
                  connectNulls={false}
                  name="Kc"
                />
              ) : null}
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

      <div className="mt-3 border-t border-slate-100 pt-3">
        <p className="text-sm font-semibold text-slate-900">
          {activePoint.date}
        </p>
        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
          {activeRows.map((row) => (
            <div key={`${activePoint.date}-${row.key}`} className="flex items-center justify-between gap-3 border border-slate-100 bg-slate-50 px-3 py-2">
              <span className="flex items-center gap-2 text-slate-600">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: row.color }}
                />
                {row.label}
              </span>
              <span className="font-medium text-slate-900">
                {row.value === null ? '-' : `${formatNumber(row.value, row.digits ?? 1)}${row.unit ? ` ${row.unit}` : ''}`}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
