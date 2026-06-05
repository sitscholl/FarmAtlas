import { LuShieldCheck, LuShieldAlert, LuShieldX, LuCircleHelp } from 'react-icons/lu'

import type { CropProtectionRuleEvaluationRead } from '../types/generated/api'

type CropProtectionStatus = 'due' | 'soon' | 'ok' | 'missing'

const statusRank: Record<CropProtectionStatus, number> = {
  due: 4,
  soon: 3,
  missing: 2,
  ok: 1,
}

const statusLabels: Record<CropProtectionStatus, string> = {
  due: 'Faellig',
  soon: 'Bald',
  ok: 'OK',
  missing: 'Offen',
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

function normalizeStatus(value: string): CropProtectionStatus {
  if (value === 'due' || value === 'soon' || value === 'ok' || value === 'missing') {
    return value
  }
  return 'missing'
}

function getWorstCropProtectionStatus(
  evaluations: CropProtectionRuleEvaluationRead[],
): CropProtectionStatus | null {
  if (evaluations.length === 0) {
    return null
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

function buildTooltip(evaluation: CropProtectionRuleEvaluationRead) {
  const metrics = evaluation.metrics
    .map((metric) => `${metric.metric_type}: ${metric.value ?? '-'} / ${metric.threshold}`)
    .join('\n')

  return [
    `${evaluation.rule_name} | ${evaluation.section_name}`,
    `${formatDate(evaluation.last_treatment_date)}${evaluation.last_treatment_product ? ` | ${evaluation.last_treatment_product}` : ''}`,
    metrics,
  ]
    .filter((line) => line.trim() !== '')
    .join('\n')
}

export default function CropProtectionStatusLayer({
  evaluations,
  maxItems = 3,
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

  const sortedEvaluations = evaluations
    .slice()
    .sort((left, right) => statusRank[normalizeStatus(right.status)] - statusRank[normalizeStatus(left.status)])
  const visibleEvaluations = sortedEvaluations.slice(0, maxItems)
  const hiddenCount = sortedEvaluations.length - visibleEvaluations.length
  const worstStatus = getWorstCropProtectionStatus(evaluations) ?? 'missing'
  const WorstIcon = statusIcons[worstStatus]

  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
        <WorstIcon className="h-4 w-4" aria-hidden="true" />
        <span>Pflanzenschutz</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {visibleEvaluations.map((evaluation) => {
          const status = normalizeStatus(evaluation.status)
          const StatusIcon = statusIcons[status]

          return (
            <div
              key={`${evaluation.rule_id}-${evaluation.section_id}`}
              className={`group/protection relative inline-flex max-w-full items-center gap-1.5 border px-2.5 py-1.5 text-xs font-semibold ${statusClasses[status]}`}
            >
              <StatusIcon className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="truncate">{evaluation.rule_name}</span>
              <span className="shrink-0">{statusLabels[status]}</span>
              <div className="pointer-events-none absolute bottom-full left-0 z-40 mb-2 hidden w-72 max-w-[calc(100vw-3rem)] whitespace-pre-line border border-slate-200 bg-white px-3 py-2 text-left text-xs font-medium text-slate-700 opacity-0 shadow-xl transition group-hover/protection:block group-hover/protection:opacity-100">
                {buildTooltip(evaluation)}
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
