import { useEffect, useMemo, useRef, useState } from 'react'
import { GoPencil } from 'react-icons/go'
import { IoMdAdd } from 'react-icons/io'
import { PiTrashBold } from 'react-icons/pi'

import api from '../api'
import DataTable, {
  type DataTableColumn,
  type DataTableFilter,
  type DataTableSummaryCell,
} from '../components/DataTable'
import FruitCountSurveyModal from '../components/FruitCountSurveyModal'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildScopeLookup,
  getScopeKindLabel,
  resolveScope,
  type ScopeInfo,
} from '../lib/scopeLabels'
import type {
  FieldDetailRead,
  FieldRead,
  FruitCountSurveyRead,
} from '../types/generated/api'

type FruitCountRow = FruitCountSurveyRead & {
  scope: ScopeInfo
  sampleCount: number
  sampleTotal: number
  sampleMean: number | null
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

function summarizeSurvey(survey: FruitCountSurveyRead) {
  const counts = (survey.samples ?? []).map((sample) => sample.apple_count)
  const total = counts.reduce((sum, count) => sum + count, 0)
  return {
    sampleCount: counts.length,
    sampleTotal: total,
    sampleMean: counts.length === 0 ? null : total / counts.length,
  }
}

function buildRows(surveys: FruitCountSurveyRead[], fieldDetails: FieldDetailRead[]) {
  const scopeLookup = buildScopeLookup(fieldDetails)
  return surveys.map((survey) => ({
    ...survey,
    ...summarizeSurvey(survey),
    scope: resolveScope(survey, scopeLookup),
  }))
}

function sortRows(rows: FruitCountRow[]) {
  return rows.slice().sort((left, right) => {
    const dateCompare = right.date.localeCompare(left.date)
    if (dateCompare !== 0) {
      return dateCompare
    }
    const fieldCompare = left.scope.fieldName.localeCompare(right.scope.fieldName, 'de-DE')
    if (fieldCompare !== 0) {
      return fieldCompare
    }
    return left.id - right.id
  })
}

export default function FruitCountsTablePage() {
  const interactiveAreaRef = useRef<HTMLDivElement | null>(null)
  const [surveys, setSurveys] = useState<FruitCountSurveyRead[]>([])
  const [fields, setFields] = useState<FieldRead[]>([])
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectedSurveyId, setSelectedSurveyId] = useState<number | null>(null)
  const [editingSurvey, setEditingSurvey] = useState<FruitCountSurveyRead | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [filters, setFilters] = useState({
    query: '',
    fieldId: '',
    seasonYear: '',
    timingCode: '',
    aggregation: '',
    dateFrom: '',
    dateTo: '',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [surveysResponse, fieldsResponse] = await Promise.all([
          api.get<FruitCountSurveyRead[]>('/fruit-counts/surveys'),
          api.get<FieldRead[]>('/fields'),
        ])
        const detailResponses = await Promise.all(
          fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
        )

        setSurveys(surveysResponse.data)
        setFields(fieldsResponse.data)
        setFieldDetails(detailResponses.map((response) => response.data))
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching fruit count table data', error)
        setSurveys([])
        setFields([])
        setFieldDetails([])
        setErrorMessage('Die Zaehlungen konnten nicht geladen werden.')
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
        setSelectedSurveyId(null)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const rows = useMemo(() => buildRows(surveys, fieldDetails), [fieldDetails, surveys])
  const yearOptions = useMemo(
    () =>
      [...new Set(surveys.map((survey) => survey.season_year))]
        .sort((left, right) => right - left)
        .map((year) => ({ label: String(year), value: String(year) })),
    [surveys],
  )
  const timingOptions = useMemo(
    () =>
      [...new Set(surveys.map((survey) => survey.timing_code).filter(Boolean))]
        .sort((left, right) => left.localeCompare(right, 'de-DE'))
        .map((timingCode) => ({ label: timingCode, value: timingCode })),
    [surveys],
  )

  const columns = useMemo<DataTableColumn<FruitCountRow>[]>(
    () => [
      {
        id: 'date',
        header: 'Datum',
        cell: (row) => formatDate(row.date),
        sortValue: (row) => row.date,
      },
      {
        id: 'season_year',
        header: 'Jahr',
        cell: (row) => row.season_year,
      },
      {
        id: 'field',
        header: 'Anlage',
        cell: (row) => row.scope.fieldName,
        sortValue: (row) => row.scope.fieldName,
      },
      {
        id: 'group',
        header: 'Gruppe',
        cell: (row) => row.scope.fieldGroup,
        sortValue: (row) => row.scope.fieldGroup,
      },
      {
        id: 'scope',
        header: 'Ebene',
        cell: (row) => getScopeKindLabel(row.scope.kind),
        sortValue: (row) => getScopeKindLabel(row.scope.kind),
      },
      {
        id: 'scopeLabel',
        header: 'Bezug',
        cell: (row) => row.scope.label,
        sortValue: (row) => row.scope.label,
      },
      {
        id: 'timing_code',
        header: 'Zeitpunkt',
        cell: (row) => row.timing_code,
      },
      {
        id: 'sampleCount',
        header: 'Proben',
        cell: (row) => formatNumber(row.sampleCount, 0),
        sortValue: (row) => row.sampleCount,
      },
      {
        id: 'sampleMean',
        header: 'Mittel',
        cell: (row) => formatNumber(row.sampleMean, 1),
        sortValue: (row) => row.sampleMean,
      },
      {
        id: 'sampleTotal',
        header: 'Summe',
        cell: (row) => formatNumber(row.sampleTotal, 0),
        sortValue: (row) => row.sampleTotal,
      },
      {
        id: 'method',
        header: 'Methode',
        cell: (row) => row.method ?? 'n/a',
      },
      {
        id: 'include_in_aggregation',
        header: 'Aggregation',
        cell: (row) => (row.include_in_aggregation ? 'Ja' : 'Nein'),
        sortValue: (row) => row.include_in_aggregation,
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
        placeholder: 'Anlage, Gruppe, Bezug, Zeitpunkt, Methode',
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
        id: 'seasonYear',
        label: 'Jahr',
        type: 'select',
        value: filters.seasonYear,
        options: [{ label: 'Alle', value: '' }, ...yearOptions],
      },
      {
        id: 'timingCode',
        label: 'Zeitpunkt',
        type: 'select',
        value: filters.timingCode,
        options: [{ label: 'Alle', value: '' }, ...timingOptions],
      },
      {
        id: 'aggregation',
        label: 'Aggregation',
        type: 'select',
        value: filters.aggregation,
        options: [
          { label: 'Alle', value: '' },
          { label: 'Ja', value: 'true' },
          { label: 'Nein', value: 'false' },
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
    [fields, filters, timingOptions, yearOptions],
  )

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase()

    return sortRows(rows).filter((row) => {
      const matchesQuery =
        normalizedQuery === '' ||
        [
          row.scope.fieldName,
          row.scope.fieldGroup,
          row.scope.label,
          getScopeKindLabel(row.scope.kind),
          row.timing_code,
          row.method ?? '',
          row.observer ?? '',
          row.notes ?? '',
          row.date,
          String(row.season_year),
        ]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery)

      const matchesField = filters.fieldId === '' || row.scope.fieldId === Number(filters.fieldId)
      const matchesYear = filters.seasonYear === '' || row.season_year === Number(filters.seasonYear)
      const matchesTiming = filters.timingCode === '' || row.timing_code === filters.timingCode
      const matchesAggregation =
        filters.aggregation === '' ||
        row.include_in_aggregation === (filters.aggregation === 'true')
      const matchesDateFrom = filters.dateFrom === '' || row.date >= filters.dateFrom
      const matchesDateTo = filters.dateTo === '' || row.date <= filters.dateTo

      return (
        matchesQuery &&
        matchesField &&
        matchesYear &&
        matchesTiming &&
        matchesAggregation &&
        matchesDateFrom &&
        matchesDateTo
      )
    })
  }, [filters, rows])

  const selectedSurvey = useMemo(
    () => filteredRows.find((row) => row.id === selectedSurveyId) ?? null,
    [filteredRows, selectedSurveyId],
  )

  useEffect(() => {
    if (selectedSurveyId === null) {
      return
    }

    const stillExists = filteredRows.some((row) => row.id === selectedSurveyId)
    if (!stillExists) {
      setSelectedSurveyId(null)
    }
  }, [filteredRows, selectedSurveyId])

  const handleFilterChange = (filterId: string, value: string) => {
    setFilters((current) => ({ ...current, [filterId]: value }))
  }

  const handleResetFilters = () => {
    setFilters({
      query: '',
      fieldId: '',
      seasonYear: '',
      timingCode: '',
      aggregation: '',
      dateFrom: '',
      dateTo: '',
    })
  }

  const handleDeleteSurvey = async (survey: FruitCountRow) => {
    const confirmed = window.confirm(
      `Soll die Zaehlung fuer "${survey.scope.fieldName}" vom ${formatDate(survey.date)} wirklich geloescht werden?`,
    )
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/fruit-counts/surveys/${survey.id}`)
      setSelectedSurveyId(null)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting fruit count survey ${survey.id}`, error)
      setErrorMessage('Die Zaehlung konnte nicht geloescht werden.')
    }
  }

  const summaryCells = useMemo<DataTableSummaryCell<FruitCountRow>[]>(
    () => [
      {
        columnId: 'date',
        content: 'Summe',
      },
      {
        columnId: 'sampleCount',
        content: (activeRows) =>
          formatNumber(
            activeRows.reduce((total, row) => total + row.sampleCount, 0),
            0,
          ),
      },
      {
        columnId: 'sampleTotal',
        content: (activeRows) =>
          formatNumber(
            activeRows.reduce((total, row) => total + row.sampleTotal, 0),
            0,
          ),
      },
    ],
    [],
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
              Zaehlungen
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-2 border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800 transition hover:bg-sky-100"
            >
              <IoMdAdd />
              Zaehlung
            </button>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {filteredRows.length} / {rows.length} Eintraege
            </div>
          </div>
        </div>

        <div ref={interactiveAreaRef} className="mt-8">
          {selectedSurvey ? (
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border border-slate-200 bg-slate-50 px-4 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Ausgewaehlter Eintrag
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-900">
                  {selectedSurvey.scope.fieldName} am {formatDate(selectedSurvey.date)}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {selectedSurvey.timing_code} | {selectedSurvey.sampleCount} Proben | Mittel{' '}
                  {formatNumber(selectedSurvey.sampleMean, 1)}
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setEditingSurvey(selectedSurvey)}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-amber-500"
                >
                  <GoPencil />
                  Bearbeiten
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteSurvey(selectedSurvey)}
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
              Lade Zaehlungen...
            </div>
          ) : errorMessage ? (
            <div className="rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {errorMessage}
            </div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredRows}
              getRowKey={(row) => row.id}
              emptyMessage="Keine Zaehlungen gefunden."
              filters={tableFilters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              summaryCells={summaryCells}
              selectedRowKey={selectedSurveyId}
              onRowSelect={(row) => setSelectedSurveyId(row?.id ?? null)}
            />
          )}
        </div>
      </div>

      <FruitCountSurveyModal
        isOpen={isCreateOpen}
        fieldDetails={fieldDetails}
        onClose={() => setIsCreateOpen(false)}
      />
      <FruitCountSurveyModal
        isOpen={editingSurvey !== null}
        survey={editingSurvey}
        fieldDetails={fieldDetails}
        onClose={() => setEditingSurvey(null)}
      />
    </section>
  )
}
