import { type FormEvent, useEffect, useMemo, useState } from 'react'

import api from '../api'
import { notifyDataChanged } from '../lib/dataEvents'
import type { FieldRead, VarietyRead } from '../types/generated/api'
import {
  type CreateActionConfig,
  type CreateActionField,
  type FieldOption,
} from '../types/createActions'

type CreateEntityModalProps = {
  action: CreateActionConfig | null
  isOpen: boolean
  initialValues?: Record<string, string>
  onClose: () => void
}

function buildInitialValues(
  action: CreateActionConfig | null,
  initialValues?: Record<string, string>,
) {
  if (action === null) {
    return {}
  }

  return {
    ...Object.fromEntries(
      action.fields.map((field) => {
        if (field.type === 'date') {
          const today = new Date().toISOString().slice(0, 10)
          return [field.id, String(field.defaultValue ?? today)]
        }

        return [field.id, String(field.defaultValue ?? '')]
      }),
    ),
    ...initialValues,
  }
}

function buildFieldOptions(fields: FieldRead[]): FieldOption[] {
  return fields.map((field) => ({
    value: String(field.id),
    label: field.unique_name,
  }))
}

function buildVarietyOptions(varieties: VarietyRead[]): FieldOption[] {
  return varieties.map((variety) => ({
    value: variety.name,
    label: `${variety.name}${variety.group ? ` (${variety.group})` : ''}`,
  }))
}

export default function CreateEntityModal({
  action,
  isOpen,
  initialValues,
  onClose,
}: CreateEntityModalProps) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [fieldOptions, setFieldOptions] = useState<FieldOption[]>([])
  const [varietyOptions, setVarietyOptions] = useState<FieldOption[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const dynamicOptionSources = useMemo(
    () =>
      new Set(
        action?.fields
          .filter(
            (field): field is Extract<CreateActionField, { type: 'select' }> =>
              field.type === 'select' && field.optionsSource !== undefined,
          )
          .map((field) => field.optionsSource) ?? [],
      ),
    [action],
  )

  useEffect(() => {
    if (!isOpen) {
      return
    }

    setValues(buildInitialValues(action, initialValues))
    setErrorMessage(null)
  }, [action, initialValues, isOpen])

  useEffect(() => {
    if (!isOpen || dynamicOptionSources.size === 0) {
      return
    }

    const fetchAndSeedOptions = async () => {
      try {
        const nextFieldOptions = dynamicOptionSources.has('fields')
          ? buildFieldOptions((await api.get<FieldRead[]>('/fields')).data)
          : []
        const nextVarietyOptions = dynamicOptionSources.has('varieties')
          ? buildVarietyOptions((await api.get<VarietyRead[]>('/varieties')).data)
          : []

        setFieldOptions(nextFieldOptions)
        setVarietyOptions(nextVarietyOptions)
        setValues((currentValues) => {
          const nextValues = { ...currentValues }
          if (!nextValues.field_id && nextFieldOptions.length > 0) {
            nextValues.field_id = nextFieldOptions[0].value
          }
          if (!nextValues.variety && nextVarietyOptions.length > 0) {
            nextValues.variety = nextVarietyOptions[0].value
          }
          return nextValues
        })
      } catch (error) {
        console.error('Error loading select options', error)
        setErrorMessage('Die verfuegbaren Optionen konnten nicht geladen werden.')
      }
    }

    void fetchAndSeedOptions()
  }, [dynamicOptionSources, isOpen])

  if (!isOpen || action === null) {
    return null
  }

  const handleChange = (fieldId: string, nextValue: string) => {
    setValues((currentValues) => ({ ...currentValues, [fieldId]: nextValue }))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)

    try {
      const payload = action.buildPayload(values)
      const endpoint =
        action.id === 'irrigation' && action.endpoint === ''
          ? `/fields/${(payload as { field_id: number }).field_id}/irrigation`
          : action.endpoint

      await api.request({
        method: action.method ?? 'post',
        url: endpoint,
        data: payload,
      })
      notifyDataChanged()
      onClose()
    } catch (error) {
      console.error(`Error saving ${action.id}`, error)
      setErrorMessage('Die Daten konnten nicht gespeichert werden.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const renderField = (field: CreateActionField) => {
    const commonClasses =
      'mt-2 w-full border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100'

    if (field.type === 'select') {
      const options =
        field.optionsSource === 'fields'
          ? fieldOptions
          : field.optionsSource === 'varieties'
            ? varietyOptions
            : (field.options ?? [])

      return (
        <select
          id={String(field.id)}
          value={values[String(field.id)] ?? ''}
          onChange={(event) => handleChange(String(field.id), event.target.value)}
          className={commonClasses}
          required={field.required ?? true}
        >
          {options.length === 0 ? (
            <option value="">
              {field.optionsSource === 'varieties' ? 'Keine Sorten vorhanden' : 'Keine Auswahl verfuegbar'}
            </option>
          ) : null}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )
    }

    return (
      <input
        id={String(field.id)}
        type={field.type}
        value={values[String(field.id)] ?? ''}
        onChange={(event) => handleChange(String(field.id), event.target.value)}
        placeholder={field.placeholder}
        step={field.type === 'number' ? field.step : undefined}
        className={commonClasses}
        required={field.required ?? true}
      />
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4 py-4 backdrop-blur-sm">
      <div className="flex max-h-[calc(100vh-2rem)] w-full max-w-xl flex-col overflow-hidden rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl sm:p-7">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              {action.method === 'put' ? 'Eintrag bearbeiten' : 'Neuer Eintrag'}
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900">
              {action.title}
            </h2>
          </div>
        </div>

        <form
          className="mt-6 overflow-y-auto pr-1"
          onSubmit={handleSubmit}
        >
          <div className="grid gap-4 lg:grid-cols-2">
          {action.fields.map((field) => (
            <label key={String(field.id)} htmlFor={String(field.id)} className="block">
              <span className="text-sm font-medium text-slate-700">{field.label}</span>
              {renderField(field)}
            </label>
          ))}
          </div>

          {errorMessage ? (
            <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <div className="mt-6 flex justify-end gap-3 border-t border-slate-100 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-200 px-5 py-3 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-full bg-sky-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-sky-300"
            >
              {isSubmitting ? 'Speichern...' : action.submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
