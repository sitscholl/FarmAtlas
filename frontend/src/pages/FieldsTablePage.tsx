import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { GoPencil } from 'react-icons/go'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import DataTable, { type DataTableColumn } from '../components/DataTable'
import { DATA_CHANGED_EVENT } from '../lib/dataEvents'
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
  const [fields, setFields] = useState<FieldOverview[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [editingField, setEditingField] = useState<FieldOverview | null>(null)

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

  const columns = useMemo<DataTableColumn<FieldOverview>[]>(
    () => [
      {
        id: 'edit',
        header: '',
        headerClassName: 'w-14',
        cellClassName: 'w-14',
        cell: (field) => (
          <button
            type="button"
            onClick={() => setEditingField(field)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-amber-400 text-slate-950 shadow-sm transition hover:bg-amber-500"
            aria-label={`${field.name} bearbeiten`}
          >
            <GoPencil />
          </button>
        ),
      },
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
            {fields.length} Eintraege
          </div>
        </div>

        <div className="mt-8">
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
              rows={fields}
              getRowKey={(field) => field.id}
              emptyMessage="Keine Anlagen gefunden."
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
