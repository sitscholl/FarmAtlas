import { useEffect, useMemo, useState } from 'react'

import { GoPencil } from 'react-icons/go'
import { IoWater } from 'react-icons/io5'
import { GiPlantWatering } from "react-icons/gi";
import { PiTrashBold } from 'react-icons/pi'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import FieldBox, {
  type FieldBoxMetric,
  type FieldBoxStatusBar,
} from '../components/FieldBox'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildFieldEditAction,
  buildFieldEditInitialValues,
} from '../lib/fieldForm'
import { type FieldOverview } from '../types/generated/api'

function formatNumber(value: number, digits = 1) {
  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatOptionalNumber(
  value: number | null,
  suffix: string,
  digits = 1,
) {
  if (value === null) {
    return 'n/a'
  }

  return `${formatNumber(value, digits)} ${suffix}`.trim()
}

function buildFieldMetrics(field: FieldOverview): FieldBoxMetric[] {
  return [
    { label: 'Flaeche', value: formatOptionalNumber(field.area_ha, 'ha', 2) },
    { label: 'Pflanzjahr', value: String(field.planting_year) },
    { label: 'Eff. Wurzeltiefe', value: `${formatNumber(field.effective_root_depth_cm)} cm` },
    {
      label: 'Baumzahl',
      value: field.tree_count === null ? 'n/a' : formatNumber(field.tree_count, 0),
    },
    {
      label: 'Wasserdefizit',
      value: formatOptionalNumber(field.current_water_deficit, 'mm', 1),
    },
  ]
}

function buildSafeRatioBar(field: FieldOverview): FieldBoxStatusBar | undefined {
  if (field.safe_ratio === null) {
    return undefined
  }

  const ratioPercent = Math.round(field.safe_ratio * 100)
  return {
    label: 'Wasserbilanz',
    value: `${ratioPercent}%`,
    percentage: Math.max(0, Math.min(100, ratioPercent)),
    isCritical: field.safe_ratio < 0,
  }
}

function formatReference(field: Pick<FieldOverview, 'reference_provider' | 'reference_station'>) {
  return `${field.reference_station}`
}

function buildSubtitle(field: FieldOverview) {
  return [
    field.section ? `Abschnitt: ${field.section}` : null,
    `Sorte: ${field.variety}`,
    `Bodenart: ${field.soil_type}`,
    field.soil_weight ? `Bodenschwere: ${field.soil_weight}` : null,
  ]
    .filter((part): part is string => part !== null)
    .join('\n')
}

export default function Home() {
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
        console.error('Error fetching fields', error)
        setErrorMessage('Fields could not be loaded.')
        setFields([])
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

  const editAction = useMemo(() => buildFieldEditAction(editingField), [editingField])

  const editInitialValues = useMemo(
    () => buildFieldEditInitialValues(editingField),
    [editingField],
  )

  const handleDeleteField = async (field: FieldOverview) => {
    const confirmed = window.confirm(`Soll die Anlage "${field.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/fields/${field.id}`)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting field ${field.id}`, error)
      setErrorMessage('Die Anlage konnte nicht geloescht werden.')
    }
  }

  const handleRefreshField = async (field: FieldOverview) => {
    try {
      await api.post(`/fields/${field.id}/water-balance`)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error refreshing field ${field.id}`, error)
      setErrorMessage('Die Wasserbilanz fuer das Feld konnte nicht aktualisiert werden.')
    }
  }

  const handleClearIrrigation = async (field: FieldOverview) => {
    const confirmed = window.confirm(`Sollen alle Bewaesserungseintraege fuer "${field.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/fields/${field.id}/irrigation`)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error clearing irrigation for field ${field.id}`, error)
      setErrorMessage('Die Bewaesserungseintraege konnten nicht geloescht werden.')
    }
  }

  const content = (() => {
    if (isLoading) {
      return (
        <div className="mt-10 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
          Loading fields...
        </div>
      )
    }

    if (errorMessage !== null) {
      return (
        <div className="mt-10 rounded-2xl border border-rose-200 bg-rose-50 px-6 py-10 text-center text-rose-700">
          {errorMessage}
        </div>
      )
    }

    if (fields.length === 0) {
      return (
        <div className="mt-10 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
          No fields are configured yet.
        </div>
      )
    }

    return (
      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {fields.map((field) => (
          <FieldBox
            key={field.id}
            title={field.name}
            badge={formatReference(field)}
            subtitle={buildSubtitle(field)}
            statusBar={buildSafeRatioBar(field)}
            metrics={buildFieldMetrics(field)}
            to={`/fields/${field.id}`}
            titleAdornment={
              field.herbicide_free === true ? (
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500"
                  aria-hidden="true"
                />
              ) : undefined
            }
            actions={
              <>
                <button
                  type="button"
                  onClick={() => setEditingField(field)}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-amber-400 text-slate-950 shadow-sm transition hover:bg-amber-500"
                  aria-label={`${field.name} bearbeiten`}
                >
                  <GoPencil />
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteField(field)}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-rose-600 text-white shadow-sm transition hover:bg-rose-700"
                  aria-label={`${field.name} loeschen`}
                >
                  <PiTrashBold />
                </button>
                <button
                  type="button"
                  onClick={() => void handleRefreshField(field)}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-white shadow-sm transition hover:bg-blue-700"
                  aria-label={`${field.name} Wasserbilanz aktualisieren`}
                >
                  <IoWater />
                </button>
                <button
                  type="button"
                  onClick={() => void handleClearIrrigation(field)}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-rose-700 text-white shadow-sm transition hover:bg-rose-800"
                  aria-label={`${field.name} Bewaesserung leeren`}
                >
                  <GiPlantWatering />
                </button>
              </>
            }
          />
        ))}
      </div>
    )
  })()

  return (
    <section className="relative max-w-5xl">
      <div className="relative p-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="mb-4 text-4xl font-semibold text-slate-900 sm:text-5xl">
            Oberlenghof
          </h1>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-400">
            Anlagen Uebersicht
          </p>
        </div>

        {content}
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
