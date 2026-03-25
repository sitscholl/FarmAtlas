import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { GoPencil } from 'react-icons/go'
import { PiTrashBold } from 'react-icons/pi'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
  type DataTableSummaryCell,
} from '../components/DataTable'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildFieldEditAction,
  buildFieldEditInitialValues,
} from '../lib/fieldForm'
import type { FieldOverview } from '../types/field'

function formatNumber(value: number | null, digits = 1) {
  if (value === null) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatBoolean(value: boolean | null) {
  if (value === null) {
    return 'n/a'
  }

  return value ? 'Ja' : 'Nein'
}

export default function FieldsTablePage() {
  const interactiveAreaRef = useRef<HTMLDivElement | null>(null)
  const [fields, setFields] = useState<FieldOverview[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedFieldId, setSelectedFieldId] = useState<number | null>(null)
  const [editingField, setEditingField] = useState<FieldOverview | null>(null)
  const [filters, setFilters] = useState({
    query: '',
    status: 'active',
    herbicideFree: '',
  })

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const response = await api.get<FieldOverview[]>('/fields/overview')
        if (!Array.isArray(response.data)) {
          throw new TypeError('Expected /fields/overview to return an array.')
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

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (interactiveAreaRef.current === null) {
        return
      }

      if (!interactiveAreaRef.current.contains(event.target as Node)) {
        setSelectedFieldId(null)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const columns = useMemo<DataTableColumn<FieldOverview>[]>(
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
        id: 'section',
        header: 'Abschnitt',
        cell: (field) => field.section ?? 'n/a',
      },
      {
        id: 'variety',
        header: 'Sorte',
        cell: (field) => field.variety,
      },
      {
        id: 'area_ha',
        header: 'Flaeche (ha)',
        cell: (field) => formatNumber(field.area_ha, 2),
      },
      {
        id: 'planting_year',
        header: 'Pflanzjahr',
        cell: (field) => String(field.planting_year),
      },
      {
        id: 'tree_count',
        header: 'Baumzahl',
        cell: (field) => formatNumber(field.tree_count, 0),
      },
      {
        id: 'tree_height',
        header: 'Baumhoehe',
        cell: (field) => `${formatNumber(field.tree_height, 1)} m`,
      },
      {
        id: 'soil_type',
        header: 'Bodenart',
        cell: (field) => field.soil_type,
      },
      {
        id: 'soil_weight',
        header: 'Bodenschwere',
        cell: (field) => field.soil_weight ?? 'n/a',
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
        placeholder: 'Name, Sorte oder Station',
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
          {label: 'Alle', value: ''},
          {label: 'Ja', value: 'Ja'},
          {label: 'Nein', value: 'Nein'},
        ]
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
          [field.name, field.variety, field.reference_station, field.reference_provider]
            .join(' ')
            .toLowerCase()
            .includes(normalizedQuery)

        const matchesStatus =
          filters.status === '' ||
          (filters.status === 'active' ? field.active : !field.active)

        const matchesherbicideFree =
          filters.herbicideFree === '' ||
          (filters.herbicideFree === 'Ja' ? field.herbicide_free : !field.herbicide_free)

        return matchesQuery && matchesStatus && matchesherbicideFree
      })
  }, [fields, filters])

  const selectedField = useMemo(
    () => filteredFields.find((field) => field.id === selectedFieldId) ?? null,
    [filteredFields, selectedFieldId],
  )

  useEffect(() => {
    if (selectedFieldId === null) {
      return
    }

    const stillExists = filteredFields.some((field) => field.id === selectedFieldId)
    if (!stillExists) {
      setSelectedFieldId(null)
    }
  }, [filteredFields, selectedFieldId])

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

  const handleDeleteField = async (field: FieldOverview) => {
    const confirmed = window.confirm(`Soll die Anlage "${field.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/fields/${field.id}`)
      setSelectedFieldId(null)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting field ${field.id}`, error)
      setErrorMessage('Die Anlage konnte nicht geloescht werden.')
    }
  }

  const summaryCells = useMemo<DataTableSummaryCell<FieldOverview>[]>(
    () => [
      {
        columnId: 'name',
        content: 'Summe',
      },
      {
        columnId: 'area_ha',
        content: (rows) =>
          formatNumber(
            rows.reduce((total, field) => total + (field.area_ha ?? 0), 0),
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

  const editAction = useMemo(() => buildFieldEditAction(editingField), [editingField])
  const editInitialValues = useMemo(
    () => buildFieldEditInitialValues(editingField),
    [editingField],
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
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {filteredFields.length} / {fields.length} Eintraege
          </div>
        </div>

        <div ref={interactiveAreaRef} className="mt-8">
          {selectedField ? (
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Ausgewaehlte Anlage
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {selectedField.name}
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setEditingField(selectedField)}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-amber-500"
                >
                  <GoPencil />
                  Bearbeiten
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteField(selectedField)}
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
              Lade Felddaten...
            </div>
          ) : errorMessage ? (
            <div className="rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
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
              selectedRowKey={selectedFieldId}
              onRowSelect={(field) => setSelectedFieldId(field?.id ?? null)}
            />
          )}
        </div>
      </div>

      <CreateEntityModal
        action={editAction}
        isOpen={editingField !== null}
        initialValues={editInitialValues}
        onClose={() => setEditingField(null)}
      />
    </section>
  )
}
