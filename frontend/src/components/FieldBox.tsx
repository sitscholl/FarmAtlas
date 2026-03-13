type FieldBoxProps = {
  name: string
  referenceStation: string
  soilType: string
  areaHa: number | null
  rootDepthCm: number
  humusPct: number
  pAllowable: number | null
}

function formatNumber(value: number, digits = 1) {
  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatNullableValue(value: number | null, suffix: string, digits = 1) {
  if (value === null) {
    return 'n/a'
  }

  return `${formatNumber(value, digits)} ${suffix}`.trim()
}

export default function FieldBox({
  name,
  referenceStation,
  soilType,
  areaHa,
  rootDepthCm,
  humusPct,
  pAllowable,
}: FieldBoxProps) {
  const metrics = [
    { label: 'Area', value: formatNullableValue(areaHa, 'ha', 2) },
    { label: 'Root depth', value: formatNullableValue(rootDepthCm, 'cm') },
    { label: 'Humus', value: formatNullableValue(humusPct, '%', 1) },
    { label: 'P allowable', value: formatNullableValue(pAllowable, '', 2) },
  ]

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white/80 p-5 shadow-sm backdrop-blur transition duration-300 hover:-translate-y-0.5 hover:shadow-lg">
      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
            Field
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">{name}</h3>
          <p className="mt-2 text-sm text-slate-500">{soilType} soil</p>
        </div>
        <span className="rounded-full bg-slate-900/5 px-3 py-1 text-xs font-medium text-slate-700">
          {referenceStation}
        </span>
      </div>

      <div className="relative mt-5 grid gap-3 sm:grid-cols-2">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              {metric.label}
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              {metric.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
