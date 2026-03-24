import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import api from '../api'
import WaterBalanceChart from '../components/WaterBalanceChart'
import { DATA_CHANGED_EVENT } from '../lib/dataEvents'
import { type FieldOverview, type WaterBalanceSeriesPoint } from '../types/field'

const FORECAST_DAYS = 6

type DetailMetric = {
  label: string
  value: string
  accent?: boolean
}

function formatNumber(value: number | null, digits = 1) {
  if (value === null) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatBoolean(value: boolean | null) {
  if (value === null) {
    return 'n/a'
  }

  return value ? 'Ja' : 'Nein'
}

function buildSubtitle(field: FieldOverview) {
  return [
    field.section ? `Abschnitt: ${field.section}` : null,
    `Sorte: ${field.variety}`,
    `Bodenart: ${field.soil_type}`,
    field.soil_weight ? `Bodenschwere: ${field.soil_weight}` : null,
  ]
    .filter((part): part is string => part !== null)
    .join('\n')
}

function buildFieldMetrics(field: FieldOverview): DetailMetric[] {
  return [
    { label: 'Flaeche', value: `${formatNumber(field.area_ha, 2)} ha` },
    { label: 'Pflanzjahr', value: String(field.planting_year) },
    { label: 'Baumzahl', value: formatNumber(field.tree_count, 0) },
    { label: 'Baumhoehe', value: `${formatNumber(field.tree_height, 1)} cm` },
    { label: 'Effektive Wurzeltiefe', value: `${formatNumber(field.effective_root_depth_cm)} cm` },
    { label: 'Reihenabstand', value: `${formatNumber(field.row_distance, 1)} m` },
    { label: 'Baumabstand', value: `${formatNumber(field.tree_distance, 1)} m` },
    { label: 'Laufmeter', value: `${formatNumber(field.running_metre, 1)} m` },
    { label: 'Herbizidfrei', value: formatBoolean(field.herbicide_free) },
    { label: 'Status', value: field.active ? 'Aktiv' : 'Inaktiv' },
  ]
}

function buildWaterMetrics(field: FieldOverview): DetailMetric[] {
  return [
    { label: 'Verfuegbarer Wasserspeicher', value: `${formatNumber(field.available_water_storage, 1)} mm` },
    { label: 'Wasserdefizit', value: `${formatNumber(field.current_water_deficit, 1)} mm` },
    { label: 'Letzte Aktualisierung', value: field.water_balance_as_of ?? 'n/a' },
  ]
}

function MetricSection({
  title,
  metrics,
}: {
  title: string
  metrics: DetailMetric[]
}) {
  return (
    <section className="rounded-[1.5rem] bg-white border border-slate-200/80 bg-slate-50/80 p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
          {title}
        </h2>
      </div>

      <div className="mt-2 grid sm:grid-cols-2">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className={
              metric.accent
                ? 'rounded-2xl border border-slate-200 px-4 py-3 shadow-sm'
                : 'rounded-2xl border border-transparent py-1'
            }
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
              {metric.label}
            </p>
            <p className="text-lg font-semibold text-slate-900">
              {metric.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function FieldDetail() {
  const { fieldId } = useParams()
  const [field, setField] = useState<FieldOverview | null>(null)
  const [series, setSeries] = useState<WaterBalanceSeriesPoint[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isForecastLoading, setIsForecastLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let isActive = true

    const fetchDetail = async () => {
      if (!fieldId) {
        setErrorMessage('Field id is missing.')
        setIsLoading(false)
        return
      }

      try {
        const [overviewResponse, seriesResponse] = await Promise.all([
          api.get<FieldOverview>(`/fields/${fieldId}/overview`),
          api.get<WaterBalanceSeriesPoint[]>(`/fields/${fieldId}/water-balance/series`),
        ])
        if (!isActive) {
          return
        }

        setField(overviewResponse.data)
        setSeries(seriesResponse.data)
        setErrorMessage(null)
        setIsLoading(false)

        setIsForecastLoading(true)
        try {
          const forecastResponse = await api.get<WaterBalanceSeriesPoint[]>(
            `/fields/${fieldId}/water-balance/series`,
            {
              params: { forecast_days: FORECAST_DAYS },
            },
          )
          if (!isActive) {
            return
          }
          setSeries(forecastResponse.data)
        } catch (error) {
          console.error('Error fetching forecast water-balance data', error)
        } finally {
          if (isActive) {
            setIsForecastLoading(false)
          }
        }
      } catch (error) {
        if (!isActive) {
          return
        }
        console.error('Error fetching field detail', error)
        setErrorMessage('Field details could not be loaded.')
        setIsLoading(false)
      }
    }

    void fetchDetail()

    const handleDataChanged = () => {
      setIsLoading(true)
      setIsForecastLoading(false)
      void fetchDetail()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => {
      isActive = false
      window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    }
  }, [fieldId])

  if (isLoading) {
    return (
      <div className="w-full max-w-6xl rounded-3xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
        Loading field details...
      </div>
    )
  }

  if (errorMessage !== null || field === null) {
    return (
      <div className="w-full max-w-6xl rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
        {errorMessage ?? 'Field could not be found.'}
      </div>
    )
  }

  const fieldMetrics = buildFieldMetrics(field)
  const waterMetrics = buildWaterMetrics(field)

  return (
    <section className="w-full max-w-6xl">
      <div className="px-3 py-4 sm:px-6 sm:py-6 lg:p-8">
        <Link
          to="/"
          className="text-sm font-medium text-sky-700 hover:text-sky-900"
        >
          Back to dashboard
        </Link>

        <div className="mt-4 flex flex-wrap items-start justify-between gap-4 border-b border-black pb-3 sm:mt-6 sm:gap-6 sm:pb-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Field Detail
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              {field.name}
            </h1>
            <p className="relative mt-2 text-sm text-slate-500 whitespace-pre-line">{ buildSubtitle(field) }</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Provider
              </p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {field.reference_provider.toUpperCase()}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Station
              </p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {field.reference_station}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-10">
          <WaterBalanceChart data={series} />
          {isForecastLoading ? (
            <p className="mt-3 text-sm text-slate-500">
              Lade Prognosedaten...
            </p>
          ) : null}
        </div>

        <h1 className="mt-12 text-4xl font-semibold text-slate-900">
          Detailinfo
        </h1>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.7fr_1fr]">
          <MetricSection title="Anlage" metrics={fieldMetrics} />
          <MetricSection title="Wasserhaushalt" metrics={waterMetrics} />
        </div>

      </div>
    </section>
  )
}
