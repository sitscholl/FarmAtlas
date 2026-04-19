import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import api from '../api'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
  type DataTableSummaryCell,
} from '../components/DataTable'
import { DATA_CHANGED_EVENT } from '../lib/dataEvents'
import type { FieldSummaryRead } from '../types/generated/api'

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatBoolean(value: boolean | null | undefined) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return value ? 'Ja' : 'Nein'
}

function squareMetresToHectares(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return null
  }
  return value / 10000
}

export default function FieldsTablePage() {
  const [fields, setFields] = useState<FieldSummaryRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    query: '',
    status: 'active',
    herbicideFree: '',
  })

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const response = await api.get<FieldSummaryRead[]>('/fields/summary')
        if (!Array.isArray(response.data)) {
          throw new TypeError('Expected /fields/summary to return an array.')
        }

        setFields(response.data)
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching fields table', error)
        setFields([])
        setErrorMessage('Die Felddaten konnten nicht geladen werden.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchFields()

    const handleDataChanged = () => {
      setIsLoading(true)
      void fetchFields()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
  }, [])

  const columns = useMemo<DataTableColumn<FieldSummaryRead>[]>(
    () => [
      {
        id: 'name',
        header: 'Anlage',
        cell: (field) => (
          <Link
            to={`/fields/${field.id}`}
            className="font-semibold text-sky-700 transition hover:text-sky-900"
          >
            {field.name}
          </Link>
        ),
      },
      {
        id: 'group',
        header: 'Gruppe',
        cell: (field) => field.group,
      },
      {
        id: 'varieties',
        header: 'Sorten',
        cell: (field) => field.variety_names.join(', ') || 'n/a',
      },
      {
        id: 'area',
        header: 'Flaeche (ha)',
        cell: (field) => formatNumber(squareMetresToHectares(field.total_area), 2),
      },
      {
        id: 'plantings',
        header: 'Pflanzungen',
        cell: (field) => formatNumber(field.planting_count, 0),
      },
      {
        id: 'sections',
        header: 'Abschnitte',
        cell: (field) => formatNumber(field.section_count, 0),
      },
      {
        id: 'tree_count',
        header: 'Baumzahl',
        cell: (field) => formatNumber(field.tree_count, 0),
      },
      {
        id: 'station',
        header: 'Station',
        cell: (field) => field.reference_station,
      },
      {
        id: 'water_balance',
        header: 'Wasserbilanz',
        cell: (field) =>
          field.water_balance_summary.safe_ratio === null || field.water_balance_summary.safe_ratio === undefined
            ? 'n/a'
            : `${formatNumber(field.water_balance_summary.safe_ratio * 100, 0)} %`,
      },
      {
        id: 'herbicide_free',
        header: 'Herbizidfrei',
        cell: (field) => formatBoolean(field.herbicide_free),
      },
      {
        id: 'active',
        header: 'Status',
        cell: (field) => (field.active ? 'Aktiv' : 'Inaktiv'),
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
        placeholder: 'Name, Gruppe oder Station',
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
      {
        id: 'herbicideFree',
        label: 'Herbizidfrei',
        type: 'select',
        value: filters.herbicideFree,
        options: [
          { label: 'Alle', value: '' },
          { label: 'Ja', value: 'Ja' },
          { label: 'Nein', value: 'Nein' },
        ],
      },
    ],
    [filters],
  )

  const filteredFields = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return [...fields]
      .sort((left, right) => left.name.localeCompare(right.name, 'de-DE'))
      .filter((field) => {
        const matchesQuery =
          normalizedQuery === '' ||
          [field.name, field.group, field.reference_station, field.reference_provider, field.variety_names.join(' ')]
            .join(' ')
            .toLowerCase()
            .includes(normalizedQuery)

        const matchesStatus =
          filters.status === '' ||
          (filters.status === 'active' ? field.active : !field.active)

        const matchesHerbicideFree =
          filters.herbicideFree === '' ||
          (filters.herbicideFree === 'Ja'
            ? field.herbicide_free === true
            : field.herbicide_free === false)

        return matchesQuery && matchesStatus && matchesHerbicideFree
      })
  }, [fields, filters])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      status: 'active',
      herbicideFree: '',
    })
  }

  const summaryCells = useMemo<DataTableSummaryCell<FieldSummaryRead>[]>(
    () => [
      {
        columnId: 'name',
        content: 'Summe',
      },
      {
        columnId: 'area',
        content: (rows) =>
          formatNumber(
            rows.reduce((total, field) => total + (squareMetresToHectares(field.total_area) ?? 0), 0),
            2,
          ),
      },
      {
        columnId: 'tree_count',
        content: (rows) =>
          formatNumber(
            rows.reduce((total, field) => total + (field.tree_count ?? 0), 0),
            0,
          ),
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
              Anlagen
            </h1>
          </div>
          <div className="border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {filteredFields.length} / {fields.length} Eintraege
          </div>
        </div>

        <div className="mt-8">
          {isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
              Lade Felddaten...
            </div>
          ) : errorMessage ? (
            <div className="border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredFields}
              getRowKey={(field) => field.id}
              emptyMessage="Keine Anlagen gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              summaryCells={summaryCells}
            />
          )}
        </div>
      </div>
    </section>
  )
}
