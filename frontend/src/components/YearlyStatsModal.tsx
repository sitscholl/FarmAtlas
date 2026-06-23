import { type FormEvent, useEffect, useState } from 'react'
import { FiX } from 'react-icons/fi'

import api from '../api'
import { getApiErrorMessage } from '../lib/apiErrors'
import { notifyDataChanged } from '../lib/dataEvents'
import type {
  FieldDetailRead,
  YearlyStatsCreate,
  YearlyStatsRead,
  YearlyStatsUpdate,
} from '../types/generated/api'
import FruitCountScopePicker, { type FruitCountScope } from './FruitCountScopePicker'

type YearlyStatsModalProps = {
  isOpen: boolean
  initialScope?: FruitCountScope | null
  fieldDetails?: FieldDetailRead[]
  stats?: YearlyStatsRead | null
  onClose: () => void
}

type NumericField =
  | 'thinning_hours'
  | 'harvest_hours'
  | 'filled_boxes'
  | 'yield_kg'
  | 'revenue'

const NUMERIC_FIELDS: Array<{
  id: NumericField
  label: string
  step: string
  placeholder?: string
}> = [
  { id: 'thinning_hours', label: 'Ausduennstunden', step: '0.25' },
  { id: 'harvest_hours', label: 'Erntestunden', step: '0.25' },
  { id: 'filled_boxes', label: 'Gefuellte Grosskisten', step: '0.1' },
  { id: 'yield_kg', label: 'Ertrag', step: '0.1', placeholder: 'kg' },
  { id: 'revenue', label: 'Umsatz', step: '0.01', placeholder: 'EUR' },
]

function currentSeasonYear() {
  return String(new Date().getFullYear())
}

function optionalText(value: string) {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

function optionalNumber(value: string) {
  const trimmed = value.trim()
  return trimmed === '' ? null : Number(trimmed)
}

function getScopePayload(scope: FruitCountScope) {
  return {
    field_id: scope.type === 'field' ? scope.field_id : null,
    planting_id: scope.type === 'planting' ? scope.planting_id : null,
    section_id: scope.type === 'section' ? scope.section_id : null,
  }
}

function getStatsScope(
  stats: YearlyStatsRead,
  fieldDetails: FieldDetailRead[] | undefined,
): FruitCountScope | null {
  if (stats.field_id !== null && stats.field_id !== undefined) {
    return { type: 'field', field_id: stats.field_id }
  }

  if (stats.planting_id !== null && stats.planting_id !== undefined) {
    for (const fieldDetail of fieldDetails ?? []) {
      const planting = fieldDetail.plantings.find((candidate) => candidate.id === stats.planting_id)
      if (planting !== undefined) {
        return {
          type: 'planting',
          field_id: fieldDetail.field.id,
          planting_id: planting.id,
        }
      }
    }
    return null
  }

  if (stats.section_id !== null && stats.section_id !== undefined) {
    for (const fieldDetail of fieldDetails ?? []) {
      for (const planting of fieldDetail.plantings) {
        const section = planting.sections.find((candidate) => candidate.id === stats.section_id)
        if (section !== undefined) {
          return {
            type: 'section',
            field_id: fieldDetail.field.id,
            planting_id: planting.id,
            section_id: section.id,
          }
        }
      }
    }
  }

  return null
}

function buildNumericValues(stats: YearlyStatsRead | null) {
  return Object.fromEntries(
    NUMERIC_FIELDS.map((field) => [
      field.id,
      stats?.[field.id] === null || stats?.[field.id] === undefined ? '' : String(stats[field.id]),
    ]),
  ) as Record<NumericField, string>
}

export default function YearlyStatsModal({
  isOpen,
  initialScope,
  fieldDetails,
  stats = null,
  onClose,
}: YearlyStatsModalProps) {
  const isEditing = stats !== null
  const [scope, setScope] = useState<FruitCountScope | null>(initialScope ?? null)
  const [seasonYear, setSeasonYear] = useState(currentSeasonYear)
  const [numericValues, setNumericValues] = useState<Record<NumericField, string>>(() => buildNumericValues(null))
  const [notes, setNotes] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      return
    }

    setScope(stats === null ? initialScope ?? null : getStatsScope(stats, fieldDetails))
    setSeasonYear(stats === null ? currentSeasonYear() : String(stats.season_year))
    setNumericValues(buildNumericValues(stats))
    setNotes(stats?.notes ?? '')
    setErrorMessage(null)
    setIsSubmitting(false)
  }, [fieldDetails, initialScope, isOpen, stats])

  const handleNumericChange = (field: NumericField, value: string) => {
    setNumericValues((currentValues) => ({ ...currentValues, [field]: value }))
  }

  const buildPayload = (): YearlyStatsCreate | YearlyStatsUpdate | null => {
    if (scope === null) {
      setErrorMessage('Bitte Anlage, Pflanzung oder Abschnitt auswaehlen.')
      return null
    }

    const parsedYear = Number(seasonYear)
    if (!Number.isInteger(parsedYear) || parsedYear < 1900) {
      setErrorMessage('Bitte ein gueltiges Jahr eingeben.')
      return null
    }

    const parsedNumbers = Object.fromEntries(
      NUMERIC_FIELDS.map((field) => [field.id, optionalNumber(numericValues[field.id])]),
    ) as Record<NumericField, number | null>

    const invalidField = NUMERIC_FIELDS.find((field) => {
      const value = parsedNumbers[field.id]
      return value !== null && (!Number.isFinite(value) || value < 0)
    })
    if (invalidField !== undefined) {
      setErrorMessage(`"${invalidField.label}" muss groesser oder gleich 0 sein.`)
      return null
    }

    return {
      season_year: parsedYear,
      ...getScopePayload(scope),
      ...parsedNumbers,
      notes: optionalText(notes),
    }
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage(null)

    const payload = buildPayload()
    if (payload === null) {
      return
    }

    setIsSubmitting(true)
    try {
      if (stats === null) {
        await api.post<YearlyStatsRead>('/yearly-stats', payload)
      } else {
        await api.put<YearlyStatsRead>(`/yearly-stats/${stats.id}`, payload)
      }
      notifyDataChanged()
      onClose()
    } catch (error) {
      console.error('Error saving yearly stats', error)
      setErrorMessage(getApiErrorMessage(error, 'Die Jahresdaten konnten nicht gespeichert werden.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) {
    return null
  }

  const inputClasses =
    'mt-2 w-full border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100'

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-sm sm:flex sm:items-center sm:justify-center sm:px-4 sm:py-4"
      onClick={onClose}
    >
      <div
        className="flex h-dvh w-full flex-col overflow-hidden bg-white sm:max-h-[calc(100vh-2rem)] sm:max-w-3xl sm:rounded-[2rem] sm:border sm:border-slate-200 sm:shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-100 px-4 py-4 sm:border-b-0 sm:px-6 sm:pt-6 sm:pb-0 sm:p-7">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              {isEditing ? 'Eintrag bearbeiten' : 'Neuer Eintrag'}
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900">
              Jahresdaten
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            aria-label="Modal schliessen"
          >
            <FiX className="h-5 w-5" />
          </button>
        </div>

        <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit}>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:mt-6 sm:px-6 sm:pt-0 sm:pb-0 sm:pr-7">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="lg:col-span-2">
                <span className="text-sm font-medium text-slate-700">Bezugsflaeche</span>
                <FruitCountScopePicker
                  value={scope}
                  onChange={setScope}
                  fieldDetails={fieldDetails}
                  disabled={isSubmitting}
                />
              </div>

              <label className="block">
                <span className="text-sm font-medium text-slate-700">Jahr</span>
                <input
                  type="number"
                  value={seasonYear}
                  onChange={(event) => setSeasonYear(event.target.value)}
                  className={inputClasses}
                  min="1900"
                  step="1"
                  required
                />
              </label>

              {NUMERIC_FIELDS.map((field) => (
                <label key={field.id} className="block">
                  <span className="text-sm font-medium text-slate-700">{field.label}</span>
                  <input
                    type="number"
                    value={numericValues[field.id]}
                    onChange={(event) => handleNumericChange(field.id, event.target.value)}
                    className={inputClasses}
                    min="0"
                    step={field.step}
                    placeholder={field.placeholder}
                  />
                </label>
              ))}

              <label className="block lg:col-span-2">
                <span className="text-sm font-medium text-slate-700">Notizen</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  className={`${inputClasses} min-h-24 resize-y`}
                />
              </label>
            </div>

            {errorMessage ? (
              <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {errorMessage}
              </div>
            ) : null}
          </div>

          <div className="shrink-0 border-t border-slate-100 bg-white px-4 py-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:mt-6 sm:flex sm:justify-end sm:gap-3 sm:px-6 sm:pt-4 sm:pb-6">
            <button
              type="button"
              onClick={onClose}
              className="mb-3 w-full rounded-full border border-slate-200 px-5 py-3 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 sm:mb-0 sm:w-auto"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-full bg-sky-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-sky-300 sm:w-auto"
            >
              {isSubmitting ? 'Speichern...' : isEditing ? 'Aenderungen speichern' : 'Speichern'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
