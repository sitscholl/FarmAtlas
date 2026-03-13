import { useEffect, useState } from 'react'

import api from '../api'
import FieldBox from '../components/FieldBox'
import { type FieldContainer } from '../components/FieldContainer'

export default function Home() {
  const [fields, setFields] = useState<FieldContainer[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const response = await api.get<FieldContainer[]>('/fields')
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
            name={field.name}
            referenceStation={field.reference_station}
            soilType={field.soil_type}
            areaHa={field.area_ha}
            rootDepthCm={field.root_depth_cm}
            humusPct={field.humus_pct}
            pAllowable={field.p_allowable}
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
            Anlagen Uebersicht
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
