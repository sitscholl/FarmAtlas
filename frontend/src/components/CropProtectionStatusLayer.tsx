import { LuCircleHelp, LuShieldAlert, LuShieldCheck, LuShieldX } from 'react-icons/lu'

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
    <div className="mt-1 flex flex-wrap gap-1">
      {metrics.map((metric) => (
        <span key={metric.metric_type} className="border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[11px] text-slate-600">
          {metricLabels[metric.metric_type] ?? metric.metric_type}: {formatMetricValue(metric.value)}
        </span>
      ))}
    </div>
  )
}

function RuleTooltip({ ruleGroup }: { ruleGroup: RuleGroup }) {
  const treatmentGroups = groupEvaluationsByTreatment(ruleGroup.evaluations)

  return (
    <div>
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
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
                        <span className={`shrink-0 border px-1.5 py-0.5 text-[10px] font-semibold ${statusClasses[normalizeStatus(evaluation.status)]}`}>
                          {normalizeStatus(evaluation.status)}
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
  maxItems = 4,
}: {
  evaluations: CropProtectionRuleEvaluationRead[]
  maxItems?: number
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
  const visibleRuleGroups = ruleGroups.slice(0, maxItems)
  const hiddenCount = ruleGroups.length - visibleRuleGroups.length

  return (
    <div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
        Pflanzenschutz
      </div>
      <div className="flex flex-wrap gap-2">
        {visibleRuleGroups.map((ruleGroup) => {
          const StatusIcon = statusIcons[ruleGroup.status]

          return (
            <div
              key={ruleGroup.ruleId}
              className={`group/protection relative inline-flex max-w-full items-center gap-1.5 border px-2.5 py-1.5 text-xs font-semibold ${statusClasses[ruleGroup.status]}`}
            >
              <StatusIcon className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="truncate">{ruleGroup.ruleName}</span>
              <div className="absolute left-0 top-full z-40 hidden h-2 w-96 max-w-[calc(100vw-3rem)] group-hover/protection:block" />
              <div className="pointer-events-auto absolute left-0 top-full z-50 mt-2 hidden w-96 max-w-[calc(100vw-3rem)] border border-slate-200 bg-white p-3 text-left text-xs font-normal text-slate-700 opacity-0 shadow-xl transition duration-150 group-hover/protection:block group-hover/protection:opacity-100">
                <RuleTooltip ruleGroup={ruleGroup} />
              </div>
            </div>
          )
        })}
        {hiddenCount > 0 ? (
          <div className="inline-flex items-center border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-500">
            +{hiddenCount}
          </div>
        ) : null}
      </div>
    </div>
  )
}
