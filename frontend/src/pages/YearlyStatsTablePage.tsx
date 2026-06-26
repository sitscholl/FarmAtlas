import { useEffect, useMemo, useRef, useState } from 'react'
import { GoPencil } from 'react-icons/go'
import { IoMdAdd } from 'react-icons/io'
import { PiTrashBold } from 'react-icons/pi'

import api from '../api'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
  type DataTableSummaryCell,
} from '../components/DataTable'
import YearlyStatsModal from '../components/YearlyStatsModal'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildScopeLookup,
  getScopeKindLabel,
  resolveScope,
  type ScopeInfo,
} from '../lib/scopeLabels'
import type {
  FieldDetailRead,
  FieldRead,
  YearlyStatsRead,
} from '../types/generated/api'

type YearlyStatsRow = YearlyStatsRead & {
  scope: ScopeInfo
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

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)
}

function buildRows(stats: YearlyStatsRead[], fieldDetails: FieldDetailRead[]) {
  const scopeLookup = buildScopeLookup(fieldDetails)
  return stats.map((item) => ({
    ...item,
    scope: resolveScope(item, scopeLookup),
  }))
}

function sortRows(rows: YearlyStatsRow[]) {
  return rows.slice().sort((left, right) => {
    if (left.season_year !== right.season_year) {
      return right.season_year - left.season_year
    }
    const fieldCompare = left.scope.fieldName.localeCompare(right.scope.fieldName, 'de-DE')
    if (fieldCompare !== 0) {
      return fieldCompare
    }
    return left.id - right.id
  })
}

function sumNullable(rows: YearlyStatsRow[], key: keyof Pick<
  YearlyStatsRow,
  'thinning_hours' | 'harvest_hours' | 'filled_boxes' | 'yield_kg' | 'revenue'
>) {
  return rows.reduce((total, row) => total + (row[key] ?? 0), 0)
}

export default function YearlyStatsTablePage() {
  const interactiveAreaRef = useRef<HTMLDivElement | null>(null)
  const [stats, setStats] = useState<YearlyStatsRead[]>([])
  const [fields, setFields] = useState<FieldRead[]>([])
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedStatsId, setSelectedStatsId] = useState<number | null>(null)
  const [editingStats, setEditingStats] = useState<YearlyStatsRead | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [filters, setFilters] = useState({
    query: '',
    fieldId: '',
    seasonYear: '',
    scopeKind: '',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsResponse, fieldsResponse] = await Promise.all([
          api.get<YearlyStatsRead[]>('/yearly-stats'),
          api.get<FieldRead[]>('/fields'),
        ])
        const detailResponses = await Promise.all(
          fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
        )

        setStats(statsResponse.data)
        setFields(fieldsResponse.data)
        setFieldDetails(detailResponses.map((response) => response.data))
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching yearly stats table data', error)
        setStats([])
        setFields([])
        setFieldDetails([])
        setErrorMessage('Die Jahreswerte konnten nicht geladen werden.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchData()

    const handleDataChanged = () => {
      setIsLoading(true)
      void fetchData()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
  }, [])

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (interactiveAreaRef.current === null) {
        return
      }

      if (!interactiveAreaRef.current.contains(event.target as Node)) {
        setSelectedStatsId(null)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const rows = useMemo(() => buildRows(stats, fieldDetails), [fieldDetails, stats])
  const yearOptions = useMemo(
    () =>
      [...new Set(stats.map((item) => item.season_year))]
        .sort((left, right) => right - left)
        .map((year) => ({ label: String(year), value: String(year) })),
    [stats],
  )

  const columns = useMemo<DataTableColumn<YearlyStatsRow>[]>(
    () => [
      {
        id: 'season_year',
        header: 'Jahr',
        cell: (row) => row.season_year,
      },
      {
        id: 'field',
        header: 'Anlage',
        cell: (row) => row.scope.fieldName,
        sortValue: (row) => row.scope.fieldName,
      },
      {
        id: 'group',
        header: 'Gruppe',
        cell: (row) => row.scope.fieldGroup,
        sortValue: (row) => row.scope.fieldGroup,
      },
      {
        id: 'scope',
        header: 'Ebene',
        cell: (row) => getScopeKindLabel(row.scope.kind),
        sortValue: (row) => getScopeKindLabel(row.scope.kind),
      },
      {
        id: 'scopeLabel',
        header: 'Bezug',
        cell: (row) => row.scope.label,
        sortValue: (row) => row.scope.label,
      },
      {
        id: 'thinning_hours',
        header: 'Ausduennung (h)',
        cell: (row) => formatNumber(row.thinning_hours, 1),
        sortValue: (row) => row.thinning_hours,
      },
      {
        id: 'harvest_hours',
        header: 'Ernte (h)',
        cell: (row) => formatNumber(row.harvest_hours, 1),
        sortValue: (row) => row.harvest_hours,
      },
      {
        id: 'filled_boxes',
        header: 'Grosskisten',
        cell: (row) => formatNumber(row.filled_boxes, 1),
        sortValue: (row) => row.filled_boxes,
      },
      {
        id: 'yield_kg',
        header: 'Ertrag (kg)',
        cell: (row) => formatNumber(row.yield_kg, 0),
        sortValue: (row) => row.yield_kg,
      },
      {
        id: 'revenue',
        header: 'Umsatz',
        cell: (row) => formatCurrency(row.revenue),
        sortValue: (row) => row.revenue,
      },
      {
        id: 'notes',
        header: 'Notizen',
        cell: (row) => row.notes ?? '',
      },
    ],
    [],
  )

  const tableFilters = useMemo<DataTableFilter[]>(
    () => [
      {
        id: 'query',
        label: 'Suche',
        type: 'text',
        value: filters.query,
        placeholder: 'Anlage, Gruppe, Bezug oder Notiz',
      },
      {
        id: 'fieldId',
        label: 'Anlage',
        type: 'select',
        value: filters.fieldId,
        options: [
          { label: 'Alle', value: '' },
          ...fields
            .slice()
            .sort((left, right) => left.name.localeCompare(right.name, 'de-DE'))
            .map((field) => ({
              label: field.name,
              value: String(field.id),
            })),
        ],
      },
      {
        id: 'seasonYear',
        label: 'Jahr',
        type: 'select',
        value: filters.seasonYear,
        options: [{ label: 'Alle', value: '' }, ...yearOptions],
      },
      {
        id: 'scopeKind',
        label: 'Ebene',
        type: 'select',
        value: filters.scopeKind,
        options: [
          { label: 'Alle', value: '' },
          { label: 'Anlage', value: 'field' },
          { label: 'Pflanzung', value: 'planting' },
          { label: 'Abschnitt', value: 'section' },
        ],
      },
    ],
    [fields, filters, yearOptions],
  )

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return sortRows(rows).filter((row) => {
      const matchesQuery =
        normalizedQuery === '' ||
        [
          row.scope.fieldName,
          row.scope.fieldGroup,
          row.scope.label,
          getScopeKindLabel(row.scope.kind),
          row.notes ?? '',
          String(row.season_year),
        ]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery)

      const matchesField = filters.fieldId === '' || row.scope.fieldId === Number(filters.fieldId)
      const matchesYear = filters.seasonYear === '' || row.season_year === Number(filters.seasonYear)
      const matchesScope = filters.scopeKind === '' || row.scope.kind === filters.scopeKind

      return matchesQuery && matchesField && matchesYear && matchesScope
    })
  }, [filters, rows])

  const selectedStats = useMemo(
    () => filteredRows.find((row) => row.id === selectedStatsId) ?? null,
    [filteredRows, selectedStatsId],
  )

  useEffect(() => {
    if (selectedStatsId === null) {
      return
    }

    const stillExists = filteredRows.some((row) => row.id === selectedStatsId)
    if (!stillExists) {
      setSelectedStatsId(null)
    }
  }, [filteredRows, selectedStatsId])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      fieldId: '',
      seasonYear: '',
      scopeKind: '',
    })
  }

  const handleDeleteStats = async (row: YearlyStatsRow) => {
    const confirmed = window.confirm(
      `Sollen die Jahreswerte ${row.season_year} fuer "${row.scope.fieldName}" wirklich geloescht werden?`,
    )
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/yearly-stats/${row.id}`)
      setSelectedStatsId(null)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting yearly stats ${row.id}`, error)
      setErrorMessage('Die Jahreswerte konnten nicht geloescht werden.')
    }
  }

  const summaryCells = useMemo<DataTableSummaryCell<YearlyStatsRow>[]>(
    () => [
      {
        columnId: 'season_year',
        content: 'Summe',
      },
      {
        columnId: 'thinning_hours',
        content: (activeRows) => formatNumber(sumNullable(activeRows, 'thinning_hours'), 1),
      },
      {
        columnId: 'harvest_hours',
        content: (activeRows) => formatNumber(sumNullable(activeRows, 'harvest_hours'), 1),
      },
      {
        columnId: 'filled_boxes',
        content: (activeRows) => formatNumber(sumNullable(activeRows, 'filled_boxes'), 1),
      },
      {
        columnId: 'yield_kg',
        content: (activeRows) => formatNumber(sumNullable(activeRows, 'yield_kg'), 0),
      },
      {
        columnId: 'revenue',
        content: (activeRows) => formatCurrency(sumNullable(activeRows, 'revenue')),
      },
    ],
    [],
  )

  return (
    <section className="w-full max-w-7xl">
      <div className="px-3 py-4 sm:px-6 sm:py-6 lg:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Tabellenansicht
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              Jahreswerte
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800 transition hover:bg-sky-100"
            >
              <IoMdAdd />
              Jahreswerte
            </button>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {filteredRows.length} / {rows.length} Eintraege
            </div>
          </div>
        </div>

        <div ref={interactiveAreaRef} className="mt-8">
          {selectedStats ? (
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Ausgewaehlter Eintrag
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {selectedStats.scope.fieldName} | {selectedStats.season_year}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  Ertrag {formatNumber(selectedStats.yield_kg, 0)} kg | Umsatz{' '}
                  {formatCurrency(selectedStats.revenue)}
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setEditingStats(selectedStats)}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-amber-500"
                >
                  <GoPencil />
                  Bearbeiten
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteStats(selectedStats)}
                  className="inline-flex items-center gap-2 rounded-full bg-rose-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-rose-700"
                >
                  <PiTrashBold />
                  Loeschen
                </button>
              </div>
            </div>
          ) : null}

          {isLoading ? (
            <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
              Lade Jahreswerte...
            </div>
          ) : errorMessage ? (
            <div className="rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredRows}
              getRowKey={(row) => row.id}
              emptyMessage="Keine Jahreswerte gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              summaryCells={summaryCells}
              selectedRowKey={selectedStatsId}
              onRowSelect={(row) => setSelectedStatsId(row?.id ?? null)}
            />
          )}
        </div>
      </div>

      <YearlyStatsModal
        isOpen={isCreateOpen}
        fieldDetails={fieldDetails}
        onClose={() => setIsCreateOpen(false)}
      />
      <YearlyStatsModal
        isOpen={editingStats !== null}
        stats={editingStats}
        fieldDetails={fieldDetails}
        onClose={() => setEditingStats(null)}
      />
    </section>
  )
}
