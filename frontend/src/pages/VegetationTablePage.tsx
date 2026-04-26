import { useEffect, useMemo, useState } from 'react'
import { IoMdAdd } from 'react-icons/io'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
} from '../components/DataTable'
import { phenologyCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT } from '../lib/dataEvents'
import type { FieldDetailRead, FieldRead, PhenologicalStageDefinition } from '../types/generated/api'

type SectionReadFromDetail = FieldDetailRead['plantings'][number]['sections'][number]

type VegetationRow = {
  id: number
  fieldId: number
  fieldName: string
  fieldGroup: string
  variety: string
  sectionName: string
  active: boolean
  currentPhenology: string | null | undefined
  phenologyDatesByStageCode: Record<string, string>
}

function buildPhenologyDatesByStageCode(events: SectionReadFromDetail['phenology_events']) {
  const datesByStageCode: Record<string, string> = {}

  for (const event of events ?? []) {
    const existingDate = datesByStageCode[event.stage_code]
    if (existingDate === undefined || event.date > existingDate) {
      datesByStageCode[event.stage_code] = event.date
    }
  }

  return datesByStageCode
}

function buildVegetationRows(fieldDetails: FieldDetailRead[]): VegetationRow[] {
  return fieldDetails.flatMap((fieldDetail) =>
    fieldDetail.plantings.flatMap((planting) =>
      planting.sections.map((section) => ({
        id: section.id,
        fieldId: fieldDetail.field.id,
        fieldName: fieldDetail.field.name,
        fieldGroup: fieldDetail.field.group,
        variety: planting.variety,
        sectionName: section.name,
        active: section.active,
        currentPhenology: section.current_phenology,
        phenologyDatesByStageCode: buildPhenologyDatesByStageCode(section.phenology_events),
      })),
    ),
  )
}

function sortRows(rows: VegetationRow[]) {
  return rows
    .slice()
    .sort((left, right) => {
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
      return left.sectionName.localeCompare(right.sectionName, 'de-DE')
    })
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return '-'
  }

  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

export default function VegetationTablePage() {
  const [rows, setRows] = useState<VegetationRow[]>([])
  const [fields, setFields] = useState<FieldRead[]>([])
  const [phenologicalStages, setPhenologicalStages] = useState<PhenologicalStageDefinition[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [filters, setFilters] = useState({
    query: '',
    fieldId: '',
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

  const columns = useMemo<DataTableColumn<VegetationRow>[]>(
    () => [
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
        id: 'phenology',
        header: 'Phänologie',
        cell: (row) => row.currentPhenology ?? '-',
      },
      ...phenologicalStages.map((stage): DataTableColumn<VegetationRow> => ({
        id: `stage_${stage.code}`,
        header: stage.label,
        cell: (row) => formatDate(row.phenologyDatesByStageCode[stage.code]),
      })),
    ],
    [phenologicalStages],
  )

  const tableFilters = useMemo<DataTableFilter[]>(
    () => [
      {
        id: 'query',
        label: 'Suche',
        type: 'text',
        value: filters.query,
        placeholder: 'Anlage, Gruppe, Pflanzung oder Abschnitt',
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
              label: [field.group, field.name]
                .filter((part) => String(part).trim() !== '')
                .join(' | '),
              value: String(field.id),
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
    [fields, filters],
  )

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return sortRows(rows).filter((row) => {
      const matchesQuery =
        normalizedQuery === '' ||
        [row.fieldName, row.fieldGroup, row.variety, row.sectionName, row.currentPhenology ?? '']
          .concat(Object.values(row.phenologyDatesByStageCode))
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery)

      const matchesField = filters.fieldId === '' || row.fieldId === Number(filters.fieldId)
      const matchesStatus =
        filters.status === '' ||
        (filters.status === 'active' ? row.active : !row.active)

      return matchesQuery && matchesField && matchesStatus
    })
  }, [filters, rows])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      fieldId: '',
      status: 'active',
    })
  }

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
              Phänologie
            </button>
            <div className="border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {filteredRows.length} / {rows.length} Eintraege
            </div>
          </div>
        </div>

        <div className="mt-8">
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
              emptyMessage="Keine Abschnitte gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
            />
          )}
        </div>
      </div>

      <CreateEntityModal
        action={phenologyCreateAction}
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </section>
  )
}
