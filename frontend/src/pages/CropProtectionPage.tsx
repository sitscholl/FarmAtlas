import { useEffect, useMemo, useState } from 'react'
import { LuLink2, LuListChecks, LuPencil, LuPlus, LuRefreshCw, LuSprayCan, LuTrash2 } from 'react-icons/lu'

import api from '../api'
import DataTable, { type DataTableColumn } from '../components/DataTable'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import { getApiErrorMessage } from '../lib/apiErrors'
import {
  type CropProtectionRuleCreate,
  type CropProtectionRuleMetricBase,
  type CropProtectionRuleRead,
  type CropProtectionRuleScopeBase,
  type FieldDetailRead,
  type FieldRead,
  type TreatmentEventRead,
  type TreatmentSectionAliasRead,
} from '../types/generated/api'

type ScopeType = CropProtectionRuleScopeBase['scope_type']
type MetricType = CropProtectionRuleMetricBase['metric_type']

type ScopeOption = {
  key: string
  type: ScopeType
  id: number
  label: string
}

type RuleFormMetricState = {
  enabled: boolean
  threshold: string
  warningThreshold: string
  baseTemperature: string
}

type RuleFormState = {
  id: number | null
  name: string
  enabled: boolean
  logic: 'any' | 'all'
  seasonStart: string
  seasonEnd: string
  notes: string
  productsText: string
  scopes: CropProtectionRuleScopeBase[]
  metricInputs: Record<MetricType, RuleFormMetricState>
}

const metricTypes: MetricType[] = ['days_since', 'rain_since', 'gdd_since']
const SMARTFARMER_SOURCE = 'smartfarmer'
const CURRENT_SEASON_YEAR = new Date().getFullYear()
const TREATMENT_TABLE_LIMIT = 300

const emptyMetricInputs: Record<MetricType, RuleFormMetricState> = {
  days_since: { enabled: true, threshold: '7', warningThreshold: '5', baseTemperature: '10' },
  rain_since: { enabled: false, threshold: '25', warningThreshold: '20', baseTemperature: '10' },
  gdd_since: { enabled: false, threshold: '100', warningThreshold: '80', baseTemperature: '10' },
}

const emptyRuleForm: RuleFormState = {
  id: null,
  name: '',
  enabled: true,
  logic: 'any',
  seasonStart: '',
  seasonEnd: '',
  notes: '',
  productsText: '',
  scopes: [],
  metricInputs: emptyMetricInputs,
}

const metricLabels: Record<MetricType, string> = {
  days_since: 'Tage',
  rain_since: 'Regen',
  gdd_since: 'GDD',
}

const treatmentResolutionLabels: Record<string, string> = {
  resolved: 'Zugeordnet',
  unresolved: 'Offen',
}

const treatmentResolutionClasses: Record<string, string> = {
  resolved: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  unresolved: 'border-amber-200 bg-amber-50 text-amber-900',
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return '-'
  }
  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

function formatMetricValue(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '-'
  }
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 }).format(value)
}

function cloneMetricInputs(inputs: Record<MetricType, RuleFormMetricState>) {
  return Object.fromEntries(
    metricTypes.map((metricType) => [metricType, { ...inputs[metricType] }]),
  ) as Record<MetricType, RuleFormMetricState>
}

function buildScopeOptions(fieldDetails: FieldDetailRead[]): ScopeOption[] {
  return fieldDetails.flatMap((fieldDetail) => {
    const fieldOption: ScopeOption = {
      key: `field-${fieldDetail.field.id}`,
      type: 'field',
      id: fieldDetail.field.id,
      label: fieldDetail.field.name,
    }

    const plantingOptions = fieldDetail.plantings.map((planting) => ({
      key: `planting-${planting.id}`,
      type: 'planting' as const,
      id: planting.id,
      label: `${fieldDetail.field.name} | ${planting.variety}`,
    }))

    const sectionOptions = fieldDetail.plantings.flatMap((planting) =>
      planting.sections.map((section) => ({
        key: `section-${section.id}`,
        type: 'section' as const,
        id: section.id,
        label: `${fieldDetail.field.name} | ${planting.variety} | ${section.name}`,
      })),
    )

    return [fieldOption, ...plantingOptions, ...sectionOptions]
  })
}

function buildRuleForm(rule: CropProtectionRuleRead): RuleFormState {
  const metricInputs = cloneMetricInputs(emptyMetricInputs)
  for (const metric of rule.metrics) {
    const metricConfig = metric.metric_config ?? {}
    metricInputs[metric.metric_type] = {
      enabled: metric.enabled ?? true,
      threshold: String(metric.threshold),
      warningThreshold: metric.warning_threshold === null || metric.warning_threshold === undefined
        ? ''
        : String(metric.warning_threshold),
      baseTemperature: typeof metricConfig.base_temperature === 'number'
        ? String(metricConfig.base_temperature)
        : '10',
    }
  }

  return {
    id: rule.id,
    name: rule.name,
    enabled: rule.enabled,
    logic: rule.logic,
    seasonStart: rule.season_start ?? '',
    seasonEnd: rule.season_end ?? '',
    notes: rule.notes ?? '',
    productsText: rule.products.map((product) => product.product_name).join('\n'),
    scopes: rule.scopes.map((scope) => ({ scope_type: scope.scope_type, scope_id: scope.scope_id })),
    metricInputs,
  }
}

function parseProducts(value: string) {
  return Array.from(
    new Set(
      value
        .split(/[\n,]+/)
        .map((product) => product.trim())
        .filter((product) => product !== ''),
    ),
  )
}

function buildRulePayload(form: RuleFormState): CropProtectionRuleCreate {
  const metrics = metricTypes.map((metricType) => {
    const input = form.metricInputs[metricType]
    const metricConfig = metricType === 'gdd_since'
      ? { base_temperature: Number(input.baseTemperature || 10) }
      : {}

    return {
      metric_type: metricType,
      enabled: input.enabled,
      threshold: Number(input.threshold),
      warning_threshold: input.warningThreshold.trim() === '' ? null : Number(input.warningThreshold),
      metric_config: metricConfig,
    }
  })

  return {
    name: form.name.trim(),
    enabled: form.enabled,
    logic: form.logic,
    season_start: form.seasonStart || null,
    season_end: form.seasonEnd || null,
    notes: form.notes.trim() || null,
    product_names: parseProducts(form.productsText),
    scopes: form.scopes,
    metrics,
  }
}

function treatmentResolutionBadge(status: string) {
  return (
    <span className={`inline-flex border px-2 py-1 text-xs font-semibold ${treatmentResolutionClasses[status] ?? treatmentResolutionClasses.unresolved}`}>
      {treatmentResolutionLabels[status] ?? status}
    </span>
  )
}

export default function CropProtectionPage() {
  const [rules, setRules] = useState<CropProtectionRuleRead[]>([])
  const [treatments, setTreatments] = useState<TreatmentEventRead[]>([])
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [productNames, setProductNames] = useState<string[]>([])
  const [aliases, setAliases] = useState<TreatmentSectionAliasRead[]>([])
  const [unresolvedNames, setUnresolvedNames] = useState<string[]>([])
  const [aliasSelections, setAliasSelections] = useState<Record<string, string>>({})
  const [form, setForm] = useState<RuleFormState>(emptyRuleForm)
  const [selectedScopeKeys, setSelectedScopeKeys] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isAliasSubmitting, setIsAliasSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [aliasMessage, setAliasMessage] = useState<string | null>(null)
  const [aliasErrorMessage, setAliasErrorMessage] = useState<string | null>(null)
  const [treatmentLimit, setTreatmentLimit] = useState(TREATMENT_TABLE_LIMIT)
  const [treatmentLimitInput, setTreatmentLimitInput] = useState(String(TREATMENT_TABLE_LIMIT))

  const fetchData = async () => {
    try {
      setIsLoading(true)
      const [
        rulesResponse,
        treatmentsResponse,
        fieldsResponse,
        productsResponse,
        unresolvedResponse,
        aliasesResponse,
      ] = await Promise.all([
        api.get<CropProtectionRuleRead[]>('/crop-protection/rules'),
        api.get<TreatmentEventRead[]>('/treatments', {
          params: {
            season_year: CURRENT_SEASON_YEAR,
            limit: treatmentLimit,
          },
        }),
        api.get<FieldRead[]>('/fields'),
        api.get<string[]>('/treatments/products'),
        api.get<string[]>('/treatments/unresolved-sections', {
          params: { season_year: CURRENT_SEASON_YEAR },
        }),
        api.get<TreatmentSectionAliasRead[]>('/treatments/section-aliases'),
      ])
      const detailResponses = await Promise.all(
        fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
      )

      setRules(rulesResponse.data)
      setTreatments(treatmentsResponse.data)
      setFieldDetails(detailResponses.map((response) => response.data))
      setProductNames(productsResponse.data)
      setUnresolvedNames(unresolvedResponse.data)
      setAliases(aliasesResponse.data)
      setErrorMessage(null)
    } catch (error) {
      console.error('Error loading crop protection data', error)
      setErrorMessage('Pflanzenschutzdaten konnten nicht geladen werden.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void fetchData()
  }, [treatmentLimit])

  useEffect(() => {
    const handleDataChanged = () => {
      void fetchData()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
  }, [treatmentLimit])

  const scopeOptions = useMemo(() => buildScopeOptions(fieldDetails), [fieldDetails])
  const sectionScopeOptions = useMemo(
    () => scopeOptions.filter((option) => option.type === 'section'),
    [scopeOptions],
  )
  const sectionLabelsById = useMemo(
    () => Object.fromEntries(sectionScopeOptions.map((option) => [option.id, option.label])),
    [sectionScopeOptions],
  )
  const scopeLabelsByKey = useMemo(
    () => Object.fromEntries(scopeOptions.map((option) => [option.key, option.label])),
    [scopeOptions],
  )

  const treatmentColumns: DataTableColumn<TreatmentEventRead>[] = [
    { id: 'date', header: 'Datum', cell: (row) => formatDate(row.date) },
    { id: 'external-section', header: 'Smartfarmer Anlage', cell: (row) => row.external_section_name },
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

  const handleSelectRule = (rule: CropProtectionRuleRead) => {
    setForm(buildRuleForm(rule))
    setSelectedScopeKeys([])
  }

  const handleNewRule = () => {
    setForm({
      ...emptyRuleForm,
      metricInputs: cloneMetricInputs(emptyMetricInputs),
    })
    setSelectedScopeKeys([])
  }

  const selectedScopeSet = useMemo(() => new Set(selectedScopeKeys), [selectedScopeKeys])
  const addedScopeKeySet = useMemo(
    () => new Set(form.scopes.map((scope) => `${scope.scope_type}-${scope.scope_id}`)),
    [form.scopes],
  )

  const handleToggleScopeSelection = (scopeKey: string) => {
    setSelectedScopeKeys((currentKeys) =>
      currentKeys.includes(scopeKey)
        ? currentKeys.filter((key) => key !== scopeKey)
        : [...currentKeys, scopeKey],
    )
  }

  const handleSelectAllSections = () => {
    setSelectedScopeKeys(
      sectionScopeOptions
        .map((option) => option.key)
        .filter((key) => !addedScopeKeySet.has(key)),
    )
  }

  const handleAddSelectedScopes = () => {
    const selectedOptions = sectionScopeOptions.filter((option) => selectedScopeSet.has(option.key))
    if (selectedOptions.length === 0) {
      return
    }

    setForm((currentForm) => {
      const currentScopeKeys = new Set(currentForm.scopes.map((scope) => `${scope.scope_type}-${scope.scope_id}`))
      const nextScopes = selectedOptions
        .filter((option) => !currentScopeKeys.has(option.key))
        .map((option) => ({ scope_type: option.type, scope_id: option.id }))

      return {
        ...currentForm,
        scopes: [...currentForm.scopes, ...nextScopes],
      }
    })
    setSelectedScopeKeys([])
  }

  const handleSaveRule = async () => {
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      const payload = buildRulePayload(form)
      if (form.id === null) {
        await api.post('/crop-protection/rules', payload)
      } else {
        await api.put(`/crop-protection/rules/${form.id}`, payload)
      }
      notifyDataChanged()
      await fetchData()
      handleNewRule()
    } catch (error) {
      console.error('Error saving crop protection rule', error)
      setErrorMessage('Die Pflanzenschutzregel konnte nicht gespeichert werden.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteRule = async () => {
    if (form.id === null) {
      return
    }
    const confirmed = window.confirm(`Soll die Regel "${form.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }
    setIsSubmitting(true)
    try {
      await api.delete(`/crop-protection/rules/${form.id}`)
      notifyDataChanged()
      await fetchData()
      handleNewRule()
    } catch (error) {
      console.error('Error deleting crop protection rule', error)
      setErrorMessage('Die Pflanzenschutzregel konnte nicht geloescht werden.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSaveAlias = async (externalSectionName: string) => {
    const sectionId = Number(aliasSelections[externalSectionName])
    if (!Number.isFinite(sectionId) || sectionId <= 0) {
      setAliasErrorMessage('Bitte zuerst einen Farm Atlas Abschnitt auswaehlen.')
      return
    }

    setIsAliasSubmitting(true)
    setAliasMessage(null)
    setAliasErrorMessage(null)
    try {
      await api.post('/treatments/section-aliases', {
        source: SMARTFARMER_SOURCE,
        external_section_name: externalSectionName,
        section_id: sectionId,
      })
      setAliasSelections((currentSelections) => {
        const nextSelections = { ...currentSelections }
        delete nextSelections[externalSectionName]
        return nextSelections
      })
      setAliasMessage('Smartfarmer Zuordnung gespeichert.')
      notifyDataChanged()
      await fetchData()
    } catch (error) {
      console.error('Error saving treatment section alias', error)
      setAliasErrorMessage(getApiErrorMessage(error, 'Die Smartfarmer Zuordnung konnte nicht gespeichert werden.'))
    } finally {
      setIsAliasSubmitting(false)
    }
  }

  const handleDeleteAlias = async (alias: TreatmentSectionAliasRead) => {
    setIsAliasSubmitting(true)
    setAliasMessage(null)
    setAliasErrorMessage(null)
    try {
      await api.delete(`/treatments/section-aliases/${alias.id}`)
      setAliasMessage('Smartfarmer Zuordnung geloescht.')
      notifyDataChanged()
      await fetchData()
    } catch (error) {
      console.error('Error deleting treatment section alias', error)
      setAliasErrorMessage(getApiErrorMessage(error, 'Die Smartfarmer Zuordnung konnte nicht geloescht werden.'))
    } finally {
      setIsAliasSubmitting(false)
    }
  }

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

  const handleMetricChange = (
    metricType: MetricType,
    updates: Partial<RuleFormMetricState>,
  ) => {
    setForm((currentForm) => ({
      ...currentForm,
      metricInputs: {
        ...currentForm.metricInputs,
        [metricType]: {
          ...currentForm.metricInputs[metricType],
          ...updates,
        },
      },
    }))
  }

  const aliasManagementPanel = (
    <div className="min-w-0 border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <h3 className="text-lg font-semibold text-slate-900">Smartfarmer Zuordnung</h3>
        <span className="border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-600">
          {unresolvedNames.length} offen
        </span>
      </div>
      {aliasErrorMessage ? (
        <div className="mt-3 border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {aliasErrorMessage}
        </div>
      ) : null}
      {aliasMessage ? (
        <div className="mt-3 border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {aliasMessage}
        </div>
      ) : null}

      <div className="mt-4">
        <div className="text-sm font-semibold text-slate-900">Offene Anlagen</div>
        <div className="mt-2 grid gap-2">
          {unresolvedNames.length === 0 ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
              Keine offenen Smartfarmer Anlagen.
            </div>
          ) : (
            unresolvedNames.map((externalName) => (
              <div key={externalName} className="border border-slate-200 bg-slate-50 p-3">
                <div className="break-words text-sm font-semibold text-slate-900">{externalName}</div>
                <div className="mt-2 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                  <select
                    value={aliasSelections[externalName] ?? ''}
                    onChange={(event) =>
                      setAliasSelections((currentSelections) => ({
                        ...currentSelections,
                        [externalName]: event.target.value,
                      }))
                    }
                    className="w-full border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <option value="">Abschnitt auswaehlen</option>
                    {sectionScopeOptions.map((option) => (
                      <option key={option.key} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => void handleSaveAlias(externalName)}
                    disabled={isAliasSubmitting}
                    className="inline-flex items-center justify-center border border-sky-700 bg-sky-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  >
                    Zuordnen
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="mt-5">
        <div className="text-sm font-semibold text-slate-900">Bestehende Zuordnungen</div>
        <div className="mt-2 grid gap-2">
          {aliases.length === 0 ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
              Keine Smartfarmer Zuordnungen vorhanden.
            </div>
          ) : (
            aliases.map((alias) => (
              <div
                key={alias.id}
                className="grid gap-2 border border-slate-200 bg-white p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-slate-900">
                    {alias.external_section_name}
                  </div>
                  <div className="mt-1 truncate text-sm text-slate-500">
                    {sectionLabelsById[alias.section_id] ?? `Abschnitt ${alias.section_id}`}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void handleDeleteAlias(alias)}
                  disabled={isAliasSubmitting}
                  className="inline-flex items-center justify-center gap-1 border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 disabled:opacity-60"
                >
                  <LuTrash2 className="h-4 w-4" />
                  Loeschen
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )

  return (
    <section className="w-full max-w-7xl">
      <div className="px-2 py-4 sm:px-6 sm:py-6 lg:p-8">
        <div className="flex flex-col gap-4 border-b border-black pb-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Pflanzenschutz
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              Planung und Regeln
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

        <div className="mt-8 mb-3 flex items-center gap-2">
          <LuListChecks className="h-5 w-5 text-slate-500" />
          <h2 className="text-xl font-semibold text-slate-900">Pflanzenschutz Regeln</h2>
        </div>
        <section className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="min-w-0 border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <h2 className="text-xl font-semibold text-slate-900">Bestehende Regeln</h2>
              <button
                type="button"
                onClick={handleNewRule}
                className="inline-flex items-center gap-1 border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800"
              >
                <LuPlus className="h-4 w-4" />
                Neu
              </button>
            </div>
            <div className="mt-3 grid gap-2">
              {rules.length === 0 ? (
                <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                  Keine Regeln vorhanden.
                </div>
              ) : (
                rules.map((rule) => (
                  <button
                    key={rule.id}
                    type="button"
                    onClick={() => handleSelectRule(rule)}
                    className={`border px-4 py-3 text-left transition hover:bg-slate-50 ${
                      form.id === rule.id ? 'border-slate-900 bg-slate-50' : 'border-slate-200 bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{rule.name}</div>
                        <div className="mt-1 text-sm text-slate-500">
                          {rule.products.length} Produkte | {rule.scopes.length} Bereiche
                        </div>
                      </div>
                      <span className={`text-xs font-semibold ${rule.enabled ? 'text-emerald-700' : 'text-slate-400'}`}>
                        {rule.enabled ? 'Aktiv' : 'Inaktiv'}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="min-w-0 border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <h2 className="text-xl font-semibold text-slate-900">
                {form.id === null ? 'Neue Regel' : 'Regel bearbeiten'}
              </h2>
              {form.id !== null ? (
                <button
                  type="button"
                  onClick={handleDeleteRule}
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1 border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 disabled:opacity-60"
                >
                  <LuTrash2 className="h-4 w-4" />
                  Loeschen
                </button>
              ) : null}
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Name</span>
                <input
                  value={form.name}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, name: event.target.value }))}
                  className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Saisonstart</span>
                <input
                  type="date"
                  value={form.seasonStart}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, seasonStart: event.target.value }))}
                  className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Saisonende</span>
                <input
                  type="date"
                  value={form.seasonEnd}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, seasonEnd: event.target.value }))}
                  className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, enabled: event.target.checked }))}
                  className="h-5 w-5"
                />
                <span className="text-sm font-medium text-slate-700">Aktiv</span>
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Logik</span>
                <select
                  value={form.logic}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, logic: event.target.value as 'any' | 'all' }))}
                  className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="any">Eine Metrik reicht</option>
                  <option value="all">Alle Metriken</option>
                </select>
              </label>
            </div>

            <label className="mt-4 block">
              <span className="text-sm font-medium text-slate-700">Produkte</span>
              <textarea
                value={form.productsText}
                onChange={(event) => setForm((currentForm) => ({ ...currentForm, productsText: event.target.value }))}
                rows={3}
                placeholder={productNames.slice(0, 4).join(', ')}
                className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
              />
            </label>

            <div className="mt-4">
              <div className="text-sm font-medium text-slate-700">Bereiche</div>
              <div className="mt-2 border border-slate-200 bg-slate-50">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Abschnitte waehlen
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleSelectAllSections}
                      className="border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700"
                    >
                      Alle Auswaehlen
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedScopeKeys([])}
                      className="border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-500"
                    >
                      Auswahl leeren
                    </button>
                  </div>
                </div>
                <div className="max-h-72 overflow-y-auto p-2">
                  {sectionScopeOptions.length === 0 ? (
                    <div className="px-3 py-6 text-sm text-slate-500">
                      Keine Abschnitte verfuegbar.
                    </div>
                  ) : (
                    <div className="grid gap-1">
                      {sectionScopeOptions.map((option) => {
                        const alreadyAdded = addedScopeKeySet.has(option.key)
                        return (
                          <label
                            key={option.key}
                            className={`flex items-start gap-3 px-3 py-2 text-sm ${
                              alreadyAdded ? 'text-slate-400' : 'text-slate-700 hover:bg-white'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={selectedScopeSet.has(option.key)}
                              disabled={alreadyAdded}
                              onChange={() => handleToggleScopeSelection(option.key)}
                              className="mt-0.5 h-4 w-4"
                            />
                            <span>{option.label}</span>
                          </label>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
              <div className="mt-2 flex justify-end">
                <button
                  type="button"
                  onClick={handleAddSelectedScopes}
                  className="inline-flex items-center justify-center gap-1 border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold"
                >
                  <LuPlus className="h-4 w-4" />
                  Hinzufuegen
                </button>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {form.scopes.map((scope) => {
                  const key = `${scope.scope_type}-${scope.scope_id}`
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() =>
                        setForm((currentForm) => ({
                          ...currentForm,
                          scopes: currentForm.scopes.filter(
                            (candidate) => !(candidate.scope_type === scope.scope_type && candidate.scope_id === scope.scope_id),
                          ),
                        }))
                      }
                      className="border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700"
                    >
                      {scopeLabelsByKey[key] ?? key} x
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              {metricTypes.map((metricType) => {
                const metric = form.metricInputs[metricType]
                return (
                  <div key={metricType} className="border border-slate-200 bg-slate-50 p-3">
                    <label className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={metric.enabled}
                        onChange={(event) => handleMetricChange(metricType, { enabled: event.target.checked })}
                        className="h-5 w-5"
                      />
                      <span className="font-semibold text-slate-900">{metricLabels[metricType]}</span>
                    </label>
                    <div className="mt-3 grid gap-3 sm:grid-cols-3">
                      <label className="block">
                        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Faellig</span>
                        <input
                          type="number"
                          value={metric.threshold}
                          onChange={(event) => handleMetricChange(metricType, { threshold: event.target.value })}
                          className="mt-1 w-full border border-slate-200 px-3 py-2 text-sm"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Bald</span>
                        <input
                          type="number"
                          value={metric.warningThreshold}
                          onChange={(event) => handleMetricChange(metricType, { warningThreshold: event.target.value })}
                          className="mt-1 w-full border border-slate-200 px-3 py-2 text-sm"
                        />
                      </label>
                      {metricType === 'gdd_since' ? (
                        <label className="block">
                          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Basis C</span>
                          <input
                            type="number"
                            value={metric.baseTemperature}
                            onChange={(event) => handleMetricChange(metricType, { baseTemperature: event.target.value })}
                            className="mt-1 w-full border border-slate-200 px-3 py-2 text-sm"
                          />
                        </label>
                      ) : null}
                    </div>
                  </div>
                )
              })}
            </div>

            <label className="mt-4 block">
              <span className="text-sm font-medium text-slate-700">Notizen</span>
              <textarea
                value={form.notes}
                onChange={(event) => setForm((currentForm) => ({ ...currentForm, notes: event.target.value }))}
                rows={2}
                className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
              />
            </label>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleNewRule}
                className="border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600"
              >
                Zuruecksetzen
              </button>
              <button
                type="button"
                onClick={() => void handleSaveRule()}
                disabled={isSubmitting}
                className="inline-flex items-center gap-2 border border-sky-700 bg-sky-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                <LuPencil className="h-4 w-4" />
                {isSubmitting ? 'Speichern...' : 'Speichern'}
              </button>
            </div>
          </div>
        </section>

        <section className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <LuLink2 className="h-5 w-5 text-slate-500" />
            <h2 className="text-xl font-semibold text-slate-900">Smartfarmer - FarmAtlas Zuordnungen</h2>
          </div>
          {isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
              Lade Pflanzenschutzstatus...
            </div>
          ) : (
            aliasManagementPanel
          )}
        </section>

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
