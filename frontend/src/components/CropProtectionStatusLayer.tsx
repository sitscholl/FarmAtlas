import { LuCalendarDays, LuCircleHelp, LuCloudRain, LuShieldAlert, LuShieldCheck, LuShieldX, LuThermometerSun } from 'react-icons/lu'

import type { CropProtectionMetricEvaluationRead, CropProtectionRuleEvaluationRead } from '../types/generated/api'

type CropProtectionStatus = 'due' | 'soon' | 'ok' | 'missing'

type RuleGroup = {
  ruleId: number
  ruleName: string
  status: CropProtectionStatus
  evaluations: CropProtectionRuleEvaluationRead[]
}

type TreatmentGroup = {
  key: string
  dateLabel: string
  productLabel: string
  evaluations: CropProtectionRuleEvaluationRead[]
}

const statusRank: Record<CropProtectionStatus, number> = {
  due: 4,
  soon: 3,
  missing: 2,
  ok: 1,
}

const statusClasses: Record<CropProtectionStatus, string> = {
  due: 'border-rose-200 bg-rose-50 text-rose-800',
  soon: 'border-amber-200 bg-amber-50 text-amber-900',
  ok: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  missing: 'border-slate-200 bg-slate-50 text-slate-600',
}

const statusIcons = {
  due: LuShieldX,
  soon: LuShieldAlert,
  ok: LuShieldCheck,
  missing: LuCircleHelp,
}

const metricLabels: Record<string, string> = {
  days_since: 'Tage',
  rain_since: 'Regen',
  gdd_since: 'GDD',
}

const metricUnits: Record<string, string> = {
  days_since: 'd',
  rain_since: 'mm',
  gdd_since: 'GDD',
}

const metricIcons = {
  days_since: LuCalendarDays,
  rain_since: LuCloudRain,
  gdd_since: LuThermometerSun,
}

const metricStatusClasses: Record<CropProtectionStatus, string> = {
  due: 'border-rose-200 bg-rose-50 text-rose-900',
  soon: 'border-amber-200 bg-amber-50 text-amber-950',
  ok: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  missing: 'border-slate-200 bg-slate-50 text-slate-600',
}

const statusLabels: Record<string, string> = {
  due: 'Fällig',
  soon: 'Bald',
  ok: 'OK',
  missing: 'Offen',
}

function normalizeStatus(value: string): CropProtectionStatus {
  if (value === 'due' || value === 'soon' || value === 'ok' || value === 'missing') {
    return value
  }
  return 'missing'
}

function getWorstCropProtectionStatus(
  evaluations: CropProtectionRuleEvaluationRead[],
): CropProtectionStatus {
  if (evaluations.length === 0) {
    return 'missing'
  }

  return evaluations
    .map((evaluation) => normalizeStatus(evaluation.status))
    .sort((left, right) => statusRank[right] - statusRank[left])[0]
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return 'Keine Behandlung'
  }
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: 'short',
  }).format(new Date(value))
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return 'unbekannt'
  }
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatMetricValue(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '-'
  }
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 }).format(value)
}

function groupEvaluationsByRule(evaluations: CropProtectionRuleEvaluationRead[]): RuleGroup[] {
  const groupsByRuleId = evaluations.reduce<Record<number, CropProtectionRuleEvaluationRead[]>>(
    (groups, evaluation) => {
      groups[evaluation.rule_id] = [...(groups[evaluation.rule_id] ?? []), evaluation]
      return groups
    },
    {},
  )

  return Object.entries(groupsByRuleId)
    .map(([ruleId, ruleEvaluations]) => ({
      ruleId: Number(ruleId),
      ruleName: ruleEvaluations[0]?.rule_name ?? `Regel ${ruleId}`,
      status: getWorstCropProtectionStatus(ruleEvaluations),
      evaluations: ruleEvaluations.slice().sort((left, right) => left.section_name.localeCompare(right.section_name)),
    }))
    .sort((left, right) => statusRank[right.status] - statusRank[left.status] || left.ruleName.localeCompare(right.ruleName))
}

function groupEvaluationsByTreatment(evaluations: CropProtectionRuleEvaluationRead[]): TreatmentGroup[] {
  const groups = evaluations.reduce<Record<string, TreatmentGroup>>((accumulator, evaluation) => {
    const dateLabel = formatDate(evaluation.last_treatment_date)
    const productLabel = evaluation.last_treatment_product ?? '-'
    const key = `${dateLabel}|${productLabel}`
    accumulator[key] = accumulator[key] ?? {
      key,
      dateLabel,
      productLabel,
      evaluations: [],
    }
    accumulator[key].evaluations.push(evaluation)
    return accumulator
  }, {})

  return Object.values(groups).sort((left, right) => right.dateLabel.localeCompare(left.dateLabel))
}

function MetricSummary({ metrics }: { metrics: CropProtectionMetricEvaluationRead[] }) {
  if (metrics.length === 0) {
    return null
  }

  return (
    <div className="mt-2 grid grid-cols-3 gap-1.5">
      {metrics.map((metric) => {
        const status = normalizeStatus(metric.status)
        const MetricIcon = metricIcons[metric.metric_type as keyof typeof metricIcons] ?? LuCircleHelp
        const unit = metricUnits[metric.metric_type] ?? ''
        const valueLabel = formatMetricValue(metric.value)

        return (
          <div
            key={metric.metric_type}
            className={`min-w-0 border px-2 py-1.5 ${metricStatusClasses[status]}`}
          >
            <div className="flex items-center gap-1.5">
              <MetricIcon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate text-tiny font-semibold uppercase tracking-[0.12em]">
                {metricLabels[metric.metric_type] ?? metric.metric_type}
              </span>
            </div>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-base font-semibold leading-none">{valueLabel}</span>
              {unit ? <span className="text-tiny font-semibold opacity-70">{unit}</span> : null}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function RuleTooltip({ ruleGroup }: { ruleGroup: RuleGroup }) {
  const treatmentGroups = groupEvaluationsByTreatment(ruleGroup.evaluations)

  return (
    <div>
      <div className="mb-2 text-caption font-semibold uppercase tracking-[0.18em] text-slate-500">
        {ruleGroup.ruleName}
      </div>
      <div className="max-h-72 overflow-y-auto pr-1">
        {treatmentGroups.map((group) => (
          <div key={group.key} className="border-t border-slate-100 py-2 first:border-t-0 first:pt-0">
            <div className="grid grid-cols-[5.5rem_1fr] gap-1">
              <div className="font-semibold text-slate-900">{group.dateLabel}</div>
              <div className="min-w-0">
                <div className="font-medium text-slate-800">{group.productLabel}</div>
                <div className="mt-1 grid gap-1">
                  {group.evaluations.map((evaluation) => (
                    <div key={`${evaluation.rule_id}-${evaluation.section_id}`} className="min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-slate-600">{evaluation.section_name}</span>
                        <span className={`shrink-0 border px-1.5 py-0.5 text-tiny font-semibold ${statusClasses[normalizeStatus(evaluation.status)]}`}>
                          {statusLabels[normalizeStatus(evaluation.status)]}
                        </span>
                      </div>
                      <MetricSummary metrics={evaluation.metrics} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function CropProtectionStatusLayer({
  evaluations,
  weatherUpdatedAt,
}: {
  evaluations: CropProtectionRuleEvaluationRead[]
  weatherUpdatedAt?: string | null
}) {
  if (evaluations.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <LuCircleHelp className="h-4 w-4" aria-hidden="true" />
        <span>Kein Pflanzenschutzstatus</span>
      </div>
    )
  }

  const ruleGroups = groupEvaluationsByRule(evaluations)

  return (
    <div>
      <div className="mb-2 text-xs text-caption font-medium uppercase tracking-[0.18em] text-slate-500">
        Pflanzenschutz
      </div>
      <div className="mb-2 text-xs text-caption font-medium text-slate-500">
        Wetterdaten: {formatDateTime(weatherUpdatedAt)}
      </div>
      <div className="flex flex-wrap gap-2">
        {ruleGroups.map((ruleGroup) => {
          const StatusIcon = statusIcons[ruleGroup.status]

          return (
            <div
              key={ruleGroup.ruleId}
              className={`group/protection relative inline-flex max-w-full items-center gap-1.5 border px-2.5 py-1.5 text-xs font-semibold ${statusClasses[ruleGroup.status]}`}
            >
              <StatusIcon className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="truncate">{ruleGroup.ruleName}</span>
              <div className="absolute left-0 top-full z-40 hidden h-2 w-96 max-w-[calc(100vw-3rem)] group-hover/protection:sm:block" />
              <div className="pointer-events-auto fixed inset-x-4 bottom-4 z-50 hidden max-h-[70vh] overflow-y-auto border border-slate-200 bg-white p-3 text-left text-xs font-normal text-slate-700 opacity-0 shadow-xl transition duration-150 group-hover/protection:block group-hover/protection:opacity-100 sm:absolute sm:inset-x-auto sm:bottom-auto sm:left-0 sm:top-full sm:mt-2 sm:w-96 sm:max-w-[calc(100vw-3rem)] sm:overflow-visible">
                <RuleTooltip ruleGroup={ruleGroup} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
