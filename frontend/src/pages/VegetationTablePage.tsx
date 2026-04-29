import { useEffect, useMemo, useRef, useState } from 'react'
import { GoPencil } from 'react-icons/go'
import { IoMdAdd } from 'react-icons/io'
import { PiTrashBold } from 'react-icons/pi'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
} from '../components/DataTable'
import { phenologyCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildPhenologyEditAction,
  buildPhenologyEditInitialValues,
} from '../lib/phenologyForm'
import type {
  FieldDetailRead,
  FieldRead,
  PhenologicalStageDefinition,
  PhenologyEventRead,
} from '../types/generated/api'

type VegetationRow = PhenologyEventRead & {
  fieldId: number
  fieldName: string
  fieldGroup: string
  variety: string
  sectionName: string
  sectionActive: boolean
}

function buildVegetationRows(fieldDetails: FieldDetailRead[]): VegetationRow[] {
  return fieldDetails.flatMap((fieldDetail) =>
    fieldDetail.plantings.flatMap((planting) =>
      planting.sections.flatMap((section) =>
        (section.phenology_events ?? []).map((event) => ({
          ...event,
          fieldId: fieldDetail.field.id,
          fieldName: fieldDetail.field.name,
          fieldGroup: fieldDetail.field.group,
          variety: planting.variety,
          sectionName: section.name,
          sectionActive: section.active,
        })),
      ),
    ),
  )
}

function sortRows(rows: VegetationRow[]) {
  return rows
    .slice()
    .sort((left, right) => {
      const dateCompare = right.date.localeCompare(left.date)
      if (dateCompare !== 0) {
        return dateCompare
      }
      const groupCompare = left.fieldGroup.localeCompare(right.fieldGroup, 'de-DE')
      if (groupCompare !== 0) {
        return groupCompare
      }
      const fieldCompare = left.fieldName.localeCompare(right.fieldName, 'de-DE')
      if (fieldCompare !== 0) {
        return fieldCompare
      }
      const varietyCompare = left.variety.localeCompare(right.variety, 'de-DE')
      if (varietyCompare !== 0) {
        return varietyCompare
      }
      const sectionCompare = left.sectionName.localeCompare(right.sectionName, 'de-DE')
      if (sectionCompare !== 0) {
        return sectionCompare
      }
      return left.stage_name.localeCompare(right.stage_name, 'de-DE')
    })
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

function formatStage(event: PhenologyEventRead) {
  return event.bbch_code === null || event.bbch_code === undefined
    ? event.stage_name
    : `${event.stage_name} (BBCH ${event.bbch_code})`
}

export default function VegetationTablePage() {
  const interactiveAreaRef = useRef<HTMLDivElement | null>(null)
  const [rows, setRows] = useState<VegetationRow[]>([])
  const [fields, setFields] = useState<FieldRead[]>([])
  const [phenologicalStages, setPhenologicalStages] = useState<PhenologicalStageDefinition[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [editingEvent, setEditingEvent] = useState<PhenologyEventRead | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [filters, setFilters] = useState({
    query: '',
    fieldId: '',
    stageCode: '',
    status: 'active',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [fieldsResponse, stagesResponse] = await Promise.all([
          api.get<FieldRead[]>('/fields'),
          api.get<PhenologicalStageDefinition[]>('/phenological-stages'),
        ])
        const detailResponses = await Promise.all(
          fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
        )

        setFields(fieldsResponse.data)
        setPhenologicalStages(
          stagesResponse.data.slice().sort((left, right) => left.sort_order - right.sort_order),
        )
        setRows(buildVegetationRows(detailResponses.map((response) => response.data)))
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching vegetation table data', error)
        setFields([])
        setPhenologicalStages([])
        setRows([])
        setErrorMessage('Die Vegetationsdaten konnten nicht geladen werden.')
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

  const columns = useMemo<DataTableColumn<VegetationRow>[]>(
    () => [
      {
        id: 'date',
        header: 'Datum',
        cell: (row) => formatDate(row.date),
      },
      {
        id: 'field',
        header: 'Anlage',
        cell: (row) => row.fieldName,
      },
      {
        id: 'group',
        header: 'Gruppe',
        cell: (row) => row.fieldGroup,
      },
      {
        id: 'variety',
        header: 'Pflanzung',
        cell: (row) => row.variety,
      },
      {
        id: 'section',
        header: 'Abschnitt',
        cell: (row) => row.sectionName,
      },
      {
        id: 'stage',
        header: 'Stadium',
        cell: (row) => formatStage(row),
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
        placeholder: 'Anlage, Gruppe, Pflanzung, Abschnitt oder Stadium',
      },
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
              label: field.name,
              value: String(field.id),
            })),
        ],
      },
      {
        id: 'stageCode',
        label: 'Stadium',
        type: 'select',
        value: filters.stageCode,
        options: [
          { label: 'Alle', value: '' },
          ...phenologicalStages.map((stage) => ({
            label: stage.bbch_code === null || stage.bbch_code === undefined
              ? stage.label
              : `${stage.label} (BBCH ${stage.bbch_code})`,
            value: stage.code,
          })),
        ],
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
    ],
    [fields, filters, phenologicalStages],
  )

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return sortRows(rows).filter((row) => {
      const matchesQuery =
        normalizedQuery === '' ||
        [
          row.fieldName,
          row.fieldGroup,
          row.variety,
          row.sectionName,
          row.stage_name,
          row.stage_code,
          row.date,
        ]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery)

      const matchesField = filters.fieldId === '' || row.fieldId === Number(filters.fieldId)
      const matchesStage = filters.stageCode === '' || row.stage_code === filters.stageCode
      const matchesStatus =
        filters.status === '' ||
        (filters.status === 'active' ? row.sectionActive : !row.sectionActive)

      return matchesQuery && matchesField && matchesStage && matchesStatus
    })
  }, [filters, rows])

  const selectedEvent = useMemo(
    () => filteredRows.find((row) => row.id === selectedEventId) ?? null,
    [filteredRows, selectedEventId],
  )

  useEffect(() => {
    if (selectedEventId === null) {
      return
    }

    const stillExists = filteredRows.some((row) => row.id === selectedEventId)
    if (!stillExists) {
      setSelectedEventId(null)
    }
  }, [filteredRows, selectedEventId])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      fieldId: '',
      stageCode: '',
      status: 'active',
    })
  }

  const handleDeleteEvent = async (event: VegetationRow) => {
    const confirmed = window.confirm(
      `Soll der Phaenologieeintrag "${formatStage(event)}" fuer "${event.fieldName}" am ${formatDate(event.date)} wirklich geloescht werden?`,
    )
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/phenology-events/${event.id}`)
      setSelectedEventId(null)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting phenology event ${event.id}`, error)
      setErrorMessage('Der Phaenologieeintrag konnte nicht geloescht werden.')
    }
  }

  const editAction = useMemo(
    () => buildPhenologyEditAction(editingEvent),
    [editingEvent],
  )
  const editInitialValues = useMemo(
    () => buildPhenologyEditInitialValues(editingEvent),
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
              Vegetation
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800 transition hover:bg-sky-100"
            >
              <IoMdAdd />
              Phaenologie
            </button>
            <div className="border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {filteredRows.length} / {rows.length} Eintraege
            </div>
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
                  {selectedEvent.fieldName} am {formatDate(selectedEvent.date)}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {selectedEvent.sectionName} | {formatStage(selectedEvent)}
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
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
              Lade Vegetationsdaten...
            </div>
          ) : errorMessage ? (
            <div className="border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredRows}
              getRowKey={(row) => row.id}
              emptyMessage="Keine Phaenologieeintraege gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              selectedRowKey={selectedEventId}
              onRowSelect={(row) => setSelectedEventId(row?.id ?? null)}
            />
          )}
        </div>
      </div>

      <CreateEntityModal
        action={phenologyCreateAction}
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
      <CreateEntityModal
        action={editAction}
        isOpen={editingEvent !== null}
        initialValues={editInitialValues}
        onClose={() => setEditingEvent(null)}
      />
    </section>
  )
}
