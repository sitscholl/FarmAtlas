import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { GoPencil } from 'react-icons/go'
import { PiTrashBold } from 'react-icons/pi'
import { IoMdAdd } from 'react-icons/io'

import api from '../api'
import CreateEntityModal from '../components/CreateEntityModal'
import { irrigationCreateAction } from '../config/createActions'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  buildFieldEditAction,
  buildFieldEditInitialValues,
  buildPlantingCreateAction,
  buildPlantingEditAction,
  buildPlantingEditInitialValues,
  buildSectionCreateAction,
  buildSectionEditAction,
  buildSectionEditInitialValues,
} from '../lib/fieldForm'
import {
  type CreateActionConfig,
} from '../types/createActions'
import {
  type FieldDetailRead,
  type PlantingDetailRead,
  type SectionRead,
  type WaterBalanceSummary,
} from '../types/generated/api'

type DetailMetric = {
  label: string
  value: string
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

function formatBoolean(value: boolean | null | undefined) {
  if (value === null || value === undefined) {
    return 'n/a'
  }

  return value ? 'Ja' : 'Nein'
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return 'n/a'
  }
  return new Intl.DateTimeFormat('de-DE').format(new Date(value))
}

function squareMetresToHectares(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return null
  }
  return value / 10000
}

function buildFieldMetrics(fieldDetail: FieldDetailRead): DetailMetric[] {
  const field = fieldDetail.field
  const sections = fieldDetail.plantings.flatMap((planting) => planting.sections)
  const totalArea = sections.reduce((sum, section) => sum + section.area, 0)
  const treeCount = sections.reduce((sum, section) => sum + (section.tree_count ?? 0), 0)
  const runningMetre = sections.reduce((sum, section) => sum + (section.running_metre ?? 0), 0)

  return [
    { label: 'Flaeche', value: `${formatNumber(squareMetresToHectares(totalArea), 2)} ha` },
    { label: 'Pflanzungen', value: String(fieldDetail.plantings.length) },
    { label: 'Abschnitte', value: String(sections.length) },
    { label: 'Baumzahl', value: treeCount > 0 ? formatNumber(treeCount, 0) : 'n/a' },
    { label: 'Laufmeter', value: runningMetre > 0 ? `${formatNumber(runningMetre, 1)} m` : 'n/a' },
    { label: 'Bodenart', value: field.soil_type ?? 'n/a' },
    { label: 'Bodenschwere', value: field.soil_weight ?? 'n/a' },
    { label: 'Hoehe', value: `${formatNumber(field.elevation, 0)} m` },
  ]
}

function buildIrrigationMetrics(fieldDetail: FieldDetailRead): DetailMetric[] {
  const field = fieldDetail.field
  return [
    { label: 'Tropferabstand', value: `${formatNumber(field.drip_distance, 2)} m` },
    { label: 'Tropferleistung', value: `${formatNumber(field.drip_discharge, 2)} l/h` },
    { label: 'Baumstreifenbreite', value: `${formatNumber(field.tree_strip_width, 2)} m` },
    { label: 'Entziehbarer Wasseranteil', value: `${formatNumber(field.p_allowable, 2)}` },
    { label: 'Ventil offen', value: formatBoolean(field.valve_open) },
  ]
}

function buildWaterMetrics(summary: WaterBalanceSummary): DetailMetric[] {
  return [
    { label: 'Verfuegbarer Wasserspeicher', value: `${formatNumber(summary.available_water_storage, 1)} mm` },
    { label: 'Wasserdefizit', value: `${formatNumber(summary.current_water_deficit, 1)} mm` },
    { label: 'Safe Ratio', value: summary.safe_ratio === null ? 'n/a' : `${formatNumber(summary.safe_ratio * 100, 0)} %` },
    { label: 'Letzte Aktualisierung', value: formatDate(summary.as_of) },
  ]
}

function MetricSection({
  title,
  metrics,
  actions,
}: {
  title: string
  metrics: DetailMetric[]
  actions?: ReactNode
}) {
  return (
    <section className="border border-slate-200 bg-slate-50/80 p-5">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
          {title}
        </h2>
        {actions}
      </div>

      <div className="mt-2 grid sm:grid-cols-2">
        {metrics.map((metric) => (
          <div key={metric.label} className="border border-transparent py-1">
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

function SectionCard({
  section,
  onEdit,
  onDelete,
}: {
  section: SectionRead
  onEdit: (section: SectionRead) => void
  onDelete: (section: SectionRead) => void
}) {
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h4 className="text-base font-semibold text-slate-900">{section.name}</h4>
          <p className="mt-1 text-sm text-slate-500">
            {formatNumber(squareMetresToHectares(section.area), 2)} ha | Pflanzjahr {section.planting_year}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onEdit(section)}
            className="inline-flex items-center gap-2 border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900 transition hover:bg-amber-100"
          >
            <GoPencil />
            Bearbeiten
          </button>
          <button
            type="button"
            onClick={() => onDelete(section)}
            className="inline-flex items-center gap-2 border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100"
          >
            <PiTrashBold />
            Loeschen
          </button>
        </div>
      </div>

      <div className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2 lg:grid-cols-4">
        <div>Baumzahl: {formatNumber(section.tree_count, 0)}</div>
        <div>Baumhoehe: {formatNumber(section.tree_height, 1)} m</div>
        <div>Reihenabstand: {formatNumber(section.row_distance, 1)} m</div>
        <div>Baumabstand: {formatNumber(section.tree_distance, 1)} m</div>
        <div>Laufmeter: {formatNumber(section.running_metre, 1)} m</div>
        <div>Herbizidfrei: {formatBoolean(section.herbicide_free)}</div>
        <div>Gueltig ab: {formatDate(section.valid_from)}</div>
        <div>Gueltig bis: {formatDate(section.valid_to)}</div>
      </div>
    </div>
  )
}

function PlantingCard({
  planting,
  onEdit,
  onDelete,
  onAddSection,
  onEditSection,
  onDeleteSection,
}: {
  planting: PlantingDetailRead
  onEdit: (planting: PlantingDetailRead) => void
  onDelete: (planting: PlantingDetailRead) => void
  onAddSection: (planting: PlantingDetailRead) => void
  onEditSection: (section: SectionRead) => void
  onDeleteSection: (section: SectionRead) => void
}) {
  const totalArea = planting.sections.reduce((sum, section) => sum + section.area, 0)

  return (
    <section className="border border-slate-200 bg-slate-50 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Pflanzung
          </p>
          <h3 className="mt-1 text-xl font-semibold text-slate-900">{planting.variety}</h3>
          <p className="mt-1 text-sm text-slate-500">
            {planting.sections.length} Abschnitte | {formatNumber(squareMetresToHectares(totalArea), 2)} ha | {planting.active ? 'Aktiv' : 'Inaktiv'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onEdit(planting)}
            className="inline-flex items-center gap-2 border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900 transition hover:bg-amber-100"
          >
            <GoPencil />
            Bearbeiten
          </button>
          <button
            type="button"
            onClick={() => onAddSection(planting)}
            className="inline-flex items-center gap-2 border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800 transition hover:bg-sky-100"
          >
            <IoMdAdd />
            Abschnitt
          </button>
          <button
            type="button"
            onClick={() => onDelete(planting)}
            className="inline-flex items-center gap-2 border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100"
          >
            <PiTrashBold />
            Loeschen
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3">
        {planting.sections.length === 0 ? (
          <div className="border border-dashed border-slate-300 bg-white px-4 py-6 text-sm text-slate-500">
            Keine Abschnitte vorhanden.
          </div>
        ) : (
          planting.sections.map((section) => (
            <SectionCard
              key={section.id}
              section={section}
              onEdit={onEditSection}
              onDelete={onDeleteSection}
            />
          ))
        )}
      </div>
    </section>
  )
}

export default function FieldDetail() {
  const navigate = useNavigate()
  const { fieldId } = useParams()
  const [fieldDetail, setFieldDetail] = useState<FieldDetailRead | null>(null)
  const [waterSummary, setWaterSummary] = useState<WaterBalanceSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [activeAction, setActiveAction] = useState<CreateActionConfig | null>(null)
  const [activeInitialValues, setActiveInitialValues] = useState<Record<string, string> | undefined>(undefined)
  const [irrigationInitialValues, setIrrigationInitialValues] = useState<Record<string, string> | undefined>(undefined)
  const [isIrrigationOpen, setIsIrrigationOpen] = useState(false)

  useEffect(() => {
    let isActive = true

    const fetchDetail = async () => {
      if (!fieldId) {
        setErrorMessage('Field id is missing.')
        setIsLoading(false)
        return
      }

      try {
        const [detailResponse, summaryResponse] = await Promise.all([
          api.get<FieldDetailRead>(`/fields/${fieldId}`),
          api.get<WaterBalanceSummary>(`/fields/${fieldId}/water-balance/summary`),
        ])
        if (!isActive) {
          return
        }

        setFieldDetail(detailResponse.data)
        setWaterSummary(summaryResponse.data)
        setErrorMessage(null)
        setIsLoading(false)
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
      void fetchDetail()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => {
      isActive = false
      window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    }
  }, [fieldId])

  const fieldMetrics = useMemo(
    () => (fieldDetail === null ? [] : buildFieldMetrics(fieldDetail)),
    [fieldDetail],
  )
  const irrigationMetrics = useMemo(
    () => (fieldDetail === null ? [] : buildIrrigationMetrics(fieldDetail)),
    [fieldDetail],
  )
  const waterMetrics = useMemo(
    () => (waterSummary === null ? [] : buildWaterMetrics(waterSummary)),
    [waterSummary],
  )

  if (isLoading) {
    return (
      <div className="w-full max-w-6xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
        Loading field details...
      </div>
    )
  }

  if (errorMessage !== null || fieldDetail === null || waterSummary === null) {
    return (
      <div className="w-full max-w-6xl border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
        {errorMessage ?? 'Field could not be found.'}
      </div>
    )
  }

  const { field, plantings, cadastral_parcels } = fieldDetail

  const openAction = (action: CreateActionConfig | null, initialValues?: Record<string, string>) => {
    setActiveAction(action)
    setActiveInitialValues(initialValues)
  }

  const handleDeleteField = async () => {
    const confirmed = window.confirm(`Soll die Anlage "${field.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/fields/${field.id}`)
      notifyDataChanged()
      navigate('/fields')
    } catch (error) {
      console.error(`Error deleting field ${field.id}`, error)
      setErrorMessage('Die Anlage konnte nicht geloescht werden.')
    }
  }

  const handleDeletePlanting = async (planting: PlantingDetailRead) => {
    const confirmed = window.confirm(`Soll die Pflanzung "${planting.variety}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/plantings/${planting.id}`)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting planting ${planting.id}`, error)
      setErrorMessage('Die Pflanzung konnte nicht geloescht werden.')
    }
  }

  const handleDeleteSection = async (section: SectionRead) => {
    const confirmed = window.confirm(`Soll der Abschnitt "${section.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }

    try {
      await api.delete(`/sections/${section.id}`)
      notifyDataChanged()
    } catch (error) {
      console.error(`Error deleting section ${section.id}`, error)
      setErrorMessage('Der Abschnitt konnte nicht geloescht werden.')
    }
  }

  return (
    <section className="w-full max-w-6xl">
      <div className="px-3 py-4 sm:px-6 sm:py-6 lg:p-8">
        <Link
          to="/fields"
          className="text-sm font-medium text-sky-700 hover:text-sky-900"
        >
          Zurueck zur Tabellenansicht
        </Link>

        <div className="mt-4 flex flex-wrap items-start justify-between gap-4 border-b border-black pb-3 sm:mt-6 sm:gap-6 sm:pb-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Field Detail
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              {field.name}
            </h1>
            <p className="relative mt-2 whitespace-pre-line text-sm text-slate-500">
              {field.group}{'\n'}
              Provider: {field.reference_provider.toUpperCase()}{'\n'}
              Station: {field.reference_station}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => openAction(buildFieldEditAction(field), buildFieldEditInitialValues(field))}
              className="inline-flex items-center gap-2 border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 transition hover:bg-amber-100"
            >
              <GoPencil />
              Anlage bearbeiten
            </button>
            <button
              type="button"
              onClick={() => {
                setIrrigationInitialValues({ field_ids: JSON.stringify([field.id]) })
                setIsIrrigationOpen(true)
              }}
              className="inline-flex items-center gap-2 border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800 transition hover:bg-sky-100"
            >
              <IoMdAdd />
              Bewaesserung
            </button>
            <button
              type="button"
              onClick={handleDeleteField}
              className="inline-flex items-center gap-2 border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100"
            >
              <PiTrashBold />
              Anlage loeschen
            </button>
          </div>
        </div>

        <h2 className="mt-12 text-4xl font-semibold text-slate-900">
          Detailinfo
        </h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr_1fr]">
          <MetricSection title="Anlage" metrics={fieldMetrics} />
          <MetricSection title="Bewaesserung" metrics={irrigationMetrics} />
          <MetricSection title="Wasserhaushalt" metrics={waterMetrics} />
        </div>

        <section className="mt-10 border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-4 border-b border-slate-200 pb-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                Pflanzungen
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                Feldstruktur
              </h2>
            </div>
            <button
              type="button"
              onClick={() => openAction(buildPlantingCreateAction(field.id))}
              className="inline-flex items-center gap-2 border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800 transition hover:bg-sky-100"
            >
              <IoMdAdd />
              Pflanzung
            </button>
          </div>

          <div className="mt-4 grid gap-4">
            {plantings.length === 0 ? (
              <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                Keine Pflanzungen vorhanden.
              </div>
            ) : (
              plantings.map((planting) => (
                <PlantingCard
                  key={planting.id}
                  planting={planting}
                  onEdit={(selectedPlanting) =>
                    openAction(
                      buildPlantingEditAction(selectedPlanting),
                      buildPlantingEditInitialValues(selectedPlanting),
                    )
                  }
                  onDelete={handleDeletePlanting}
                  onAddSection={(selectedPlanting) => openAction(buildSectionCreateAction(selectedPlanting.id))}
                  onEditSection={(section) =>
                    openAction(
                      buildSectionEditAction(section),
                      buildSectionEditInitialValues(section),
                    )
                  }
                  onDeleteSection={handleDeleteSection}
                />
              ))
            )}
          </div>
        </section>

        <section className="mt-10 border border-slate-200 bg-white p-5">
          <div className="border-b border-slate-200 pb-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
              Katastralparzellen
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">
              Parzellen
            </h2>
          </div>

          <div className="mt-4 grid gap-3">
            {cadastral_parcels.length === 0 ? (
              <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                Keine Parzellen vorhanden.
              </div>
            ) : (
              cadastral_parcels.map((parcel) => (
                <div key={parcel.id} className="border border-slate-200 bg-slate-50 px-4 py-4">
                  <div className="text-base font-semibold text-slate-900">
                    {parcel.municipality_id} / {parcel.parcel_id}
                  </div>
                  <div className="mt-1 text-sm text-slate-500">
                    {formatNumber(squareMetresToHectares(parcel.area), 2)} ha
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <CreateEntityModal
        action={activeAction}
        isOpen={activeAction !== null}
        initialValues={activeInitialValues}
        onClose={() => {
          setActiveAction(null)
          setActiveInitialValues(undefined)
        }}
      />
      <CreateEntityModal
        action={irrigationCreateAction}
        isOpen={isIrrigationOpen}
        initialValues={irrigationInitialValues}
        onClose={() => {
          setIsIrrigationOpen(false)
          setIrrigationInitialValues(undefined)
        }}
      />
    </section>
  )
}
