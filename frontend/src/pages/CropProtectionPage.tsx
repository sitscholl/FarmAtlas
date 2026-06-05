import { useEffect, useMemo, useState } from 'react'
import { LuPencil, LuPlus, LuRefreshCw, LuShieldAlert, LuTrash2 } from 'react-icons/lu'

import api from '../api'
import DataTable, { type DataTableColumn } from '../components/DataTable'
import { notifyDataChanged } from '../lib/dataEvents'
import {
  type CropProtectionRuleCreate,
  type CropProtectionRuleEvaluationRead,
  type CropProtectionRuleMetricBase,
  type CropProtectionRuleRead,
  type CropProtectionRuleScopeBase,
  type FieldDetailRead,
  type FieldRead,
} from '../types/generated/api'

type StatusFilter = 'all' | 'due' | 'soon' | 'missing' | 'ok'
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
  target: string
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

const emptyMetricInputs: Record<MetricType, RuleFormMetricState> = {
  days_since: { enabled: true, threshold: '7', warningThreshold: '5', baseTemperature: '10' },
  rain_since: { enabled: false, threshold: '25', warningThreshold: '20', baseTemperature: '10' },
  gdd_since: { enabled: false, threshold: '100', warningThreshold: '80', baseTemperature: '10' },
}

const emptyRuleForm: RuleFormState = {
  id: null,
  name: '',
  target: '',
  enabled: true,
  logic: 'any',
  seasonStart: '',
  seasonEnd: '',
  notes: '',
  productsText: '',
  scopes: [],
  metricInputs: emptyMetricInputs,
}

const statusLabels: Record<string, string> = {
  due: 'Faellig',
  soon: 'Bald',
  ok: 'OK',
  missing: 'Offen',
}

const statusClasses: Record<string, string> = {
  due: 'border-rose-200 bg-rose-50 text-rose-800',
  soon: 'border-amber-200 bg-amber-50 text-amber-900',
  ok: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  missing: 'border-slate-200 bg-slate-50 text-slate-600',
}

const metricLabels: Record<MetricType, string> = {
  days_since: 'Tage',
  rain_since: 'Regen',
  gdd_since: 'GDD',
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
      label: `${fieldDetail.field.group} | ${fieldDetail.field.name}`,
    }

    const plantingOptions = fieldDetail.plantings.map((planting) => ({
      key: `planting-${planting.id}`,
      type: 'planting' as const,
      id: planting.id,
      label: `${fieldDetail.field.group} | ${fieldDetail.field.name} | ${planting.variety}`,
    }))

    const sectionOptions = fieldDetail.plantings.flatMap((planting) =>
      planting.sections.map((section) => ({
        key: `section-${section.id}`,
        type: 'section' as const,
        id: section.id,
        label: `${fieldDetail.field.group} | ${fieldDetail.field.name} | ${planting.variety} | ${section.name}`,
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
    target: rule.target,
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
    target: form.target.trim(),
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

function statusBadge(status: string) {
  return (
    <span className={`inline-flex border px-2 py-1 text-xs font-semibold ${statusClasses[status] ?? statusClasses.missing}`}>
      {statusLabels[status] ?? status}
    </span>
  )
}

export default function CropProtectionPage() {
  const [rules, setRules] = useState<CropProtectionRuleRead[]>([])
  const [evaluations, setEvaluations] = useState<CropProtectionRuleEvaluationRead[]>([])
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [productNames, setProductNames] = useState<string[]>([])
  const [form, setForm] = useState<RuleFormState>(emptyRuleForm)
  const [selectedScopeKey, setSelectedScopeKey] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setIsLoading(true)
      const [rulesResponse, evaluationsResponse, fieldsResponse, productsResponse] = await Promise.all([
        api.get<CropProtectionRuleRead[]>('/crop-protection/rules'),
        api.get<CropProtectionRuleEvaluationRead[]>('/crop-protection/evaluations'),
        api.get<FieldRead[]>('/fields'),
        api.get<string[]>('/treatments/products'),
      ])
      const detailResponses = await Promise.all(
        fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
      )

      setRules(rulesResponse.data)
      setEvaluations(evaluationsResponse.data)
      setFieldDetails(detailResponses.map((response) => response.data))
      setProductNames(productsResponse.data)
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
  }, [])

  const scopeOptions = useMemo(() => buildScopeOptions(fieldDetails), [fieldDetails])
  const scopeLabelsByKey = useMemo(
    () => Object.fromEntries(scopeOptions.map((option) => [option.key, option.label])),
    [scopeOptions],
  )

  const visibleEvaluations = useMemo(
    () =>
      evaluations.filter((evaluation) => statusFilter === 'all' || evaluation.status === statusFilter),
    [evaluations, statusFilter],
  )

  const countsByStatus = useMemo(
    () =>
      evaluations.reduce<Record<string, number>>((counts, evaluation) => {
        counts[evaluation.status] = (counts[evaluation.status] ?? 0) + 1
        return counts
      }, {}),
    [evaluations],
  )

  const evaluationColumns: DataTableColumn<CropProtectionRuleEvaluationRead>[] = [
    { id: 'status', header: 'Status', cell: (row) => statusBadge(row.status) },
    { id: 'field', header: 'Anlage', cell: (row) => row.field_name },
    { id: 'section', header: 'Abschnitt', cell: (row) => row.section_name },
    { id: 'target', header: 'Ziel', cell: (row) => row.target },
    { id: 'rule', header: 'Regel', cell: (row) => row.rule_name },
    {
      id: 'last',
      header: 'Letzte Behandlung',
      cell: (row) => `${formatDate(row.last_treatment_date)}${row.last_treatment_product ? ` | ${row.last_treatment_product}` : ''}`,
    },
    {
      id: 'metrics',
      header: 'Metriken',
      cell: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.metrics.map((metric) => (
            <span key={metric.metric_type} className="border border-slate-200 bg-slate-50 px-2 py-1 text-xs">
              {metricLabels[metric.metric_type as MetricType] ?? metric.metric_type}: {formatMetricValue(metric.value)}
            </span>
          ))}
        </div>
      ),
    },
  ]

  const handleSelectRule = (rule: CropProtectionRuleRead) => {
    setForm(buildRuleForm(rule))
    setSelectedScopeKey('')
  }

  const handleNewRule = () => {
    setForm({
      ...emptyRuleForm,
      metricInputs: cloneMetricInputs(emptyMetricInputs),
    })
    setSelectedScopeKey('')
  }

  const handleAddScope = () => {
    const option = scopeOptions.find((candidate) => candidate.key === selectedScopeKey)
    if (!option) {
      return
    }
    const nextScope = { scope_type: option.type, scope_id: option.id }
    const exists = form.scopes.some(
      (scope) => scope.scope_type === nextScope.scope_type && scope.scope_id === nextScope.scope_id,
    )
    if (exists) {
      return
    }
    setForm((currentForm) => ({ ...currentForm, scopes: [...currentForm.scopes, nextScope] }))
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

        <div className="mt-6 grid gap-3 sm:grid-cols-4">
          {(['due', 'soon', 'missing', 'ok'] as StatusFilter[]).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(statusFilter === status ? 'all' : status)}
              className={`border px-4 py-3 text-left transition ${
                statusFilter === status ? 'border-slate-900 bg-white shadow-sm' : 'border-slate-200 bg-slate-50 hover:bg-white'
              }`}
            >
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                {statusLabels[status]}
              </div>
              <div className="mt-1 text-3xl font-semibold text-slate-900">
                {countsByStatus[status] ?? 0}
              </div>
            </button>
          ))}
        </div>

        <section className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <LuShieldAlert className="h-5 w-5 text-slate-500" />
            <h2 className="text-xl font-semibold text-slate-900">Aktueller Status</h2>
          </div>
          {isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
              Lade Pflanzenschutzstatus...
            </div>
          ) : (
            <DataTable
              columns={evaluationColumns}
              rows={visibleEvaluations}
              getRowKey={(row) => `${row.rule_id}-${row.section_id}`}
              emptyMessage="Keine Pflanzenschutzbewertungen vorhanden."
              filters={[
                {
                  id: 'status',
                  label: 'Status',
                  type: 'select',
                  value: statusFilter,
                  options: [
                    { label: 'Alle', value: 'all' },
                    { label: 'Faellig', value: 'due' },
                    { label: 'Bald', value: 'soon' },
                    { label: 'Offen', value: 'missing' },
                    { label: 'OK', value: 'ok' },
                  ],
                },
              ]}
              onFilterChange={(_, value) => setStatusFilter(value as StatusFilter)}
              onResetFilters={() => setStatusFilter('all')}
            />
          )}
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <h2 className="text-xl font-semibold text-slate-900">Regeln</h2>
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
                          {rule.target} | {rule.products.length} Produkte | {rule.scopes.length} Bereiche
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

          <div className="border border-slate-200 bg-white p-4">
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
                <span className="text-sm font-medium text-slate-700">Ziel</span>
                <input
                  value={form.target}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, target: event.target.value }))}
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
              <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                <select
                  value={selectedScopeKey}
                  onChange={(event) => setSelectedScopeKey(event.target.value)}
                  className="min-w-0 flex-1 border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="">Bereich waehlen</option>
                  {scopeOptions.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleAddScope}
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
      </div>
    </section>
  )
}
