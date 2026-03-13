export type FieldBoxMetric = {
  label: string
  value: string
}

type FieldBoxProps = {
  title: string
  badge: string
  subtitle?: string
  metrics: FieldBoxMetric[]
}

export default function FieldBox({
  title,
  badge,
  subtitle,
  metrics,
}: FieldBoxProps) {
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
