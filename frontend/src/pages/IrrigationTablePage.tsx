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
  buildIrrigationEditAction,
  buildIrrigationEditInitialValues,
} from '../lib/irrigationForm'
import type { FieldRead, IrrigationRead } from '../types/generated/api'

type IrrigationColumnKey = 'date' | 'field' | 'group' | 'method' | 'duration' | 'amount'

const visibleIrrigationColumns: IrrigationColumnKey[] = [
  'date',
  'field',
  'group',
  'method',
  'duration',
  'amount',
]

function formatNumber(value: number, digits = 1) {
  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

function formatMethod(value: string) {
  return value === 'drip' ? 'Tropfer' : value === 'overhead' ? 'Oberkrone' : value
}

export default function IrrigationTablePage() {
  const interactiveAreaRef = useRef<HTMLDivElement | null>(null)
  const [events, setEvents] = useState<IrrigationRead[]>([])
  const [fields, setFields] = useState<FieldRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [editingEvent, setEditingEvent] = useState<IrrigationRead | null>(null)
  const [filters, setFilters] = useState({
    fieldId: '',
    method: '',
    dateFrom: '',
    dateTo: '',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [eventsResponse, fieldsResponse] = await Promise.all([
          api.get<IrrigationRead[]>('/irrigation'),
          api.get<FieldRead[]>('/fields'),
        ])

        setEvents(eventsResponse.data)
        setFields(fieldsResponse.data)
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching irrigation table data', error)
        setEvents([])
        setFields([])
        setErrorMessage('Die Bewaesserungsdaten konnten nicht geladen werden.')
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
        setSelectedEventId(null)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const fieldsById = useMemo(
    () =>
      Object.fromEntries(
        fields.map((field) => [
          field.id,
          {
            name: field.name,
            group: field.group,
          },
        ]),
      ),
    [fields],
  )

  const columns = useMemo<DataTableColumn<IrrigationRead>[]>(() => {
    const availableColumns: Record<IrrigationColumnKey, DataTableColumn<IrrigationRead>> = {
      date: {
        id: 'date',
        header: 'Datum',
        cell: (event) => formatDate(event.date),
      },
      field: {
        id: 'field',
        header: 'Anlage',
        cell: (event) => fieldsById[event.field_id]?.name ?? `#${event.field_id}`,
      },
      group: {
        id: 'group',
        header: 'Gruppe',
        cell: (event) => fieldsById[event.field_id]?.group ?? 'n/a',
      },
      method: {
        id: 'method',
        header: 'Methode',
        cell: (event) => formatMethod(event.method),
      },
      duration: {
        id: 'duration',
        header: 'Dauer (h)',
        cell: (event) => formatNumber(event.duration, 1),
      },
      amount: {
        id: 'amount',
        header: 'Menge (mm)',
        cell: (event) => formatNumber(event.amount, 1),
      },
    }

    return visibleIrrigationColumns.map((columnKey) => availableColumns[columnKey])
  }, [fieldsById])

  const tableFilters = useMemo<DataTableFilter[]>(
    () => [
      {
        id: 'fieldId',
        label: 'Anlage',
        type: 'select',
        value: filters.fieldId,
        options: [
          { label: 'Alle', value: '' },
          ...fields
            .slice()
            .sort((left, right) => left.name.localeCompare(right.name, 'de-DE'))
            .map((field) => ({
              label: [field.group, field.name]
                .filter((part) => String(part).trim() !== '')
                .join(' | '),
              value: String(field.id),
            })),
        ],
      },
      {
        id: 'method',
        label: 'Methode',
        type: 'select',
        value: filters.method,
        options: [
          { label: 'Alle', value: '' },
          { label: 'Tropfer', value: 'drip' },
          { label: 'Oberkrone', value: 'overhead' },
        ],
      },
      {
        id: 'dateFrom',
        label: 'Von',
        type: 'date',
        value: filters.dateFrom,
      },
      {
        id: 'dateTo',
        label: 'Bis',
        type: 'date',
        value: filters.dateTo,
      },
    ],
    [fields, filters],
  )

  const filteredEvents = useMemo(() => {
    return [...events]
      .sort((left, right) => right.date.localeCompare(left.date))
      .filter((event) => {
        const matchesField =
          filters.fieldId === '' || event.field_id === Number(filters.fieldId)

        const matchesMethod =
          filters.method === '' || event.method === filters.method

        const matchesDateFrom =
          filters.dateFrom === '' || event.date >= filters.dateFrom

        const matchesDateTo =
          filters.dateTo === '' || event.date <= filters.dateTo

        return matchesField && matchesMethod && matchesDateFrom && matchesDateTo
      })
  }, [events, filters])

  const selectedEvent = useMemo(
    () => filteredEvents.find((event) => event.id === selectedEventId) ?? null,
    [filteredEvents, selectedEventId],
  )

  useEffect(() => {
    if (selectedEventId === null) {
      return
    }

    const stillExists = filteredEvents.some((event) => event.id === selectedEventId)
    if (!stillExists) {
      setSelectedEventId(null)
    }
  }, [filteredEvents, selectedEventId])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      fieldId: '',
      method: '',
      dateFrom: '',
      dateTo: '',
    })
  }

  const handleDeleteEvent = async (event: IrrigationRead) => {
    const fieldName = fieldsById[event.field_id]?.name ?? `#${event.field_id}`
    const confirmed = window.confirm(
      `Soll der Bewaesserungseintrag fuer "${fieldName}" am ${formatDate(event.date)} wirklich geloescht werden?`,
    )
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/irrigation/${event.id}`)
      setSelectedEventId(null)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting irrigation event ${event.id}`, error)
      setErrorMessage('Der Bewaesserungseintrag konnte nicht geloescht werden.')
    }
  }

  const summaryCells = useMemo<DataTableSummaryCell<IrrigationRead>[]>(
    () => [
      {
        columnId: 'field',
        content: 'Summe',
      },
      {
        columnId: 'amount',
        content: (rows) =>
          formatNumber(
            rows.reduce((total, event) => total + event.amount, 0),
            1,
          ),
      },
    ],
    [],
  )

  const editAction = useMemo(
    () => buildIrrigationEditAction(editingEvent),
    [editingEvent],
  )
  const editInitialValues = useMemo(
    () => buildIrrigationEditInitialValues(editingEvent),
    [editingEvent],
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
              Bewaesserung
            </h1>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {filteredEvents.length} / {events.length} Eintraege
          </div>
        </div>

        <div ref={interactiveAreaRef} className="mt-8">
          {selectedEvent ? (
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Ausgewaehlter Eintrag
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {fieldsById[selectedEvent.field_id]?.name ?? `#${selectedEvent.field_id}`}{' '}
                  am {formatDate(selectedEvent.date)}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {formatMethod(selectedEvent.method)} · {formatNumber(selectedEvent.duration, 1)} h ·{' '}
                  {formatNumber(selectedEvent.amount, 1)} mm
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setEditingEvent(selectedEvent)}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-amber-500"
                >
                  <GoPencil />
                  Bearbeiten
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteEvent(selectedEvent)}
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
              Lade Bewaesserungsdaten...
            </div>
          ) : errorMessage ? (
            <div className="rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredEvents}
              getRowKey={(event) => event.id}
              emptyMessage="Keine Bewaesserungseintraege gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              summaryCells={summaryCells}
              selectedRowKey={selectedEventId}
              onRowSelect={(event) => setSelectedEventId(event?.id ?? null)}
            />
          )}
        </div>
      </div>

      <CreateEntityModal
        action={editAction}
        isOpen={editingEvent !== null}
        initialValues={editInitialValues}
        onClose={() => setEditingEvent(null)}
      />
    </section>
  )
}
