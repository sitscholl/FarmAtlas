import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import api from '../api'
import WaterBalanceChart from '../components/WaterBalanceChart'
import { type FieldOverview, type WaterBalanceSeriesPoint } from '../types/field'

function formatNumber(value: number | null, digits = 1) {
  if (value === null) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatReference(provider: string, stationId: string) {
  return `${provider}: ${stationId}`
}

export default function FieldDetail() {
  const { fieldId } = useParams()
  const [field, setField] = useState<FieldOverview | null>(null)
  const [series, setSeries] = useState<WaterBalanceSeriesPoint[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
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
        setField(overviewResponse.data)
        setSeries(seriesResponse.data)
      } catch (error) {
        console.error('Error fetching field detail', error)
        setErrorMessage('Field details could not be loaded.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchDetail()
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

  return (
    <section className="w-full max-w-6xl">
      <div className="rounded-3xl border border-slate-200/80 bg-white/90 p-8 shadow-sm">
        <Link
          to="/"
          className="text-sm font-medium text-sky-700 hover:text-sky-900"
        >
          Back to dashboard
        </Link>

        <div className="mt-6 flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Field Detail
            </p>
            <h1 className="mt-3 text-4xl font-semibold text-slate-900">
              {field.name}
            </h1>
            <p className="mt-3 text-sm text-slate-500">
              Bodentyp: {field.soil_type}, Referenzstation: {formatReference(field.reference_provider, field.reference_station)}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Safe ratio
              </p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {formatNumber(
                  field.safe_ratio === null ? null : field.safe_ratio * 100,
                  0,
                )}
                %
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Current deficit
              </p>
              <p className="mt-1 text-lg font-semibold text-slate-900">
                {formatNumber(field.current_deficit, 1)} mm
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              Area
            </p>
            <p className="mt-1 text-base font-semibold text-slate-900">
              {formatNumber(field.area_ha, 2)} ha
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              Root depth
            </p>
            <p className="mt-1 text-base font-semibold text-slate-900">
              {formatNumber(field.root_depth_cm)} cm
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              Field capacity
            </p>
            <p className="mt-1 text-base font-semibold text-slate-900">
              {formatNumber(field.field_capacity, 1)} mm
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
              Updated
            </p>
            <p className="mt-1 text-base font-semibold text-slate-900">
              {field.water_balance_as_of ?? 'n/a'}
            </p>
          </div>
        </div>

        <div className="mt-10">
          <WaterBalanceChart data={series} />
        </div>
      </div>
    </section>
  )
}
