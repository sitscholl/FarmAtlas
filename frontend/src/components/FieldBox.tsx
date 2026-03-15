export type FieldBoxMetric = {
  label: string
  value: string
}

export type FieldBoxStatusBar = {
  label: string
  value: string
  percentage: number
  isCritical: boolean
}

type FieldBoxProps = {
  title: string
  badge: string
  subtitle?: string
  metrics: FieldBoxMetric[]
  statusBar?: FieldBoxStatusBar
}

export default function FieldBox({
  title,
  badge,
  subtitle,
  metrics,
  statusBar,
}: FieldBoxProps) {
  const statusBarClasses = statusBar?.isCritical
    ? 'from-rose-500 via-orange-500 to-red-500'
    : 'from-sky-500 via-cyan-400 to-blue-400'

  return (
    <div className="group relative overflow-hidden rounded-[1.75rem] border border-slate-200/80 bg-white/90 p-6 shadow-sm backdrop-blur transition duration-300 hover:-translate-y-0.5 hover:shadow-lg">
      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
            Field
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">{title}</h3>
          {subtitle ? (
            <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
          ) : null}
        </div>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
          {badge}
        </span>
      </div>

      {statusBar ? (
        <div className="relative mt-4 rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-3">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
              {statusBar.label}
            </p>
            <p className="text-sm font-semibold text-slate-900">
              {statusBar.value}
            </p>
          </div>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${statusBarClasses} transition-[width] duration-500`}
              style={{ width: `${statusBar.percentage}%` }}
            />
          </div>
          {statusBar.isCritical ? (
            <p className="mt-2 text-xs font-medium text-rose-600">
              Below RAW threshold
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="relative mt-3 space-y-1 border-t border-slate-100 pt-1">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="flex items-baseline justify-between gap-1 border-b border-slate-100 pb-2 last:border-b-0 last:pb-0"
          >
            <p className="text-sm text-slate-500">{metric.label}</p>
            <p className="text-base font-semibold text-slate-900">
              {metric.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
