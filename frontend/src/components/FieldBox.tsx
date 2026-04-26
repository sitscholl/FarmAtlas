import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { IconType } from 'react-icons'

export type FieldBoxMetric = {
  label: string
  icon?: IconType
  value: string | number
  unit?: string
  kind?: 'text' | 'number' | 'date' | 'time' | 'datetime'
  criticalBelow?: number
  tooltip?: string
}

type FieldBoxProps = {
  title: string
  subtitle?: string
  stageLabel?: string
  stageIcon?: IconType
  metrics?: FieldBoxMetric[]
  to?: string
  actions?: ReactNode
  footerActions?: ReactNode
  borderClassName?: string
  titleAdornment?: ReactNode
}

function FieldBoxContent({
  title,
  subtitle,
  stageLabel,
  stageIcon: StageIcon,
  metrics,
  to,
  actions,
  footerActions,
  titleAdornment,
}: FieldBoxProps) {
  const contentClasses = to ? 'relative z-10 pointer-events-none' : 'relative'
  const dateFormatter = new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: 'short',
    // year: 'numeric',
  })
  const timeFormatter = new Intl.DateTimeFormat('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
  })
  const dateTimeFormatter = new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: '2-digit',
    // year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  const formatMetricValue = (metric: FieldBoxMetric) => {
    if (metric.kind === 'date' || metric.kind === 'time' || metric.kind === 'datetime') {
      const parsedDate = typeof metric.value === 'string'
        ? new Date(metric.value)
        : new Date(String(metric.value))
      if (Number.isNaN(parsedDate.getTime())) {
        return String(metric.value)
      }

      if (metric.kind === 'date') {
        return dateFormatter.format(parsedDate)
      }
      if (metric.kind === 'time') {
        return timeFormatter.format(parsedDate)
      }

      return dateTimeFormatter.format(parsedDate)
    }

    return String(metric.value)
  }

  const isMetricCritical = (metric: FieldBoxMetric) =>
    typeof metric.criticalBelow === 'number' &&
    typeof metric.value === 'number' &&
    metric.value < metric.criticalBelow

  return (
    <div className="group relative overflow-visible border border-slate-200/80 p-5 shadow-md backdrop-blur transition duration-300 sm:p-6">
      {to ? (
        <Link
          to={to}
          aria-label={`${title} oeffnen`}
          className="absolute inset-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-4"
        />
      ) : null}

      {actions ? (
        <div className="pointer-events-auto absolute right-4 top-4 z-20">
          {actions}
        </div>
      ) : null}

      <div className={`${contentClasses} flex items-start gap-4 pr-12`}>
        <div className="min-w-0 flex-1">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            {titleAdornment}
            <span>{title}</span>
          </h3>
        </div>
      </div>

      {subtitle ? (
        <p className={`${contentClasses} whitespace-pre-line text-sm text-slate-500`}>{subtitle}</p>
      ) : null}

      {stageLabel ? (
        <div className={`${contentClasses} mt-2 flex items-center gap-1.5 text-sm font-medium text-slate-700`}>
          {StageIcon ? <StageIcon className="h-4 w-4 text-emerald-600" aria-hidden="true" /> : null}
          <span>{stageLabel}</span>
        </div>
      ) : null}

      {metrics && metrics.length > 0 ? (
        <div className={`${contentClasses} mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-slate-100 pt-1`}>
          {metrics.map((metric) => {
            const MetricIcon = metric.icon
            const critical = isMetricCritical(metric)

            return (
              <div
                key={metric.label}
                className="group/metric relative flex min-w-0 items-center gap-1.5 pointer-events-auto"
              >
                {MetricIcon ? (
                  <span className="inline-flex shrink-0 items-center justify-center text-slate-400">
                    <MetricIcon className="h-4 w-4" aria-hidden="true" />
                  </span>
                ) : null}
                <p className={`whitespace-nowrap text-[15px] font-semibold ${critical ? 'text-rose-600' : 'text-slate-700'}`}>
                  {formatMetricValue(metric)}
                  {metric.unit ? <span className="ml-0.5 font-medium text-slate-500">{metric.unit}</span> : null}
                </p>
                <div className="pointer-events-none absolute bottom-full left-0 z-30 mb-2 hidden whitespace-nowrap rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white opacity-0 shadow-lg transition duration-150 group-hover/metric:flex group-hover/metric:opacity-100">
                  {metric.tooltip ?? metric.label}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}

      {footerActions ? (
        <div className="relative z-10 flex flex-wrap gap-2 pt-2 pointer-events-auto">
          {footerActions}
        </div>
      ) : null}
    </div>
  )
}

export default function FieldBox(props: FieldBoxProps) {
  return <FieldBoxContent {...props} />
}
