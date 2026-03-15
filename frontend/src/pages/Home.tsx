import { useEffect, useState } from 'react'

import api from '../api'
import FieldBox, {
  type FieldBoxMetric,
  type FieldBoxStatusBar,
} from '../components/FieldBox'
import { type FieldOverview } from '../types/field'

function formatNumber(value: number, digits = 1) {
  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatOptionalNumber(
  value: number | null,
  suffix: string,
  digits = 1,
) {
  if (value === null) {
    return 'n/a'
  }

  return `${formatNumber(value, digits)} ${suffix}`.trim()
}

function buildFieldMetrics(field: FieldOverview): FieldBoxMetric[] {
  return [
    { label: 'Fläche', value: formatOptionalNumber(field.area_ha, 'ha', 2) },
    { label: 'Wurzeltiefe', value: `${formatNumber(field.root_depth_cm)} cm` },
    { label: 'Humusgehalt', value: `${formatNumber(field.humus_pct, 1)} %` },
    {
      label: 'Wasserdefizit',
      value: formatOptionalNumber(field.current_deficit, 'mm', 1),
    },
  ]
}

function buildSafeRatioBar(field: FieldOverview): FieldBoxStatusBar | undefined {
  if (field.safe_ratio === null) {
    return undefined
  }

  const ratioPercent = Math.round(field.safe_ratio * 100)
  return {
    label: 'Wasserbilanz',
    value: `${ratioPercent}%`,
    percentage: Math.max(0, Math.min(100, ratioPercent)),
    isCritical: field.safe_ratio < 0,
  }
}

export default function Home() {
  const [fields, setFields] = useState<FieldOverview[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const response = await api.get<FieldOverview[]>('/fields/overview')
        setFields(response.data)
      } catch (error) {
        console.error('Error fetching fields', error)
        setErrorMessage('Fields could not be loaded.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchFields()
  }, [])

  const content = (() => {
    if (isLoading) {
      return (
        <div className="mt-10 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
          Loading fields...
        </div>
      )
    }

    if (errorMessage !== null) {
      return (
        <div className="mt-10 rounded-2xl border border-rose-200 bg-rose-50 px-6 py-10 text-center text-rose-700">
          {errorMessage}
        </div>
      )
    }

    if (fields.length === 0) {
      return (
        <div className="mt-10 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
          No fields are configured yet.
        </div>
      )
    }

    return (
      <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {fields.map((field) => (
          <FieldBox
            key={field.id}
            title={field.name}
            badge={field.reference_station}
            subtitle={`Bodenart: ${field.soil_type}`}
            statusBar={buildSafeRatioBar(field)}
            metrics={buildFieldMetrics(field)}
          />
        ))}
      </div>
    )
  })()

  return (
    <section className="relative max-w-5xl">
      <div className="relative rounded-3xl border border-slate-200/70 bg-white/70 p-8 shadow-xl backdrop-blur">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-400">
            Anlagen Übersicht
          </p>
          <h1 className="mt-4 text-4xl font-semibold text-slate-900 sm:text-5xl">
            Oberlenghof
          </h1>
        </div>

        {content}
      </div>
    </section>
  )
}
