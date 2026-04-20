import { useEffect, useMemo, useRef, useState } from 'react'
import { GoPencil } from 'react-icons/go'
import { IoMdAdd } from 'react-icons/io'
import { PiTrashBold } from 'react-icons/pi'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
  type DataTableSummaryCell,
} from '../components/DataTable'
import { nutrientCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildNutrientEditAction,
  buildNutrientEditInitialValues,
} from '../lib/nutrientForm'
import type { NutrientRequirementRead, VarietyRead } from '../types/generated/api'

function formatNumber(value: number | null | undefined, digits = 3) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  if (value === 0) {
    return '0'
  }

  const scientific = value.toExponential(digits)
  const [mantissa, exponent] = scientific.split('e')
  const normalizedExponent = Number(exponent)

  return `${mantissa.replace('.', ',')}e${normalizedExponent}`
}

function formatVarietyName(value: string | null | undefined) {
  return value === null || value === undefined || value.trim() === '' ? 'Standard' : value
}

export default function NutrientsTablePage() {
  const interactiveAreaRef = useRef<HTMLDivElement | null>(null)
  const [nutrients, setNutrients] = useState<NutrientRequirementRead[]>([])
  const [varieties, setVarieties] = useState<VarietyRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedNutrientId, setSelectedNutrientId] = useState<number | null>(null)
  const [editingNutrient, setEditingNutrient] = useState<NutrientRequirementRead | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [filters, setFilters] = useState({
    query: '',
    variety: '',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [nutrientsResponse, varietiesResponse] = await Promise.all([
          api.get<NutrientRequirementRead[]>('/nutrients'),
          api.get<VarietyRead[]>('/varieties'),
        ])

        setNutrients(nutrientsResponse.data)
        setVarieties(varietiesResponse.data)
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching nutrient table data', error)
        setNutrients([])
        setVarieties([])
        setErrorMessage('Die Naehrstoffdaten konnten nicht geladen werden.')
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
        setSelectedNutrientId(null)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const columns = useMemo<DataTableColumn<NutrientRequirementRead>[]>(
    () => [
      {
        id: 'nutrient_code',
        header: 'Code',
        cell: (nutrient) => <span className="font-semibold text-slate-900">{nutrient.nutrient_code}</span>,
      },
      {
        id: 'variety',
        header: 'Sorte',
        cell: (nutrient) => formatVarietyName(nutrient.variety),
      },
      {
        id: 'requirement_per_kg_min',
        header: 'Min pro kg',
        cell: (nutrient) => formatNumber(nutrient.requirement_per_kg_min, 3),
      },
      {
        id: 'requirement_per_kg_mean',
        header: 'Mittel pro kg',
        cell: (nutrient) => formatNumber(nutrient.requirement_per_kg_mean, 3),
      },
      {
        id: 'requirement_per_kg_max',
        header: 'Max pro kg',
        cell: (nutrient) => formatNumber(nutrient.requirement_per_kg_max, 3),
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
        placeholder: 'Code oder Sorte',
      },
      {
        id: 'variety',
        label: 'Sorte',
        type: 'select',
        value: filters.variety,
        options: [
          { label: 'Alle', value: '' },
          { label: 'Standard', value: '__default__' },
          ...varieties
            .slice()
            .sort((left, right) => left.name.localeCompare(right.name, 'de-DE'))
            .map((variety) => ({
              label: `${variety.name}${variety.group ? ` (${variety.group})` : ''}`,
              value: variety.name,
            })),
        ],
      },
    ],
    [filters, varieties],
  )

  const filteredNutrients = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return [...nutrients]
      .sort((left, right) => {
        const codeCompare = left.nutrient_code.localeCompare(right.nutrient_code, 'de-DE')
        if (codeCompare !== 0) {
          return codeCompare
        }

        return formatVarietyName(left.variety).localeCompare(formatVarietyName(right.variety), 'de-DE')
      })
      .filter((nutrient) => {
        const matchesQuery =
          normalizedQuery === '' ||
          [nutrient.nutrient_code, nutrient.variety ?? 'Standard']
            .join(' ')
            .toLowerCase()
            .includes(normalizedQuery)

        const matchesVariety =
          filters.variety === '' ||
          (filters.variety === '__default__'
            ? nutrient.variety === null || nutrient.variety === ''
            : nutrient.variety === filters.variety)

        return matchesQuery && matchesVariety
      })
  }, [filters, nutrients])

  const selectedNutrient = useMemo(
    () => filteredNutrients.find((nutrient) => nutrient.id === selectedNutrientId) ?? null,
    [filteredNutrients, selectedNutrientId],
  )

  useEffect(() => {
    if (selectedNutrientId === null) {
      return
    }

    const stillExists = filteredNutrients.some((nutrient) => nutrient.id === selectedNutrientId)
    if (!stillExists) {
      setSelectedNutrientId(null)
    }
  }, [filteredNutrients, selectedNutrientId])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      variety: '',
    })
  }

  const handleDeleteNutrient = async (nutrient: NutrientRequirementRead) => {
    const confirmed = window.confirm(
      `Soll der Naehrstoffeintrag "${nutrient.nutrient_code}" fuer "${formatVarietyName(nutrient.variety)}" wirklich geloescht werden?`,
    )
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/nutrients/${nutrient.id}`)
      setSelectedNutrientId(null)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting nutrient requirement ${nutrient.id}`, error)
      setErrorMessage('Der Naehrstoffeintrag konnte nicht geloescht werden.')
    }
  }

  const summaryCells = useMemo<DataTableSummaryCell<NutrientRequirementRead>[]>(
    () => [
      {
        columnId: 'nutrient_code',
        content: 'Summe',
      },
      {
        columnId: 'variety',
        content: (rows) => rows.length,
      },
    ],
    [],
  )

  const editAction = useMemo(
    () => buildNutrientEditAction(editingNutrient),
    [editingNutrient],
  )
  const editInitialValues = useMemo(
    () => buildNutrientEditInitialValues(editingNutrient),
    [editingNutrient],
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
              Naehrstoffe
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800 transition hover:bg-sky-100"
            >
              <IoMdAdd />
              Naehrstoff
            </button>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {filteredNutrients.length} / {nutrients.length} Eintraege
            </div>
          </div>
        </div>

        <div ref={interactiveAreaRef} className="mt-8">
          {selectedNutrient ? (
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Ausgewaehlter Eintrag
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {selectedNutrient.nutrient_code} | {formatVarietyName(selectedNutrient.variety)}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  Min {formatNumber(selectedNutrient.requirement_per_kg_min, 3)} | Mittel {formatNumber(selectedNutrient.requirement_per_kg_mean, 3)} | Max {formatNumber(selectedNutrient.requirement_per_kg_max, 3)}
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setEditingNutrient(selectedNutrient)}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-amber-500"
                >
                  <GoPencil />
                  Bearbeiten
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteNutrient(selectedNutrient)}
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
              Lade Naehrstoffdaten...
            </div>
          ) : errorMessage ? (
            <div className="rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredNutrients}
              getRowKey={(nutrient) => nutrient.id}
              emptyMessage="Keine Naehrstoffeintraege gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              summaryCells={summaryCells}
              selectedRowKey={selectedNutrientId}
              onRowSelect={(nutrient) => setSelectedNutrientId(nutrient?.id ?? null)}
            />
          )}
        </div>
      </div>

      <CreateEntityModal
        action={nutrientCreateAction}
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
      <CreateEntityModal
        action={editAction}
        isOpen={editingNutrient !== null}
        initialValues={editInitialValues}
        onClose={() => setEditingNutrient(null)}
      />
    </section>
  )
}
