import { useCallback, useEffect, useMemo, useState } from 'react'
import { LuRefreshCw, LuSprayCan } from 'react-icons/lu'

import api from '../api'
import DataTable, { type DataTableColumn } from '../components/DataTable'
import { DATA_CHANGED_EVENT } from '../lib/dataEvents'
import {
  type FieldDetailRead,
  type TreatmentEventRead,
} from '../types/generated/api'
import {
  buildScopeOptions,
  CURRENT_SEASON_YEAR,
  fetchFieldDetails,
  formatDate,
  formatMetricValue,
  TREATMENT_TABLE_LIMIT,
  treatmentResolutionBadge,
} from './cropProtectionShared'

export default function SpritzungenPage() {
  const [treatments, setTreatments] = useState<TreatmentEventRead[]>([])
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [treatmentLimit, setTreatmentLimit] = useState(TREATMENT_TABLE_LIMIT)
  const [treatmentLimitInput, setTreatmentLimitInput] = useState(String(TREATMENT_TABLE_LIMIT))

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true)
      const [
        treatmentsResponse,
        fieldDetailResults,
      ] = await Promise.all([
        api.get<TreatmentEventRead[]>('/treatments', {
          params: {
            season_year: CURRENT_SEASON_YEAR,
            limit: treatmentLimit,
          },
        }),
        fetchFieldDetails(),
      ])

      setTreatments(treatmentsResponse.data)
      setFieldDetails(fieldDetailResults)
      setErrorMessage(null)
    } catch (error) {
      console.error('Error loading treatments', error)
      setErrorMessage('Spritzungen konnten nicht geladen werden.')
    } finally {
      setIsLoading(false)
    }
  }, [treatmentLimit])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  useEffect(() => {
    const handleDataChanged = () => {
      void fetchData()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
  }, [fetchData])

  const scopeOptions = useMemo(() => buildScopeOptions(fieldDetails), [fieldDetails])
  const sectionScopeOptions = useMemo(
    () => scopeOptions.filter((option) => option.type === 'section'),
    [scopeOptions],
  )
  const sectionLabelsById = useMemo(
    () => Object.fromEntries(sectionScopeOptions.map((option) => [option.id, option.label])),
    [sectionScopeOptions],
  )

  const treatmentColumns: DataTableColumn<TreatmentEventRead>[] = [
    { id: 'date', header: 'Datum', cell: (row) => formatDate(row.date) },
    { id: 'external-section', header: 'SmartFarmer Anlage', cell: (row) => row.external_section_name },
    {
      id: 'resolution',
      header: 'Zuordnung',
      cell: (row) => treatmentResolutionBadge(row.resolution_status),
    },
    {
      id: 'section',
      header: 'Abschnitt',
      cell: (row) => {
        if (row.section_id === null || row.section_id === undefined) {
          return '-'
        }
        return sectionLabelsById[row.section_id] ?? `Abschnitt ${row.section_id}`
      },
    },
    { id: 'product', header: 'Mittel', cell: (row) => row.product_name },
    { id: 'dose', header: 'Dosis /hl', cell: (row) => formatMetricValue(row.dose_per_hl) },
    { id: 'hl', header: 'hl', cell: (row) => formatMetricValue(row.hl) },
    { id: 'reason', header: 'Grund', cell: (row) => row.reason ?? '-' },
    { id: 'source', header: 'Quelle', cell: (row) => row.source },
  ]

  const handleApplyTreatmentLimit = () => {
    const nextLimit = Math.min(5000, Math.max(1, Number(treatmentLimitInput)))
    if (!Number.isFinite(nextLimit)) {
      setTreatmentLimitInput(String(treatmentLimit))
      return
    }
    const normalizedLimit = Math.trunc(nextLimit)
    setTreatmentLimitInput(String(normalizedLimit))
    setTreatmentLimit(normalizedLimit)
  }

  return (
    <section className="w-full max-w-7xl">
      <div className="px-2 py-4 sm:px-6 sm:py-6 lg:p-8">
        <div className="flex flex-col gap-4 border-b border-black pb-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Pflanzenschutz
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              Spritzungen
            </h1>
          </div>
          <button
            type="button"
            onClick={() => void fetchData()}
            className="inline-flex items-center gap-2 border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <LuRefreshCw className="h-4 w-4" />
            Aktualisieren
          </button>
        </div>

        {errorMessage ? (
          <div className="mt-5 border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <section className="mt-8">
          <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="flex items-center gap-2">
              <LuSprayCan className="h-5 w-5 text-slate-500" />
              <h2 className="text-xl font-semibold text-slate-900">Eingetragene Spritzungen</h2>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <div className="text-sm text-slate-500">
                {treatments.length} von maximal
              </div>
              <label className="block">
                <span className="sr-only">Maximale Anzahl Spritzungen</span>
                <input
                  type="number"
                  min={1}
                  max={5000}
                  step={50}
                  value={treatmentLimitInput}
                  onChange={(event) => setTreatmentLimitInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      handleApplyTreatmentLimit()
                    }
                  }}
                  className="w-24 border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <div className="text-sm text-slate-500">neuesten</div>
              <button
                type="button"
                onClick={handleApplyTreatmentLimit}
                className="border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                Anwenden
              </button>
            </div>
          </div>
          {isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
              Lade Spritzungen...
            </div>
          ) : (
            <div className="max-h-[32rem] overflow-y-auto">
              <DataTable
                columns={treatmentColumns}
                rows={treatments}
                getRowKey={(row) => row.id}
                emptyMessage="Keine Spritzungen vorhanden."
              />
            </div>
          )}
        </section>
      </div>
    </section>
  )
}
