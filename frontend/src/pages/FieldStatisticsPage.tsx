import { useCallback, useEffect, useMemo, useState } from 'react'

import api from '../api'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
  type DataTableSummaryCell,
} from '../components/DataTable'
import FieldStatisticBarChart from '../components/FieldStatisticBarChart'
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

const CHART_METRICS = [
  { metricCode: 'count.before_hand_thinning' },
  { metricCode: 'count.after_hand_thinning' },
  { metricCode: 'thinning_hours' },
  { metricCode: 'yield_kg' },
  { metricCode: 'filled_boxes' },
  { metricCode: 'harvest_hours' },
  { metricCode: 'revenue' },
] as const

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return '-'
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

function metricTitle(metricCode: string, perHectare: boolean) {
  switch (metricCode) {
    case 'count.before_hand_thinning':
      return 'Zupfen'
    case 'count.after_hand_thinning':
      return 'Ernte'
    case 'thinning_hours':
      return perHectare ? 'Zupfen [h/ha]' : 'Zupfen [h]'
    case 'yield_kg':
      return perHectare ? 'Ertrag [kg/ha]' : 'Ertrag [kg]'
    case 'filled_boxes':
      return perHectare ? 'Kisten [n/ha]' : 'Kisten [n]'
    case 'harvest_hours':
      return perHectare ? 'Ernte [h/ha]' : 'Ernte [h]'
    case 'revenue':
      return perHectare ? 'Erlös [€/ha]' : 'Erlös [€]'
    default:
      return metricCode
  }
}

function getHistoricalSummaryMetric(
  visibleRows: FieldStatisticsRow[],
  metricCode: string,
  year: number,
  perHectare: boolean,
) {
  const rowsForYear = visibleRows
    .map((row) => {
      const historyEntry = row.history?.find((entry) => entry.season_year === year)
      if (historyEntry === undefined || historyEntry.active === false) {
        return null
      }

      return {
        metric: historyEntry.metrics?.[metricCode],
        area: historyEntry.area ?? row.area,
        treeCount: historyEntry.tree_count === undefined ? row.tree_count : historyEntry.tree_count,
      }
    })
    .filter((row): row is {
      metric: FieldStatisticsMetric | undefined
      area: number
      treeCount: number | null | undefined
    } => row !== null)

  const rowsWithMetric = rowsForYear
    .map((row) => ({
      value: row.metric?.value,
      area: row.area,
      treeCount: row.treeCount,
    }))
    .filter((row): row is { value: number; area: number; treeCount: number | null | undefined } =>
      row.value !== null && row.value !== undefined,
    )

  if (COUNT_METRIC_CODES.has(metricCode)) {
    const weightedRows = rowsWithMetric.filter((row) => (row.treeCount ?? row.area) > 0)
    if (weightedRows.length > 0) {
      const totalWeight = weightedRows.reduce((sum, row) => sum + (row.treeCount ?? row.area), 0)
      return weightedRows.reduce(
        (sum, row) => sum + row.value * (row.treeCount ?? row.area),
        0,
      ) / totalWeight
    }

    return rowsWithMetric.length === 0
      ? null
      : rowsWithMetric.reduce((sum, row) => sum + row.value, 0) / rowsWithMetric.length
  }

  const totalValue = rowsWithMetric.reduce((sum, row) => sum + row.value, 0)
  if (rowsWithMetric.length === 0) {
    return null
  }
  if (!perHectare) {
    return totalValue
  }

  const totalArea = rowsForYear.reduce((sum, row) => sum + row.area, 0)
  return totalArea <= 0 ? null : totalValue / (totalArea / 10000)
}

export default function FieldStatisticsPage() {
  const [statistics, setStatistics] = useState<FieldStatisticsResponse | null>(null)
  const [selectedYear, setSelectedYear] = useState('')
  const [perHectare, setPerHectare] = useState(false)
  const [selectedRowKey, setSelectedRowKey] = useState<number | null>(null)
  const [filters, setFilters] = useState({
    query: '',
    group: '',
    variety: '',
  })
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

  const groupOptions = useMemo(
    () =>
      [...new Set(rows.map((row) => row.field_group).filter(Boolean))]
        .sort((left, right) => left.localeCompare(right, 'de-DE'))
        .map((group) => ({ label: group, value: group })),
    [rows],
  )

  const varietyOptions = useMemo(
    () =>
      [...new Set(rows.map((row) => row.planting_name).filter(Boolean))]
        .sort((left, right) => left.localeCompare(right, 'de-DE'))
        .map((variety) => ({ label: variety, value: variety })),
    [rows],
  )

  const tableFilters = useMemo<DataTableFilter[]>(
    () => [
      {
        id: 'query',
        label: 'Suche',
        type: 'text',
        value: filters.query,
        placeholder: 'Anlage, Sorte oder Gruppe',
      },
      {
        id: 'group',
        label: 'Gruppe',
        type: 'select',
        value: filters.group,
        options: [
          { label: 'Alle', value: '' },
          ...groupOptions,
        ],
      },
      {
        id: 'variety',
        label: 'Sorte',
        type: 'select',
        value: filters.variety,
        options: [
          { label: 'Alle', value: '' },
          ...varietyOptions,
        ],
      },
    ],
    [filters, groupOptions, varietyOptions],
  )

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return rows.filter((row) => {
      const matchesQuery =
        normalizedQuery === '' ||
        [row.field_name, row.planting_name, row.field_group]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery)

      const matchesGroup = filters.group === '' || row.field_group === filters.group
      const matchesVariety = filters.variety === '' || row.planting_name === filters.variety

      return matchesQuery && matchesGroup && matchesVariety
    })
  }, [filters, rows])

  const selectedYearNumber = selectedYear === '' ? null : Number(selectedYear)

  const chartYears = useMemo(() => {
    const years = new Set(statistics?.history_years ?? [])
    if (selectedYearNumber !== null) {
      years.add(selectedYearNumber)
    }
    return [...years].sort((left, right) => left - right)
  }, [selectedYearNumber, statistics])

  const chartRows = useMemo(() => {
    if (selectedRowKey === null) {
      return filteredRows
    }

    const selectedRow = filteredRows.find((row) => row.planting_id === selectedRowKey)
    return selectedRow === undefined ? filteredRows : [selectedRow]
  }, [filteredRows, selectedRowKey])

  const charts = useMemo(
    () =>
      CHART_METRICS.map((metric) => ({
        ...metric,
        title: metricTitle(metric.metricCode, perHectare),
        data: chartYears.map((year) => ({
          year,
          value: getHistoricalSummaryMetric(chartRows, metric.metricCode, year, perHectare),
        })),
      })),
    [chartRows, chartYears, perHectare],
  )

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
    setSelectedRowKey(null)
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      group: '',
      variety: '',
    })
    setSelectedRowKey(null)
  }

  const metricCell = useCallback(
    (metricCode: string) => (row: FieldStatisticsRow) =>
      formatNumber(
        getDisplayedMetricValue(getMetric(row, metricCode), metricCode, perHectare),
        metricDigits(metricCode),
      ),
    [perHectare],
  )

  const metricSortValue = useCallback(
    (metricCode: string) => (row: FieldStatisticsRow) =>
      getDisplayedMetricValue(getMetric(row, metricCode), metricCode, perHectare),
    [perHectare],
  )

  const columns = useMemo<DataTableColumn<FieldStatisticsRow>[]>(
    () => [
      {
        id: 'planting',
        header: 'Pflanzung',
        cell: (row) => (
          <div>
            <div className="font-semibold text-slate-900">{row.field_name}</div>
            <div className="text-xs text-slate-500">{row.planting_name}</div>
          </div>
        ),
        sortValue: (row) => `${row.field_name} ${row.planting_name}`,
      },
      {
        id: 'count_before',
        header: 'Zupfen',
        cell: metricCell('count.before_hand_thinning'),
        sortValue: metricSortValue('count.before_hand_thinning'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'count_after',
        header: 'Ernte',
        cell: metricCell('count.after_hand_thinning'),
        sortValue: metricSortValue('count.after_hand_thinning'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'thinning_hours',
        header: metricTitle('thinning_hours', perHectare),
        cell: metricCell('thinning_hours'),
        sortValue: metricSortValue('thinning_hours'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'yield_kg',
        header: metricTitle('yield_kg', perHectare),
        cell: metricCell('yield_kg'),
        sortValue: metricSortValue('yield_kg'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'filled_boxes',
        header: metricTitle('filled_boxes', perHectare),
        cell: metricCell('filled_boxes'),
        sortValue: metricSortValue('filled_boxes'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'harvest_hours',
        header: metricTitle('harvest_hours', perHectare),
        cell: metricCell('harvest_hours'),
        sortValue: metricSortValue('harvest_hours'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
      {
        id: 'revenue',
        header: metricTitle('revenue', perHectare),
        cell: metricCell('revenue'),
        sortValue: metricSortValue('revenue'),
        cellClassName: 'text-right tabular-nums',
        headerClassName: 'text-right',
      },
    ],
    [metricCell, metricSortValue, perHectare],
  )

  const getFilteredSummaryMetric = useCallback(
    (visibleRows: FieldStatisticsRow[], metricCode: string) => {
      const rowsWithMetric = visibleRows
        .map((row) => ({
          value: getMetric(row, metricCode)?.value,
          area: row.area,
          treeCount: row.tree_count,
        }))
        .filter((row): row is { value: number; area: number; treeCount: number | null | undefined } =>
          row.value !== null && row.value !== undefined,
        )

      if (COUNT_METRIC_CODES.has(metricCode)) {
        const weightedRows = rowsWithMetric.filter((row) => (row.treeCount ?? row.area) > 0)
        if (weightedRows.length > 0) {
          const totalWeight = weightedRows.reduce((sum, row) => sum + (row.treeCount ?? row.area), 0)
          return weightedRows.reduce(
            (sum, row) => sum + row.value * (row.treeCount ?? row.area),
            0,
          ) / totalWeight
        }
        return rowsWithMetric.length === 0
          ? null
          : rowsWithMetric.reduce((sum, row) => sum + row.value, 0) / rowsWithMetric.length
      }

      const totalValue = rowsWithMetric.reduce((sum, row) => sum + row.value, 0)
      if (!perHectare) {
        return rowsWithMetric.length === 0 ? null : totalValue
      }

      const totalArea = visibleRows.reduce((sum, row) => sum + row.area, 0)
      return totalArea <= 0 ? null : totalValue / (totalArea / 10000)
    },
    [perHectare],
  )

  const summaryCells = useMemo<DataTableSummaryCell<FieldStatisticsRow>[]>(() => {
    if (statistics === null) {
      return []
    }

    return [
      {
        columnId: 'planting',
        content: (visibleRows) =>
          visibleRows.length === rows.length
            ? statistics.summary.label
            : `Summe (${visibleRows.length})`,
      },
      {
        columnId: 'count_before',
        content: (visibleRows) =>
          formatNumber(
            getFilteredSummaryMetric(visibleRows, 'count.before_hand_thinning'),
            metricDigits('count.before_hand_thinning'),
          ),
        className: 'text-right tabular-nums',
      },
      {
        columnId: 'count_after',
        content: (visibleRows) =>
          formatNumber(
            getFilteredSummaryMetric(visibleRows, 'count.after_hand_thinning'),
            metricDigits('count.after_hand_thinning'),
          ),
        className: 'text-right tabular-nums',
      },
      ...YEARLY_METRIC_CODES.map((metricCode) => ({
        columnId: metricCode,
        content: (visibleRows: FieldStatisticsRow[]) =>
          formatNumber(
            getFilteredSummaryMetric(visibleRows, metricCode),
            metricDigits(metricCode),
          ),
        className: 'text-right tabular-nums',
      })),
    ]
  }, [getFilteredSummaryMetric, rows.length, statistics])

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
            <>
              <DataTable
                columns={columns}
                rows={filteredRows}
                getRowKey={(row) => row.planting_id}
                emptyMessage="Keine Feldstatistik vorhanden."
                filters={tableFilters}
                onFilterChange={handleFilterChange}
                onResetFilters={handleResetFilters}
                summaryCells={summaryCells}
                selectedRowKey={selectedRowKey}
                onRowSelect={(row) => setSelectedRowKey(row?.planting_id ?? null)}
              />

              <div className="mt-8">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-slate-900">Zeitverlauf</h2>
                    <p className="mt-1 text-sm text-slate-500">
                      {chartRows.length === 1
                        ? `${chartRows[0].field_name} · ${chartRows[0].planting_name}`
                        : `Summe (${chartRows.length})`}
                    </p>
                  </div>
                  {perHectare ? (
                    <span className="text-sm font-medium text-slate-500">pro ha</span>
                  ) : null}
                </div>

                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  {charts.map((chart) => (
                    <FieldStatisticBarChart
                      key={chart.metricCode}
                      title={chart.title}
                      data={chart.data}
                      selectedYear={selectedYearNumber}
                      digits={metricDigits(chart.metricCode)}
                    />
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
