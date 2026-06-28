import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import api from '../api'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
} from '../components/DataTable'
import WaterBalanceModal, {
  buildWaterBalanceLoadingState,
  fetchWaterBalanceModalState,
  type WaterBalanceModalState,
} from '../components/WaterBalanceModal'
import { DATA_CHANGED_EVENT } from '../lib/dataEvents'
import type { WaterBalanceFieldSummaryRead } from '../types/generated/api'

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return 'n/a'
  }

  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return `${formatNumber(value * 100, 0)} %`
}

export default function WaterBalanceTablePage() {
  const [rows, setRows] = useState<WaterBalanceFieldSummaryRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [waterBalanceModal, setWaterBalanceModal] = useState<WaterBalanceModalState | null>(null)
  const [filters, setFilters] = useState({
    query: '',
    status: 'active',
  })

  useEffect(() => {
    const fetchRows = async () => {
      try {
        const response = await api.get<WaterBalanceFieldSummaryRead[]>('/fields/water-balance/table')
        if (!Array.isArray(response.data)) {
          throw new TypeError('Expected /fields/water-balance/table to return an array.')
        }

        setRows(response.data)
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching water balance table', error)
        setRows([])
        setErrorMessage('Die Wasserbilanzdaten konnten nicht geladen werden.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchRows()

    const handleDataChanged = () => {
      setIsLoading(true)
      void fetchRows()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
  }, [])

  const handleOpenWaterBalance = useCallback(async (row: WaterBalanceFieldSummaryRead) => {
    const field = { id: row.field_id, name: row.field_name }
    setWaterBalanceModal(buildWaterBalanceLoadingState(field))
    setWaterBalanceModal(await fetchWaterBalanceModalState(field))
  }, [])

  const columns = useMemo<DataTableColumn<WaterBalanceFieldSummaryRead>[]>(
    () => [
      {
        id: 'field_name',
        header: 'Anlage',
        cell: (row) => (
          <Link
            to={`/fields/${row.field_id}`}
            className="font-semibold text-sky-700 transition hover:text-sky-900"
          >
            {row.field_name}
          </Link>
        ),
      },
      {
        id: 'field_group',
        header: 'Gruppe',
        cell: (row) => row.field_group,
      },
      {
        id: 'safe_ratio',
        header: 'Wasserbilanz',
        sortValue: (row) => row.summary.safe_ratio,
        cell: (row) => {
          const value = row.summary.safe_ratio
          if (value === null || value === undefined) {
            return <span className="text-slate-400">n/a</span>
          }

          return (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                void handleOpenWaterBalance(row)
              }}
              className={`inline-flex min-w-20 justify-center border px-3 py-1 text-sm font-semibold transition ${
                row.summary.below_raw === true
                  ? 'border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100'
                  : 'border-sky-200 bg-sky-50 text-sky-800 hover:bg-sky-100'
              }`}
            >
              {formatPercent(value)}
            </button>
          )
        },
      },
      {
        id: 'water_deficit',
        header: 'Defizit (mm)',
        sortValue: (row) => row.summary.current_water_deficit,
        cell: (row) => formatNumber(row.summary.current_water_deficit),
      },
      {
        id: 'soil_water_content',
        header: 'Bodenwasser (mm)',
        sortValue: (row) => row.summary.current_soil_water_content,
        cell: (row) => formatNumber(row.summary.current_soil_water_content),
      },
      {
        id: 'available_water_storage',
        header: 'Speicher (mm)',
        sortValue: (row) => row.summary.available_water_storage,
        cell: (row) => formatNumber(row.summary.available_water_storage),
      },
      {
        id: 'readily_available_water',
        header: 'RAW (mm)',
        sortValue: (row) => row.summary.readily_available_water,
        cell: (row) => formatNumber(row.summary.readily_available_water),
      },
      {
        id: 'effective_root_depth_cm',
        header: 'Wurzeltiefe',
        sortValue: (row) => row.effective_root_depth_cm,
        cell: (row) =>
          row.effective_root_depth_cm === null || row.effective_root_depth_cm === undefined
            ? 'n/a'
            : `${formatNumber(row.effective_root_depth_cm, 0)} cm`,
      },
      {
        id: 'last_irrigation_date',
        header: 'Letzte Bewaesserung',
        sortValue: (row) => row.last_irrigation_date,
        cell: (row) => formatDate(row.last_irrigation_date),
      },
      {
        id: 'as_of',
        header: 'Stand',
        sortValue: (row) => row.summary.as_of,
        cell: (row) => formatDate(row.summary.as_of),
      },
      {
        id: 'status',
        header: 'Status',
        sortValue: (row) => row.active,
        cell: (row) => (row.active ? 'Aktiv' : 'Inaktiv'),
      },
    ],
    [handleOpenWaterBalance],
  )

  const tableFilters = useMemo<DataTableFilter[]>(
    () => [
      {
        id: 'query',
        label: 'Suche',
        type: 'text',
        value: filters.query,
        placeholder: 'Anlage oder Gruppe',
      },
      {
        id: 'status',
        label: 'Status',
        type: 'select',
        value: filters.status,
        options: [
          { label: 'Alle', value: '' },
          { label: 'Aktiv', value: 'active' },
          { label: 'Inaktiv', value: 'inactive' },
        ],
      },
    ],
    [filters],
  )

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return [...rows]
      .sort((left, right) => left.field_name.localeCompare(right.field_name, 'de-DE'))
      .filter((row) => {
        const matchesQuery =
          normalizedQuery === '' ||
          [row.field_name, row.field_group]
            .join(' ')
            .toLowerCase()
            .includes(normalizedQuery)

        const matchesStatus =
          filters.status === '' ||
          (filters.status === 'active' ? row.active : !row.active)

        return matchesQuery && matchesStatus
      })
  }, [filters, rows])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      status: 'active',
    })
  }

  return (
    <section className="w-full max-w-7xl">
      <div className="px-3 py-4 sm:px-6 sm:py-6 lg:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Wasserbilanz
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              Anlagen Wassergehalt
            </h1>
          </div>
          <div className="border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {filteredRows.length} / {rows.length} Eintraege
          </div>
        </div>

        <div className="mt-8">
          {isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
              Lade Wasserbilanzdaten...
            </div>
          ) : errorMessage ? (
            <div className="border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredRows}
              getRowKey={(row) => row.field_id}
              emptyMessage="Keine Wasserbilanzdaten gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
            />
          )}
        </div>
      </div>

      <WaterBalanceModal
        state={waterBalanceModal}
        onClose={() => setWaterBalanceModal(null)}
      />
    </section>
  )
}
