import { useEffect, useMemo, useRef, useState } from 'react'

import type { IconType } from 'react-icons'
import { FiMoreVertical, FiX } from 'react-icons/fi'
import { LuArrowDown, LuCalendarDays, LuClock, LuRadioTower, LuTrees } from 'react-icons/lu'
import { MdWaterDrop } from 'react-icons/md'
import { FaArrowRight } from 'react-icons/fa'
import { IoMdAdd } from 'react-icons/io'
import { Link } from 'react-router-dom'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import CropProtectionStatusLayer from '../components/CropProtectionStatusLayer'
import FieldBox, { type FieldBoxMetric } from '../components/FieldBox'
import WaterBalanceChart from '../components/WaterBalanceChart'
import { irrigationCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  type CropProtectionFieldSummaryRead,
  type CropProtectionRuleRead,
  type FieldDetailRead,
  type FieldSummaryRead,
  type WaterBalanceSeriesPoint,
  type WaterBalanceSeriesResponse,
} from '../types/generated/api'

const FORECAST_DAYS = 5

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

type WaterBalanceModalState = {
  field: FieldSummaryRead
  data: WaterBalanceSeriesPoint[]
  workflowMessages: string[]
  isLoading: boolean
  errorMessage: string | null
}

type FieldPhenologyEvent = {
  id: number
  sectionName: string
  variety: string
  stageName: string
  date: string
}

type CropProtectionRuleChip = {
  rule: CropProtectionRuleRead
  dueCount: number
  soonCount: number
  affectedCount: number
}

type WeatherCacheState = {
  label: string
  isStale: boolean
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

function formatDate(value: string) {
  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function getWeatherCacheState(summaries: CropProtectionFieldSummaryRead[]): WeatherCacheState {
  const timestamps = summaries
    .map((summary) => summary.weather_updated_at)
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .map((value) => new Date(value))
    .filter((value) => !Number.isNaN(value.getTime()))

  if (timestamps.length === 0) {
    return { label: 'unbekannt', isStale: true }
  }

  const oldestTimestamp = timestamps.reduce((oldest, current) =>
    current.getTime() < oldest.getTime() ? current : oldest,
  )

  return {
    label: formatDateTime(oldestTimestamp.toISOString()),
    isStale: Date.now() - oldestTimestamp.getTime() > 24 * 60 * 60 * 1000,
  }
}

function buildPhenologyEventsByFieldId(fieldDetails: FieldDetailRead[]) {
  return Object.fromEntries(
    fieldDetails.map((fieldDetail) => [
      fieldDetail.field.id,
      fieldDetail.plantings
        .flatMap((planting) =>
          planting.sections.flatMap((section) =>
            (section.phenology_events ?? []).map((event) => ({
              id: event.id,
              sectionName: section.name,
              variety: planting.variety,
              stageName: event.stage_name,
              date: event.date,
            })),
          ),
        )
        .sort((left, right) => right.date.localeCompare(left.date)),
    ]),
  ) as Record<number, FieldPhenologyEvent[]>
}

function hasRuleAlert(summary: CropProtectionFieldSummaryRead | undefined, ruleId: number) {
  return (summary?.evaluations ?? []).some(
    (evaluation) =>
      evaluation.rule_id === ruleId &&
      (evaluation.status === 'due' || evaluation.status === 'soon'),
  )
}

function FieldPhenologyTooltip({ events }: { events: FieldPhenologyEvent[] | undefined }) {
  const visibleEvents = events ?? []

  if (visibleEvents.length === 0) {
    return <div className="text-slate-500">Keine Phänologieereignisse erfasst.</div>
  }

  return (
    <div>
      <div className="mb-2 text-caption font-semibold uppercase tracking-[0.18em] text-slate-500">
        Phänologie
      </div>
      <div className="max-h-64 overflow-y-auto pr-1">
        {visibleEvents.map((event) => (
          <div key={event.id} className="grid grid-cols-[5.5rem_1fr] gap-1 border-t border-slate-100 py-2 first:border-t-0 first:pt-0">
            <div className="font-semibold text-slate-900">{formatDate(event.date)}</div>
            <div className="min-w-0">
              <div className="font-medium text-slate-800">{event.stageName}</div>
              <div className="truncate text-slate-500">
                {event.variety} | {event.sectionName}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FieldActionsMenu({
  field,
  onRefresh,
  onClearIrrigation,
}: {
  field: FieldSummaryRead
  onRefresh: (field: FieldSummaryRead) => Promise<void>
  onClearIrrigation: (field: FieldSummaryRead) => Promise<void>
}) {
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
        <div className="absolute right-0 top-full z-30 mt-2 min-w-56 border border-slate-200 bg-white p-2 shadow-xl">
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              setIsOpen(false)
              void onRefresh(field)
            }}
            className="flex w-full px-4 py-2 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:text-slate-900"
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
            className="flex w-full px-4 py-2 text-left text-sm font-medium text-rose-700 transition hover:bg-rose-50 hover:text-rose-800"
          >
            Bewaesserungen loeschen
          </button>
        </div>
      ) : null}
    </div>
  )
}

function WaterBalanceModal({
  state,
  onClose,
}: {
  state: WaterBalanceModalState | null
  onClose: () => void
}) {
  if (state === null) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-sm sm:flex sm:items-center sm:justify-center sm:px-4 sm:py-4"
      onClick={onClose}
    >
      <div
        className="flex h-dvh w-full flex-col overflow-hidden bg-white sm:max-h-[calc(100vh-2rem)] sm:max-w-6xl sm:border sm:border-slate-200 sm:shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-100 px-4 py-4 sm:px-6 sm:pt-6 sm:pb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              Wasserbilanz
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900">
              {state.field.name}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            aria-label="Popup schliessen"
          >
            <FiX className="h-5 w-5" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3 sm:px-6 sm:py-6">
          {state.isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
              Lade Wasserbilanz...
            </div>
          ) : state.errorMessage ? (
            <div className="border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {state.errorMessage}
            </div>
          ) : (
            <div className="space-y-3">
              {state.workflowMessages.length > 0 ? (
                <div className="border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  {state.workflowMessages.map((message) => (
                    <div key={message}>{message}</div>
                  ))}
                </div>
              ) : null}
              <WaterBalanceChart data={state.data} reservedForecastDays={FORECAST_DAYS} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const [fields, setFields] = useState<FieldSummaryRead[]>([])
  const [phenologyEventsByFieldId, setPhenologyEventsByFieldId] = useState<Record<number, FieldPhenologyEvent[]>>({})
  const [cropProtectionByFieldId, setCropProtectionByFieldId] = useState<Record<number, CropProtectionFieldSummaryRead>>({})
  const [cropProtectionRules, setCropProtectionRules] = useState<CropProtectionRuleRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [irrigationField, setIrrigationField] = useState<FieldSummaryRead | null>(null)
  const [waterBalanceModal, setWaterBalanceModal] = useState<WaterBalanceModalState | null>(null)
  const [selectedRuleId, setSelectedRuleId] = useState<number | null>(null)

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const response = await api.get<FieldSummaryRead[]>('/fields/summary')
        if (!Array.isArray(response.data)) {
          throw new TypeError('Expected /fields/summary to return an array.')
        }
        const [detailResponses, cropProtectionResponse, cropProtectionRulesResponse] = await Promise.all([
          Promise.all(
            response.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
          ),
          api.get<CropProtectionFieldSummaryRead[]>('/crop-protection/field-summaries'),
          api.get<CropProtectionRuleRead[]>('/crop-protection/rules'),
        ])
        const cropProtectionGroups = cropProtectionResponse.data.reduce<Record<number, CropProtectionFieldSummaryRead>>(
          (groups, summary) => {
            groups[summary.field_id] = summary
            return groups
          },
          {},
        )
        setFields(response.data)
        setPhenologyEventsByFieldId(
          buildPhenologyEventsByFieldId(detailResponses.map((detailResponse) => detailResponse.data)),
        )
        setCropProtectionByFieldId(cropProtectionGroups)
        setCropProtectionRules(cropProtectionRulesResponse.data)
        setErrorMessage(null)
      } catch (error) {
        console.error('Error fetching field summaries', error)
        setErrorMessage('Fields could not be loaded.')
        setFields([])
        setPhenologyEventsByFieldId({})
        setCropProtectionByFieldId({})
        setCropProtectionRules([])
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

        if (selectedRuleId === null) {
          return true
        }

        return hasRuleAlert(cropProtectionByFieldId[field.id], selectedRuleId)
      }).sort(function (a, b) {
          if (a.name < b.name) {
            return -1;
          }
          if (a.name > b.name) {
            return 1;
          }
          return 0;
        }),
    [cropProtectionByFieldId, fields, selectedRuleId],
  )

  const ruleChips = useMemo<CropProtectionRuleChip[]>(() => {
    const activeFields = fields.filter((field) => field.active)
    return cropProtectionRules
      .filter((rule) => rule.enabled)
      .map((rule) => {
        let dueCount = 0
        let soonCount = 0

        for (const field of activeFields) {
          const evaluations = cropProtectionByFieldId[field.id]?.evaluations ?? []
          const statuses = evaluations
            .filter((evaluation) => evaluation.rule_id === rule.id)
            .map((evaluation) => evaluation.status)

          if (statuses.includes('due')) {
            dueCount += 1
          } else if (statuses.includes('soon')) {
            soonCount += 1
          }
        }

        return {
          rule,
          dueCount,
          soonCount,
          affectedCount: dueCount + soonCount,
        }
      })
  }, [cropProtectionByFieldId, cropProtectionRules, fields])

  const weatherCacheState = useMemo(
    () => getWeatherCacheState(Object.values(cropProtectionByFieldId)),
    [cropProtectionByFieldId],
  )

  const selectedRuleName = useMemo(
    () => cropProtectionRules.find((rule) => rule.id === selectedRuleId)?.name ?? null,
    [cropProtectionRules, selectedRuleId],
  )

  const toggleRuleFilter = (ruleId: number) => {
    setSelectedRuleId((currentRuleId) => currentRuleId === ruleId ? null : ruleId)
  }

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

  const handleOpenWaterBalance = async (field: FieldSummaryRead) => {
    setWaterBalanceModal({
      field,
      data: [],
      workflowMessages: [],
      isLoading: true,
      errorMessage: null,
    })

    try {
      const response = await api.get<WaterBalanceSeriesResponse>(
        `/fields/${field.id}/water-balance/series`,
        {
          params: { forecast_days: FORECAST_DAYS },
        },
      )
      const workflowMessages = [
        ...(response.data.warnings ?? []).map((warning) => warning.message),
        ...(response.data.errors ?? []).map((error) => error.message),
      ]
      const data = response.data.data ?? []
      setWaterBalanceModal({
        field,
        data,
        workflowMessages,
        isLoading: false,
        errorMessage: data.length === 0 && workflowMessages.length === 0 ? 'Keine Wasserbilanzdaten vorhanden.' : null,
      })
    } catch (error) {
      console.error(`Error fetching water balance for field ${field.id}`, error)
      setWaterBalanceModal({
        field,
        data: [],
        workflowMessages: [],
        isLoading: false,
        errorMessage: 'Die Wasserbilanz konnte nicht geladen werden.',
      })
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
        {ruleChips.length > 0 ? (
          <div className="mt-6 sm:mt-8">
            <div className="flex flex-wrap gap-2">
              {ruleChips.map((chip) => {
                const isSelected = selectedRuleId === chip.rule.id
                const alertClass = chip.dueCount > 0
                  ? 'border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100'
                  : chip.soonCount > 0
                    ? 'border-amber-200 bg-amber-50 text-amber-900 hover:bg-amber-100'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'

                return (
                  <button
                    key={chip.rule.id}
                    type="button"
                    onClick={() => toggleRuleFilter(chip.rule.id)}
                    className={`inline-flex max-w-full items-center gap-2 border px-2.5 py-1.5 text-xs font-semibold shadow-sm transition ${
                      isSelected ? 'ring-2 ring-sky-400 ring-offset-2' : ''
                    } ${alertClass}`}
                    aria-pressed={isSelected}
                    title={chip.rule.name}
                  >
                    <span className="truncate">{chip.rule.name}</span>
                    <span className="inline-flex min-w-6 justify-center border border-current/20 bg-white/70 px-1.5 py-0.5 text-caption leading-none">
                      {chip.affectedCount}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        ) : null}

        {visibleFields.length === 0 ? (
          <div className="mt-6 border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-slate-500 sm:px-6 sm:py-10">
            {selectedRuleName === null
              ? 'Keine aktiven Anlagen gefunden.'
              : `Keine aktiven Anlagen mit faelliger oder bald faelliger Regel "${selectedRuleName}" gefunden.`}
          </div>
        ) : (
          <div className="mt-6 grid grid-cols-1 gap-4 pb-80 sm:gap-5 lg:grid-cols-[repeat(auto-fill,minmax(24rem,1fr))]">
            {visibleFields.map((field) => (
              <FieldBox
                key={field.id}
                title={field.name}
                subtitle={buildSubtitle(field)}
                stageIcon={LuTrees}
                stageLabel={field.current_phenology ?? '-'}
                stageTooltipContent={<FieldPhenologyTooltip events={phenologyEventsByFieldId[field.id]} />}
                metrics={buildFieldMetrics(field)}
                detailContent={
                  <CropProtectionStatusLayer
                    evaluations={cropProtectionByFieldId[field.id]?.evaluations ?? []}
                    weatherUpdatedAt={cropProtectionByFieldId[field.id]?.weather_updated_at}
                  />
                }
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
                    {field.water_balance_summary.as_of ? (
                      <button
                        type="button"
                        onClick={() => void handleOpenWaterBalance(field)}
                        className="inline-flex items-center gap-1 border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                      >
                        Wasserbilanz
                      </button>
                    ) : null}
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
    <section className="relative w-full max-w-7xl">
      <div className="relative px-1 py-2 sm:px-0 lg:p-8">
        <div className="max-w-2xl text-left sm:mx-auto sm:text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
            Anlagen Uebersicht
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:mt-4 sm:text-5xl">
            Oberlenghof
          </h1>
          <div
            className={`mt-4 inline-flex items-center gap-2 border px-3 py-1.5 text-xs font-semibold ${
              weatherCacheState.isStale
                ? 'border-rose-200 bg-rose-50 text-rose-800'
                : 'border-emerald-200 bg-emerald-50 text-emerald-800'
            }`}
          >
            <LuClock className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Wetterdaten: {weatherCacheState.label}</span>
          </div>
        </div>

        {content}
      </div>

      <CreateEntityModal
        action={irrigationCreateAction}
        isOpen={irrigationField !== null}
        initialValues={irrigationInitialValues}
        onClose={() => setIrrigationField(null)}
      />
      <WaterBalanceModal
        state={waterBalanceModal}
        onClose={() => setWaterBalanceModal(null)}
      />
    </section>
  )
}
