import { useEffect, useMemo, useState } from 'react'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import FieldBox, {
  type FieldBoxMetric,
  type FieldBoxStatusBar,
} from '../components/FieldBox'
import { fieldCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import type { CreateActionConfig } from '../types/createActions'
import { type FieldOverview } from '../types/field'

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
    { label: 'Wurzeltiefe', value: `${formatNumber(field.root_depth_cm)} cm` },
    { label: 'Humusgehalt', value: `${formatNumber(field.humus_pct, 1)} %` },
    {
      label: 'Wasserdefizit',
      value: formatOptionalNumber(field.current_deficit, 'mm', 1),
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
  return `${field.reference_provider}: ${field.reference_station}`
}

function PencilIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L8.25 18.463 4 20l1.537-4.25L16.862 3.487Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 5.25 18.75 9" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 7.5h15" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.75h4.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l.818 10.227A2.25 2.25 0 0 0 9.81 19.5h4.38a2.25 2.25 0 0 0 2.242-1.773L17.25 7.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 10.5v5.25M13.5 10.5v5.25" />
    </svg>
  )
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
        setFields(response.data)
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching fields', error)
        setErrorMessage('Fields could not be loaded.')
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

  const editAction = useMemo<CreateActionConfig | null>(() => {
    if (editingField === null) {
      return null
    }

    return {
      ...fieldCreateAction,
      title: 'Anlage bearbeiten',
      submitLabel: 'Anlage speichern',
      endpoint: `/fields/${editingField.id}`,
      method: 'put',
    }
  }, [editingField])

  const editInitialValues = useMemo<Record<string, string> | undefined>(() => {
    if (editingField === null) {
      return undefined
    }

    return {
      name: editingField.name,
      reference_provider: editingField.reference_provider,
      reference_station: editingField.reference_station,
      area_ha: String(editingField.area_ha ?? ''),
      soil_type: editingField.soil_type,
      humus_pct: String(editingField.humus_pct),
      root_depth_cm: String(editingField.root_depth_cm),
      p_allowable: String(editingField.p_allowable),
    }
  }, [editingField])

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
            subtitle={`Bodenart: ${field.soil_type}`}
            statusBar={buildSafeRatioBar(field)}
            metrics={buildFieldMetrics(field)}
            to={`/fields/${field.id}`}
            actions={
              <>
                <button
                  type="button"
                  onClick={() => setEditingField(field)}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-amber-400 text-slate-950 shadow-sm transition hover:bg-amber-500"
                  aria-label={`${field.name} bearbeiten`}
                >
                  <PencilIcon />
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteField(field)}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-rose-600 text-white shadow-sm transition hover:bg-rose-700"
                  aria-label={`${field.name} loeschen`}
                >
                  <TrashIcon />
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
      <div className="relative rounded-3xl border border-slate-200/70 bg-white/70 p-8 shadow-xl backdrop-blur">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-400">
            Anlagen Uebersicht
          </p>
          <h1 className="mt-4 text-4xl font-semibold text-slate-900 sm:text-5xl">
            Oberlenghof
          </h1>
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
