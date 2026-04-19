import { useEffect, useMemo, useState } from 'react'

import type { IconType } from 'react-icons'
import { LuArrowDown, LuCalendarDays, LuRadioTower, LuTrees } from 'react-icons/lu'
import { MdWaterDrop } from 'react-icons/md'
import { FaArrowRight } from 'react-icons/fa'
import { IoMdAdd } from 'react-icons/io'
import { Link } from 'react-router-dom'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import FieldBox, { type FieldBoxMetric } from '../components/FieldBox'
import { irrigationCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import { type FieldSummaryRead } from '../types/generated/api'

type FieldMetricDefinition = {
  key: string
  label: string
  icon: IconType
  unit?: string
  kind?: FieldBoxMetric['kind']
  criticalBelow?: number
  emptyValueLabel?: string
  getValue: (field: FieldSummaryRead) => string | number | null | undefined
}

const fieldMetricDefinitions: FieldMetricDefinition[] = [
  {
    key: 'effective_root_depth_display',
    label: 'Wurzeltiefe',
    icon: LuArrowDown,
    kind: 'text',
    getValue: (field) => field.effective_root_depth_cm === null || field.effective_root_depth_cm === undefined
      ? null
      : `${Math.round(field.effective_root_depth_cm)} cm`,
  },
  {
    key: 'reference_station_display',
    label: 'Station',
    icon: LuRadioTower,
    kind: 'text',
    getValue: (field) => field.reference_station,
  },
  {
    key: 'tree_count',
    label: 'Baumzahl',
    icon: LuTrees,
    kind: 'number',
    getValue: (field) => field.tree_count,
  },
  {
    key: 'safe_ratio',
    label: 'Wasserbilanz',
    icon: MdWaterDrop,
    unit: '%',
    kind: 'number',
    criticalBelow: 0,
    emptyValueLabel: '-',
    getValue: (field) =>
      field.water_balance_summary.safe_ratio === null || field.water_balance_summary.safe_ratio === undefined
        ? null
        : Math.round(field.water_balance_summary.safe_ratio * 100),
  },
  {
    key: 'last_irrigation_date',
    label: 'Letzte Bewaesserung',
    icon: LuCalendarDays,
    kind: 'date',
    emptyValueLabel: '-',
    getValue: (field) => field.last_irrigation_date,
  },
]

function buildFieldMetrics(field: FieldSummaryRead): FieldBoxMetric[] {
  return fieldMetricDefinitions.flatMap((definition) => {
    const value = definition.getValue(field)
    if ((value === null || value === undefined || value === '') && definition.emptyValueLabel === undefined) {
      return []
    }

    return [{
      label: definition.label,
      icon: definition.icon,
      value: value === null || value === undefined || value === '' ? definition.emptyValueLabel ?? '' : value,
      unit: definition.unit,
      kind: definition.kind,
      criticalBelow: definition.criticalBelow,
      tooltip: definition.label,
    }]
  })
}

function buildSubtitle(field: FieldSummaryRead) {
  const varietyText = field.variety_names.length === 0
    ? 'Keine Sorte'
    : field.variety_names.join(', ')

  return [
    field.group,
    `Sorte: ${varietyText}`,
    field.section_count > 0 ? `${field.section_count} Abschnitte` : null,
  ]
    .filter((value): value is string => value !== null)
    .join('\n')
}

export default function Home() {
  const [fields, setFields] = useState<FieldSummaryRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [irrigationField, setIrrigationField] = useState<FieldSummaryRead | null>(null)
  const [showOnlyFieldsWithStatus, setShowOnlyFieldsWithStatus] = useState(true)

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
        console.error('Error fetching field summaries', error)
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

  const irrigationInitialValues = useMemo(
    () => irrigationField === null
      ? undefined
      : { field_ids: JSON.stringify([irrigationField.id]) },
    [irrigationField],
  )

  const visibleFields = useMemo(
    () =>
      fields.filter((field) => {
        if (!field.active) {
          return false
        }

        if (!showOnlyFieldsWithStatus) {
          return true
        }

        return field.water_balance_summary.safe_ratio !== null && field.water_balance_summary.safe_ratio !== undefined
      }),
    [fields, showOnlyFieldsWithStatus],
  )

  const handleRefreshField = async (field: FieldSummaryRead) => {
    try {
      await api.post(`/fields/${field.id}/water-balance`)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error refreshing field ${field.id}`, error)
      setErrorMessage('Die Wasserbilanz konnte nicht aktualisiert werden.')
    }
  }

  const handleClearIrrigation = async (field: FieldSummaryRead) => {
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
        <div className="mt-6 border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:mt-8 sm:px-6 sm:py-10">
          Loading fields...
        </div>
      )
    }

    if (errorMessage !== null) {
      return (
        <div className="mt-6 border border-rose-200 bg-rose-50 px-5 py-8 text-center text-rose-700 sm:mt-8 sm:px-6 sm:py-10">
          {errorMessage}
        </div>
      )
    }

    if (fields.length === 0) {
      return (
        <div className="mt-6 border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:mt-8 sm:px-6 sm:py-10">
          No fields are configured yet.
        </div>
      )
    }

    return (
      <>
        <div className="mt-6 flex flex-col gap-3 sm:mt-8 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex w-full items-start gap-3 border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700 shadow-sm sm:inline-flex sm:w-auto sm:items-center sm:px-5 sm:py-3">
            <input
              type="checkbox"
              checked={showOnlyFieldsWithStatus}
              onChange={(event) => setShowOnlyFieldsWithStatus(event.target.checked)}
              className="mt-0.5 h-5 w-5 rounded border-slate-300 text-sky-600 focus:ring-sky-500 sm:mt-0"
            />
            <span className="block font-medium text-slate-900">Nur Anlagen mit Status anzeigen</span>
          </label>
        </div>

        {visibleFields.length === 0 ? (
          <div className="mt-6 border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:px-6 sm:py-10">
            Keine aktiven Anlagen mit Wasserbilanz gefunden.
          </div>
        ) : (
          <div className="mt-6 grid gap-4 sm:gap-5">
            {visibleFields.map((field) => (
              <FieldBox
                key={field.id}
                title={field.name}
                subtitle={buildSubtitle(field)}
                metrics={buildFieldMetrics(field)}
                titleAdornment={
                  field.herbicide_free === true ? (
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500"
                      aria-hidden="true"
                    />
                  ) : undefined
                }
                footerActions={
                  <>
                    <Link
                      to={`/fields/${field.id}`}
                      className="inline-flex items-center gap-1 border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                    >
                      <FaArrowRight className="h-3 w-3" aria-hidden="true" />
                      <span>Details</span>
                    </Link>
                    <button
                      type="button"
                      onClick={() => setIrrigationField(field)}
                      className="inline-flex items-center gap-1 border border-sky-200 bg-sky-50 px-2 py-1 text-sm font-semibold text-sky-800 shadow-sm transition hover:border-sky-300 hover:bg-sky-100"
                    >
                      <IoMdAdd className="h-3 w-3" aria-hidden="true" />
                      <span>Bewaesserung</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleRefreshField(field)}
                      className="inline-flex items-center gap-1 border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                    >
                      Wasserbilanz
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleClearIrrigation(field)}
                      className="inline-flex items-center gap-1 border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 shadow-sm transition hover:border-rose-300 hover:bg-rose-100 hover:text-rose-800"
                    >
                      Bewaesserung loeschen
                    </button>
                  </>
                }
              />
            ))}
          </div>
        )}
      </>
    )
  })()

  return (
    <section className="relative max-w-5xl">
      <div className="relative px-1 py-2 sm:px-0 lg:p-8">
        <div className="max-w-2xl text-left sm:mx-auto sm:text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
            Anlagen Uebersicht
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:mt-4 sm:text-5xl">
            Oberlenghof
          </h1>
        </div>

        {content}
      </div>

      <CreateEntityModal
        action={irrigationCreateAction}
        isOpen={irrigationField !== null}
        initialValues={irrigationInitialValues}
        onClose={() => setIrrigationField(null)}
      />
    </section>
  )
}
