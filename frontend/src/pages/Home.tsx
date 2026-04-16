import { useEffect, useMemo, useRef, useState } from 'react'

import { FiMoreVertical } from 'react-icons/fi'
import type { IconType } from 'react-icons'
import { LuArrowDown, LuCalendarDays, LuRadioTower } from 'react-icons/lu'
import { MdWaterDrop } from 'react-icons/md'
import { FaArrowRight } from 'react-icons/fa'
import { IoMdAdd } from 'react-icons/io'
import { Link } from 'react-router-dom'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import FieldBox, {
  type FieldBoxMetric,
} from '../components/FieldBox'
import { irrigationCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildFieldEditAction,
  buildFieldEditInitialValues,
} from '../lib/fieldForm'
import { type FieldGroupedOverview, type FieldOverview } from '../types/generated/api'

type AggregationLevel = FieldGroupedOverview['aggregation_level']

type FieldMetricDefinition = {
  key: string
  label: string
  icon: IconType
  unit?: string
  kind?: FieldBoxMetric['kind']
  criticalBelow?: number
  emptyValueLabel?: string
  getValue: (field: FieldGroupedOverview) => string | number | null | undefined
}

const fieldMetricDefinitions: FieldMetricDefinition[] = [
  {
    key: 'effective_root_depth_display',
    label: 'Wurzeltiefe',
    icon: LuArrowDown,
    kind: 'text',
    getValue: (field) => field.effective_root_depth_display,
  },
  {
    key: 'reference_station_display',
    label: 'Station',
    icon: LuRadioTower,
    kind: 'text',
    getValue: (field) => field.reference_station_display,
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
      field.safe_ratio === null || field.safe_ratio === undefined
        ? null
        : Math.round(field.safe_ratio * 100),
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

const aggregationOptions: Array<{ value: AggregationLevel; label: string }> = [
  { value: 'field', label: 'Feld' },
  { value: 'field_variety', label: 'Feld + Sorte' },
  { value: 'section', label: 'Abschnitt' },
]

function buildFieldMetrics(field: FieldGroupedOverview): FieldBoxMetric[] {
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

type FieldActionsMenuProps = {
  field: FieldGroupedOverview
  onRefresh: (field: FieldGroupedOverview) => Promise<void>
  onClearIrrigation: (field: FieldGroupedOverview) => Promise<void>
}

function FieldActionsMenu({
  field,
  onRefresh,
  onClearIrrigation,
}: FieldActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (menuRef.current?.contains(event.target as Node)) {
        return
      }

      setIsOpen(false)
    }

    window.addEventListener('pointerdown', handlePointerDown)
    return () => window.removeEventListener('pointerdown', handlePointerDown)
  }, [isOpen])

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={(event) => {
          event.preventDefault()
          event.stopPropagation()
          setIsOpen((currentState) => !currentState)
        }}
        className="inline-flex h-10 w-10 items-center justify-center text-slate-600 transition hover:border hover:border-slate-300 hover:text-slate-900"
        aria-label={`${field.title} Aktionen`}
        aria-expanded={isOpen}
      >
        <FiMoreVertical className="h-5 w-5" />
      </button>

      {isOpen ? (
        <div className="absolute right-0 top-full z-30 mt-2 min-w-56 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              setIsOpen(false)
              void onRefresh(field)
            }}
            className="flex w-full rounded-xl px-4 py-1 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:text-slate-900"
          >
            Wasserbilanz aktualisieren
          </button>
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              setIsOpen(false)
              void onClearIrrigation(field)
            }}
            className="flex w-full rounded-xl px-4 py-1 text-left text-sm font-medium text-rose-700 transition hover:bg-rose-50 hover:text-rose-800"
          >
            Bewaesserungen löschen
          </button>
        </div>
      ) : null}
    </div>
  )
}

export default function Home() {
  const [fields, setFields] = useState<FieldGroupedOverview[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [editingField, setEditingField] = useState<FieldOverview | null>(null)
  const [irrigationField, setIrrigationField] = useState<FieldGroupedOverview | null>(null)
  const [showOnlyFieldsWithStatus, setShowOnlyFieldsWithStatus] = useState(true)
  const [aggregationLevel, setAggregationLevel] = useState<AggregationLevel>('field')

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const response = await api.get<FieldGroupedOverview[]>('/fields/grouped-overview', {
          params: { level: aggregationLevel },
        })
        if (!Array.isArray(response.data)) {
          throw new TypeError('Expected /fields/grouped-overview to return an array.')
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
  }, [aggregationLevel])

  const editAction = useMemo(() => buildFieldEditAction(editingField), [editingField])

  const editInitialValues = useMemo(
    () => buildFieldEditInitialValues(editingField),
    [editingField],
  )

  const irrigationInitialValues = useMemo(
    () => irrigationField === null
      ? undefined
      : { field_ids: JSON.stringify(irrigationField.field_ids) },
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

        return field.safe_ratio !== null && field.safe_ratio !== undefined
      }),
    [fields, showOnlyFieldsWithStatus],
  )

  // const handleDeleteField = async (field: FieldOverview) => {
  //   const confirmed = window.confirm(`Soll die Anlage "${field.name}" wirklich geloescht werden?`)
  //   if (!confirmed) {
  //     return
  //   }

  //   try {
  //     await api.delete(`/fields/${field.id}`)
  //     notifyDataChanged()
  //   } catch (error) {
  //     console.error(`Error deleting field ${field.id}`, error)
  //     setErrorMessage('Die Anlage konnte nicht geloescht werden.')
  //   }
  // }

  const handleRefreshField = async (field: FieldGroupedOverview) => {
    if (field.field_ids.length === 0) {
      return
    }

    try {
      await Promise.all(
        field.field_ids.map((fieldId) => api.post(`/fields/${fieldId}/water-balance`)),
      )
      notifyDataChanged()
    } catch (error) {
      console.error(`Error refreshing grouped field ${field.title}`, error)
      setErrorMessage('Die Wasserbilanz fuer die Anlagen konnte nicht aktualisiert werden.')
    }
  }

  const handleClearIrrigation = async (field: FieldGroupedOverview) => {
    const confirmed = window.confirm(`Sollen alle Bewaesserungseintraege fuer "${field.title}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await Promise.all(
        field.field_ids.map((fieldId) => api.delete(`/fields/${fieldId}/irrigation`)),
      )
      notifyDataChanged()
    } catch (error) {
      console.error(`Error clearing irrigation for grouped field ${field.title}`, error)
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
          <label className="flex w-full items-start gap-3 border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700 shadow-sm sm:inline-flex sm:w-auto sm:items-center sm:rounded-full sm:px-5 sm:py-3">
            <input
              type="checkbox"
              checked={showOnlyFieldsWithStatus}
              onChange={(event) => setShowOnlyFieldsWithStatus(event.target.checked)}
              className="mt-0.5 h-5 w-5 rounded border-slate-300 text-sky-600 focus:ring-sky-500 sm:mt-0"
            />
            <span className="block font-medium text-slate-900">Nur Anlagen mit Status anzeigen</span>
          </label>

          <div className="inline-flex w-full border border-slate-200 bg-white p-1 shadow-sm sm:w-auto sm:rounded-full">
            {aggregationOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setAggregationLevel(option.value)}
                className={`flex-1 px-4 py-2 text-sm font-semibold transition sm:flex-none sm:rounded-full ${
                  aggregationLevel === option.value
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {visibleFields.length === 0 ? (
          <div className="mt-6 border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:px-6 sm:py-10">
            Keine aktiven Anlagen mit Wasserbilanz gefunden.
          </div>
        ) : (
          <div className="mt-6 grid gap-4 sm:gap-5">
            {visibleFields.map((field) => (
              <FieldBox
                key={`${field.aggregation_level}-${field.field_ids.join('-')}`}
                title={field.title}
                subtitle={field.subtitle ?? undefined}
                metrics={buildFieldMetrics(field)}
                titleAdornment={
                  field.herbicide_free === true ? (
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500"
                      aria-hidden="true"
                    />
                  ) : undefined
                }
                actions={
                  <FieldActionsMenu
                    field={field}
                    onRefresh={handleRefreshField}
                    onClearIrrigation={handleClearIrrigation}
                  />
                }
                footerActions={
                  <>
                    {field.representative_field_id ? (
                      <Link
                        to={`/fields/${field.representative_field_id}`}
                        className="inline-flex items-center gap-1 border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                      >
                        <FaArrowRight className="h-3 w-3" aria-hidden="true" />
                        <span>Wasserbilanz</span>
                      </Link>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => setIrrigationField(field)}
                      className="inline-flex items-center gap-1 border border-sky-200 bg-sky-50 px-2 py-1 text-sm font-semibold text-sky-800 shadow-sm transition hover:border-sky-300 hover:bg-sky-100"
                    >
                      <IoMdAdd className="h-3 w-3" aria-hidden="true" />
                      <span>Bewaesserung</span>
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
        action={editAction}
        isOpen={editingField !== null}
        initialValues={editInitialValues}
        onClose={() => setEditingField(null)}
      />
      <CreateEntityModal
        action={irrigationCreateAction}
        isOpen={irrigationField !== null}
        initialValues={irrigationInitialValues}
        onClose={() => setIrrigationField(null)}
      />
    </section>
  )
}
