import { useEffect, useMemo, useRef, useState } from 'react'

import { FiMoreVertical } from 'react-icons/fi'
import type { IconType } from 'react-icons'
import { LuArrowDown, LuCalendarDays, LuRadioTower } from 'react-icons/lu'
import { MdWaterDrop } from 'react-icons/md'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import FieldBox, {
  type FieldBoxMetric,
} from '../components/FieldBox'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildFieldEditAction,
  buildFieldEditInitialValues,
} from '../lib/fieldForm'
import { type FieldOverview } from '../types/generated/api'

type FieldMetricDefinition = {
  key: string
  label: string
  icon: IconType
  unit?: string
  kind?: FieldBoxMetric['kind']
  criticalBelow?: number
  getValue: (field: FieldOverview) => string | number | null | undefined
}

const fieldMetricDefinitions: FieldMetricDefinition[] = [
  {
    key: 'effective_root_depth_cm',
    label: 'Wurzeltiefe',
    icon: LuArrowDown,
    unit: 'cm',
    kind: 'number',
    getValue: (field) => field.effective_root_depth_cm,
  },
  {
    key: 'reference_station',
    label: 'Station',
    icon: LuRadioTower,
    kind: 'text',
    getValue: (field) => field.reference_station,
  },
  {
    key: 'safe_ratio',
    label: 'Wasserbilanz',
    icon: MdWaterDrop,
    unit: '%',
    kind: 'number',
    criticalBelow: 0,
    getValue: (field) => (field.safe_ratio === null ? null : Math.round(field.safe_ratio * 100)),
  },
  {
    key: 'last_irrigation_date',
    label: 'Letzte Bewaesserung',
    icon: LuCalendarDays,
    kind: 'date',
    getValue: (field) => field.last_irrigation_date,
  },
]

function buildFieldMetrics(field: FieldOverview): FieldBoxMetric[] {
  return fieldMetricDefinitions.flatMap((definition) => {
    const value = definition.getValue(field)
    if (value === null || value === undefined || value === '') {
      return []
    }

    return [{
      label: definition.label,
      icon: definition.icon,
      value,
      unit: definition.unit,
      kind: definition.kind,
      criticalBelow: definition.criticalBelow,
    }]
  })
}

function buildSubtitle(field: FieldOverview) {
  return [
    field.section ? `${field.section}` : null,
    `${field.variety}`,
  ]
    .filter((part): part is string => part !== null)
    .join(' ')
}

type FieldActionsMenuProps = {
  field: FieldOverview
  onRefresh: (field: FieldOverview) => Promise<void>
  onClearIrrigation: (field: FieldOverview) => Promise<void>
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
        aria-label={`${field.name} Aktionen`}
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
  const [fields, setFields] = useState<FieldOverview[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [editingField, setEditingField] = useState<FieldOverview | null>(null)
  const [showOnlyFieldsWithStatus, setShowOnlyFieldsWithStatus] = useState(true)

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

  const visibleFields = useMemo(
    () =>
      fields.filter((field) => {
        if (!field.active) {
          return false
        }

        if (!showOnlyFieldsWithStatus) {
          return true
        }

        return field.safe_ratio !== null
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
        <div className="mt-6 rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:mt-8 sm:px-6 sm:py-10">
          Loading fields...
        </div>
      )
    }

    if (errorMessage !== null) {
      return (
        <div className="mt-6 rounded-[1.75rem] border border-rose-200 bg-rose-50 px-5 py-8 text-center text-rose-700 sm:mt-8 sm:px-6 sm:py-10">
          {errorMessage}
        </div>
      )
    }

    if (fields.length === 0) {
      return (
        <div className="mt-6 rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:mt-8 sm:px-6 sm:py-10">
          No fields are configured yet.
        </div>
      )
    }

      return (
      <>
        <label className="mt-6 flex w-full items-start gap-3 rounded-[1.5rem] border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700 shadow-sm sm:mt-8 sm:inline-flex sm:w-auto sm:items-center sm:rounded-full sm:px-5 sm:py-3">
          <input
            type="checkbox"
            checked={showOnlyFieldsWithStatus}
            onChange={(event) => setShowOnlyFieldsWithStatus(event.target.checked)}
            className="mt-0.5 h-5 w-5 rounded border-slate-300 text-sky-600 focus:ring-sky-500 sm:mt-0"
          />
          <span>
            <span className="block font-medium text-slate-900">Nur Anlagen mit Status anzeigen</span>
          </span>
        </label>

        {visibleFields.length === 0 ? (
          <div className="mt-6 rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:px-6 sm:py-10">
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
                  <FieldActionsMenu
                    field={field}
                    onRefresh={handleRefreshField}
                    onClearIrrigation={handleClearIrrigation}
                  />
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
    </section>
  )
}
