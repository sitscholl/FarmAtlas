type FieldBoxProps = {
  name: string
  year: number
  waterBalance: number
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)))
}

export default function FieldBox({ name, year, waterBalance }: FieldBoxProps) {
  const clamped = clampPercent(waterBalance)

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white/80 p-5 shadow-sm backdrop-blur transition duration-300 hover:-translate-y-0.5 hover:shadow-lg">

      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
            Field
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">{name}</h3>
        </div>
        <span className="rounded-full bg-slate-900/5 px-3 py-1 text-xs font-medium text-slate-700">
          {year}
        </span>
      </div>

      <div className="relative mt-5">
        <div className="flex items-center justify-between text-sm text-slate-600">
          <span>Water balance</span>
          <span className="font-semibold text-slate-900">{clamped}%</span>
        </div>
        <div className="mt-2 h-2 rounded-full bg-slate-100">
          <div
            className="h-2 rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400"
            style={{ width: `${clamped}%` }}
          />
        </div>
      </div>
    </div>
  )
}
