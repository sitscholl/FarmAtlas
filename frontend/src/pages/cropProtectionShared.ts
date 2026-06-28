import { createElement } from 'react'

import api from '../api'
import {
  type CropProtectionRuleCreate,
  type CropProtectionRuleMetricBase,
  type CropProtectionRuleRead,
  type CropProtectionRuleScopeBase,
  type FieldDetailRead,
  type FieldRead,
} from '../types/generated/api'

export type ScopeType = CropProtectionRuleScopeBase['scope_type']
export type MetricType = CropProtectionRuleMetricBase['metric_type']

export type ScopeOption = {
  key: string
  type: ScopeType
  id: number
  label: string
}

export type RuleFormMetricState = {
  enabled: boolean
  threshold: string
  warningThreshold: string
  baseTemperature: string
}

export type RuleFormState = {
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

export const metricTypes: MetricType[] = ['days_since', 'rain_since', 'gdd_since']
export const SMARTFARMER_SOURCE = 'smartfarmer'
export const CURRENT_SEASON_YEAR = new Date().getFullYear()
export const TREATMENT_TABLE_LIMIT = 300

export const emptyMetricInputs: Record<MetricType, RuleFormMetricState> = {
  days_since: { enabled: true, threshold: '7', warningThreshold: '5', baseTemperature: '10' },
  rain_since: { enabled: false, threshold: '25', warningThreshold: '20', baseTemperature: '10' },
  gdd_since: { enabled: false, threshold: '100', warningThreshold: '80', baseTemperature: '10' },
}

export const emptyRuleForm: RuleFormState = {
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

export const metricLabels: Record<MetricType, string> = {
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

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return '-'
  }
  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

export function formatMetricValue(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '-'
  }
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 }).format(value)
}

export function cloneMetricInputs(inputs: Record<MetricType, RuleFormMetricState>) {
  return Object.fromEntries(
    metricTypes.map((metricType) => [metricType, { ...inputs[metricType] }]),
  ) as Record<MetricType, RuleFormMetricState>
}

export async function fetchFieldDetails() {
  const fieldsResponse = await api.get<FieldRead[]>('/fields')
  const detailResponses = await Promise.all(
    fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
  )
  return detailResponses.map((response) => response.data)
}

export function buildScopeOptions(fieldDetails: FieldDetailRead[]): ScopeOption[] {
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

export function buildRuleForm(rule: CropProtectionRuleRead): RuleFormState {
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

export function buildRulePayload(form: RuleFormState): CropProtectionRuleCreate {
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

export function treatmentResolutionBadge(status: string) {
  return createElement(
    'span',
    {
      className: `inline-flex border px-2 py-1 text-xs font-semibold ${treatmentResolutionClasses[status] ?? treatmentResolutionClasses.unresolved}`,
    },
    treatmentResolutionLabels[status] ?? status,
  )
}
