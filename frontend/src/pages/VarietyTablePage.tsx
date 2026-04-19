import { useEffect, useMemo, useRef, useState } from 'react'
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
  buildVarietyEditAction,
  buildVarietyEditInitialValues,
} from '../lib/varietyForm'
import type { FieldSummaryRead, VarietyRead } from '../types/generated/api'

function formatNumber(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

export default function VarietyTablePage() {
  const interactiveAreaRef = useRef<HTMLDivElement | null>(null)
  const [varieties, setVarieties] = useState<VarietyRead[]>([])
  const [fields, setFields] = useState<FieldSummaryRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedVarietyId, setSelectedVarietyId] = useState<number | null>(null)
  const [editingVariety, setEditingVariety] = useState<VarietyRead | null>(null)
  const [filters, setFilters] = useState({
    query: '',
    group: '',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [varietiesResponse, fieldsResponse] = await Promise.all([
          api.get<VarietyRead[]>('/varieties'),
          api.get<FieldSummaryRead[]>('/fields/summary'),
        ])

        setVarieties(varietiesResponse.data)
        setFields(fieldsResponse.data)
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching varieties table data', error)
        setVarieties([])
        setFields([])
        setErrorMessage('Die Sortendaten konnten nicht geladen werden.')
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
        setSelectedVarietyId(null)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const usageCountByVariety = useMemo(() => {
    return fields.reduce<Record<string, number>>((counts, field) => {
      field.variety_names.forEach((varietyName) => {
        counts[varietyName] = (counts[varietyName] ?? 0) + 1
      })
      return counts
    }, {})
  }, [fields])

  const columns = useMemo<DataTableColumn<VarietyRead>[]>(
    () => [
      {
        id: 'name',
        header: 'Sorte',
        cell: (variety) => <span className="font-semibold text-slate-900">{variety.name}</span>,
      },
      {
        id: 'group',
        header: 'Gruppe',
        cell: (variety) => variety.group,
      },
      {
        id: 'field_count',
        header: 'Anlagen',
        cell: (variety) => String(usageCountByVariety[variety.name] ?? 0),
      },
      {
        id: 'nr_per_kg',
        header: 'N pro kg',
        cell: (variety) => formatNumber(variety.nr_per_kg, 3),
      },
      {
        id: 'kg_per_box',
        header: 'kg pro Kiste',
        cell: (variety) => formatNumber(variety.kg_per_box, 2),
      },
      {
        id: 'slope',
        header: 'Slope',
        cell: (variety) => formatNumber(variety.slope, 3),
      },
      {
        id: 'intercept',
        header: 'Intercept',
        cell: (variety) => formatNumber(variety.intercept, 3),
      },
      {
        id: 'specific_weight',
        header: 'Spez. Gewicht',
        cell: (variety) => formatNumber(variety.specific_weight, 3),
      },
    ],
    [usageCountByVariety],
  )

  const tableFilters = useMemo<DataTableFilter[]>(
    () => [
      {
        id: 'query',
        label: 'Suche',
        type: 'text',
        value: filters.query,
        placeholder: 'Name oder Gruppe',
      },
      {
        id: 'group',
        label: 'Gruppe',
        type: 'select',
        value: filters.group,
        options: [
          { label: 'Alle', value: '' },
          ...Array.from(new Set(varieties.map((variety) => variety.group)))
            .sort((left, right) => left.localeCompare(right, 'de-DE'))
            .map((group) => ({
              label: group,
              value: group,
            })),
        ],
      },
    ],
    [filters, varieties],
  )

  const filteredVarieties = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return [...varieties]
      .sort((left, right) => left.name.localeCompare(right.name, 'de-DE'))
      .filter((variety) => {
        const matchesQuery =
          normalizedQuery === '' ||
          [variety.name, variety.group].join(' ').toLowerCase().includes(normalizedQuery)

        const matchesGroup = filters.group === '' || variety.group === filters.group

        return matchesQuery && matchesGroup
      })
  }, [filters, varieties])

  const selectedVariety = useMemo(
    () => filteredVarieties.find((variety) => variety.id === selectedVarietyId) ?? null,
    [filteredVarieties, selectedVarietyId],
  )

  useEffect(() => {
    if (selectedVarietyId === null) {
      return
    }

    const stillExists = filteredVarieties.some((variety) => variety.id === selectedVarietyId)
    if (!stillExists) {
      setSelectedVarietyId(null)
    }
  }, [filteredVarieties, selectedVarietyId])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      group: '',
    })
  }

  const handleDeleteVariety = async (variety: VarietyRead) => {
    const confirmed = window.confirm(`Soll die Sorte "${variety.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/varieties/${variety.id}`)
      setSelectedVarietyId(null)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting variety ${variety.id}`, error)
      setErrorMessage('Die Sorte konnte nicht geloescht werden.')
    }
  }

  const summaryCells = useMemo<DataTableSummaryCell<VarietyRead>[]>(
    () => [
      {
        columnId: 'name',
        content: 'Summe',
      },
      {
        columnId: 'field_count',
        content: (rows) =>
          rows.reduce((total, variety) => total + (usageCountByVariety[variety.name] ?? 0), 0),
      },
    ],
    [usageCountByVariety],
  )

  const editAction = useMemo(() => buildVarietyEditAction(editingVariety), [editingVariety])
  const editInitialValues = useMemo(
    () => buildVarietyEditInitialValues(editingVariety),
    [editingVariety],
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
              Sorten
            </h1>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {filteredVarieties.length} / {varieties.length} Eintraege
          </div>
        </div>

        <div ref={interactiveAreaRef} className="mt-8">
          {selectedVariety ? (
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Ausgewaehlte Sorte
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {selectedVariety.name}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {selectedVariety.group} | {usageCountByVariety[selectedVariety.name] ?? 0} Anlagen
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setEditingVariety(selectedVariety)}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-amber-500"
                >
                  <GoPencil />
                  Bearbeiten
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteVariety(selectedVariety)}
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
              Lade Sortendaten...
            </div>
          ) : errorMessage ? (
            <div className="rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredVarieties}
              getRowKey={(variety) => variety.id}
              emptyMessage="Keine Sorten gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              summaryCells={summaryCells}
              selectedRowKey={selectedVarietyId}
              onRowSelect={(variety) => setSelectedVarietyId(variety?.id ?? null)}
            />
          )}
        </div>
      </div>

      <CreateEntityModal
        action={editAction}
        isOpen={editingVariety !== null}
        initialValues={editInitialValues}
        onClose={() => setEditingVariety(null)}
      />
    </section>
  )
}
