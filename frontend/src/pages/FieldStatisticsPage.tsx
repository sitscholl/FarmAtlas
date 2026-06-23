import { useCallback, useEffect, useMemo, useState } from 'react'

import api from '../api'
import DataTable, {
  type DataTableColumn,
  type DataTableSummaryCell,
} from '../components/DataTable'
import type {
  FieldStatisticsMetric,
  FieldStatisticsResponse,
  FieldStatisticsRow,
} from '../types/generated/api'

const COUNT_METRIC_CODES = new Set([
  'count.before_hand_thinning',
  'count.after_hand_thinning',
])

const YEARLY_METRIC_CODES = [
  'thinning_hours',
  'yield_kg',
  'filled_boxes',
  'harvest_hours',
  'revenue',
] as const

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function getMetric(
  row: FieldStatisticsRow,
  metricCode: string,
): FieldStatisticsMetric | undefined {
  return row.metrics?.[metricCode]
}

function getDisplayedMetricValue(
  metric: FieldStatisticsMetric | undefined,
  metricCode: string,
  perHectare: boolean,
) {
  if (metric === undefined) {
    return null
  }
  return perHectare && !COUNT_METRIC_CODES.has(metricCode)
    ? metric.value_per_hectare
    : metric.value
}

function metricDigits(metricCode: string) {
  if (metricCode === 'filled_boxes') {
    return 0
  }
  if (metricCode === 'revenue' || metricCode === 'yield_kg') {
    return 0
  }
  return 1
}

export default function FieldStatisticsPage() {
  const [statistics, setStatistics] = useState<FieldStatisticsResponse | null>(null)
  const [selectedYear, setSelectedYear] = useState('')
  const [perHectare, setPerHectare] = useState(false)
  const [selectedRowKey, setSelectedRowKey] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchStatistics = async () => {
      setIsLoading(true)
      try {
        const response = await api.get<FieldStatisticsResponse>('/production/field-statistics', {
          params: selectedYear === '' ? undefined : { season_year: Number(selectedYear) },
        })
        setStatistics(response.data)
        setErrorMessage(null)
        if (selectedYear === '' && response.data.season_year > 0) {
          setSelectedYear(String(response.data.season_year))
        }
      } catch (error) {
        console.error('Error fetching field statistics', error)
        setStatistics(null)
        setErrorMessage('Die Feldstatistik konnte nicht geladen werden.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchStatistics()
  }, [selectedYear])

  const yearOptions = useMemo(() => {
    const years = new Set(statistics?.available_years ?? [])
    if (selectedYear !== '') {
      years.add(Number(selectedYear))
    }
    return [...years].sort((left, right) => right - left)
  }, [selectedYear, statistics])

  const rows = useMemo(
    () =>
      [...(statistics?.rows ?? [])].sort((left, right) => {
        const fieldCompare = left.field_name.localeCompare(right.field_name, 'de-DE')
        return fieldCompare !== 0
          ? fieldCompare
          : left.planting_name.localeCompare(right.planting_name, 'de-DE')
      }),
    [statistics],
  )

  const metricCell = useCallback(
    (metricCode: string) => (row: FieldStatisticsRow) =>
      formatNumber(
        getDisplayedMetricValue(getMetric(row, metricCode), metricCode, perHectare),
        metricDigits(metricCode),
      ),
    [perHectare],
  )

  const columns = useMemo<DataTableColumn<FieldStatisticsRow>[]>(
    () => [
      {
        id: 'planting',
        header: 'Pflanzung',
        cell: (row) => (
          <div>
            <div className="font-semibold text-slate-900">{row.planting_name}</div>
            <div className="text-xs text-slate-500">{row.field_name}</div>
          </div>
        ),
      },
      {
        id: 'count_before',
        header: 'Vor Handausdünnung',
        cell: metricCell('count.before_hand_thinning'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'count_after',
        header: 'Nach Handausdünnung',
        cell: metricCell('count.after_hand_thinning'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'thinning_hours',
        header: 'Zupfen [h]',
        cell: metricCell('thinning_hours'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'yield_kg',
        header: 'Ertrag [kg]',
        cell: metricCell('yield_kg'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'filled_boxes',
        header: 'Kisten',
        cell: metricCell('filled_boxes'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'harvest_hours',
        header: 'Ernte [h]',
        cell: metricCell('harvest_hours'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'revenue',
        header: 'Erlös [€]',
        cell: metricCell('revenue'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
    ],
    [metricCell],
  )

  const summaryCells = useMemo<DataTableSummaryCell<FieldStatisticsRow>[]>(() => {
    if (statistics === null) {
      return []
    }

    const summaryMetric = (metricCode: string) =>
      formatNumber(
        getDisplayedMetricValue(statistics.summary.metrics?.[metricCode], metricCode, perHectare),
        metricDigits(metricCode),
      )

    return [
      {
        columnId: 'planting',
        content: statistics.summary.label,
      },
      {
        columnId: 'count_before',
        content: summaryMetric('count.before_hand_thinning'),
        className: 'text-right tabular-nums',
      },
      {
        columnId: 'count_after',
        content: summaryMetric('count.after_hand_thinning'),
        className: 'text-right tabular-nums',
      },
      ...YEARLY_METRIC_CODES.map((metricCode) => ({
        columnId: metricCode,
        content: summaryMetric(metricCode),
        className: 'text-right tabular-nums',
      })),
    ]
  }, [perHectare, statistics])

  return (
    <section className="w-full max-w-7xl">
      <div className="px-3 py-4 sm:px-6 sm:py-6 lg:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Produktion
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              Feldstatistik
            </h1>
          </div>

          <div className="flex flex-wrap items-end gap-4">
            <label className="block min-w-36">
              <select
                value={selectedYear}
                onChange={(event) => setSelectedYear(event.target.value)}
                className="mt-2 w-full border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
              >
                {yearOptions.length === 0 ? (
                  <option value="">Keine Daten</option>
                ) : (
                  yearOptions.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))
                )}
              </select>
            </label>

            <label className="flex items-center gap-3 border border-slate-200 bg-white px-4 py-2.5">
              <input
                type="checkbox"
                checked={perHectare}
                onChange={(event) => setPerHectare(event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
              />
              <span className="text-sm font-medium text-slate-700">pro ha</span>
            </label>
          </div>
        </div>

        {errorMessage ? (
          <div className="mt-6 border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <div className="mt-6">
          {isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
              Feldstatistik wird geladen...
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={rows}
              getRowKey={(row) => row.planting_id}
              emptyMessage="Keine Feldstatistik vorhanden."
              summaryCells={summaryCells}
              selectedRowKey={selectedRowKey}
              onRowSelect={(row) => setSelectedRowKey(row?.planting_id ?? null)}
            />
          )}
        </div>
      </div>
    </section>
  )
}
