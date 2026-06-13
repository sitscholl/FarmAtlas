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
  stageTooltipContent?: ReactNode
  metrics?: FieldBoxMetric[]
  to?: string
  actions?: ReactNode
  footerActions?: ReactNode
  detailContent?: ReactNode
  borderClassName?: string
  titleAdornment?: ReactNode
}

function FieldBoxContent({
  title,
  subtitle,
  stageLabel,
  stageIcon: StageIcon,
  stageTooltipContent,
  metrics,
  to,
  actions,
  footerActions,
  detailContent,
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
    <div className="app-card group relative z-0 overflow-visible border p-5 shadow-md backdrop-blur transition duration-300 hover:z-50 focus-within:z-50 sm:p-6">
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
          <h3 className="app-heading flex items-center gap-2">
            {titleAdornment}
            <span>{title}</span>
          </h3>
        </div>
      </div>

      {subtitle ? (
        <p className={`${contentClasses} app-muted whitespace-pre-line`}>{subtitle}</p>
      ) : null}

      {stageLabel ? (
        <div className={`${contentClasses} app-meta group/stage pointer-events-auto mt-2 inline-flex items-center gap-1.5`}>
          {StageIcon ? <StageIcon className="h-4 w-4 text-emerald-600" aria-hidden="true" /> : null}
          <span>{stageLabel}</span>
          {stageTooltipContent ? (
            <>
              <div className="absolute left-0 top-full z-40 hidden h-2 w-80 max-w-[calc(100vw-3rem)] group-hover/stage:block" />
              <div className="app-card app-muted pointer-events-auto absolute left-0 top-full z-50 mt-2 hidden w-80 max-w-[calc(100vw-3rem)] border p-3 text-left font-normal opacity-0 shadow-xl transition duration-150 group-hover/stage:block group-hover/stage:opacity-100">
                {stageTooltipContent}
              </div>
            </>
          ) : null}
        </div>
      ) : null}

      {metrics && metrics.length > 0 ? (
        <div className={`${contentClasses} app-divider mt-1 flex flex-wrap items-center gap-x-5 gap-y-2 border-t pt-1`}>
          {metrics.map((metric) => {
            const MetricIcon = metric.icon
            const critical = isMetricCritical(metric)

            return (
              <div
                key={metric.label}
                className="group/metric relative flex min-w-0 items-center gap-1.5 pointer-events-auto"
              >
                {MetricIcon ? (
                  <span className="app-icon-muted inline-flex shrink-0 items-center justify-center">
                    <MetricIcon className="h-4 w-4" aria-hidden="true" />
                  </span>
                ) : null}
                <p className={`app-metric whitespace-nowrap ${critical ? 'text-rose-600' : ''}`}>
                  {formatMetricValue(metric)}
                  {metric.unit ? <span className="app-muted ml-0.5 font-medium">{metric.unit}</span> : null}
                </p>
                <div className="app-tooltip pointer-events-none absolute bottom-full left-0 z-30 mb-2 hidden whitespace-nowrap rounded-lg px-2.5 py-1.5 opacity-0 shadow-lg transition duration-150 group-hover/metric:flex group-hover/metric:opacity-100">
                  {metric.tooltip ?? metric.label}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}

      {detailContent ? (
        <div className={`${contentClasses} app-divider pointer-events-auto mt-1 border-t py-3 border-b`}>
          {detailContent}
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
