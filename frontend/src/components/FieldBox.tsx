import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { IconType } from 'react-icons'

import { MdWaterDrop } from 'react-icons/md'

export type FieldBoxMetric = {
  label: string
  value: string
}

export type FieldBoxStatusBar = {
  label: string
  value: string
  percentage: number
  isCritical: boolean
  icon?: IconType
}

type FieldBoxProps = {
  title: string
  badge: string
  subtitle?: string
  metrics?: FieldBoxMetric[]
  statusBars?: FieldBoxStatusBar[]
  to?: string
  actions?: ReactNode
  borderClassName?: string
  titleAdornment?: ReactNode
}

function FieldBoxContent({
  title,
  badge,
  subtitle,
  metrics,
  statusBars,
  to,
  actions,
  titleAdornment,
}: FieldBoxProps) {
  const contentClasses = to ? 'relative z-10 pointer-events-none' : 'relative'

  return (
    <div className="group relative overflow-hidden rounded-[1.75rem] border p-6 shadow-sm backdrop-blur transition duration-300 hover:-translate-y-0.5 hover:shadow-lg border-slate-200/80 hover:border-sky-500">
      {to ? (
        <Link
          to={to}
          aria-label={`${title} oeffnen`}
          className="absolute inset-0 rounded-[1.75rem] focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-4"
        />
      ) : null}

      <div className={`${contentClasses} flex items-start justify-between gap-4`}>
        <div className="min-w-0 flex-1">
          {actions ? (
            <div className="z-20 flex justify-left gap-2 pointer-events-auto">
              {actions}
            </div>
          ) : null}
          <h3 className="mt-2 flex items-center gap-2 text-lg font-semibold text-slate-900">
            {titleAdornment}
            <span>{title}</span>
          </h3>
        </div>
        <span className="shrink-0 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
          {badge}
        </span>
      </div>

      {subtitle ? (
        <p className={`${contentClasses} text-sm text-slate-500 whitespace-pre-line`}>{subtitle}</p>
      ) : null}

      {statusBars && statusBars.length > 0 ? (
        <div className={`${contentClasses} mt-4 space-y-2`}>
          {statusBars.map((statusBar) => {
            const StatusIcon = statusBar.icon ?? MdWaterDrop
            const statusBarClasses = statusBar.isCritical
              ? 'bg-rose-500'
              : 'bg-gradient-to-r from-sky-500 via-cyan-400 to-blue-400'
            const statusCardClasses = statusBar.isCritical
              ? 'border-rose-200/80 bg-rose-50/80 text-rose-600'
              : 'border-slate-200/80 bg-slate-50/80 text-sky-700'
            const statusBarWidth = statusBar.isCritical ? 100 : statusBar.percentage

            return (
              <div
                key={`${statusBar.label}-${statusBar.value}`}
                className={`group/status relative flex items-center gap-3 rounded-2xl border px-3 py-2 ${statusCardClasses}`}
                title={`${statusBar.label}: ${statusBar.value}`}
              >
                <StatusIcon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <div className="flex-1">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className={`h-full rounded-full ${statusBarClasses} transition-[width] duration-500`}
                      style={{ width: `${statusBarWidth}%` }}
                    />
                  </div>
                </div>
                <div className="pointer-events-none absolute inset-y-1 right-2 z-20 hidden items-center rounded-lg bg-slate-900 px-2.5 text-xs font-medium text-white opacity-0 shadow-lg transition duration-150 group-hover/status:flex group-hover/status:opacity-100">
                  {statusBar.label}: {statusBar.value}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}

      {metrics ? (
        <div className={`${contentClasses} mt-2 space-y-1 border-t border-black/30 border-slate-100 pt-1`}>
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="flex items-baseline justify-between gap-1"
            >
              <p className="text-sm text-slate-500">{metric.label}</p>
              <p className="text-base font-semibold text-slate-900">
                {metric.value}
              </p>
            </div>
          ))}
        </div>
      ): null }
    </div>
  )
}

export default function FieldBox(props: FieldBoxProps) {
  return <FieldBoxContent {...props} />
}
