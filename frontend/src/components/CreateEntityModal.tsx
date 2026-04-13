import { type FormEvent, useEffect, useMemo, useState } from 'react'

import api from '../api'
import { notifyDataChanged } from '../lib/dataEvents'
import type { FieldRead, VarietyRead } from '../types/generated/api'
import {
  type CreateActionConfig,
  type CreateActionField,
  type FieldOption,
} from '../types/createActions'

function calculateDripAmount(field: FieldRead | undefined, duration: string) {
  if (field === undefined) {
    return null
  }

  const hours = Number(duration)
  if (!Number.isFinite(hours) || hours <= 0) {
    return null
  }

  const { drip_distance, drip_discharge, tree_strip_width } = field
  if (
    drip_distance === undefined ||
    drip_discharge === undefined ||
    tree_strip_width === undefined ||
    drip_distance === null ||
    drip_discharge === null ||
    tree_strip_width === null ||
    drip_distance <= 0 ||
    drip_discharge <= 0 ||
    tree_strip_width <= 0
  ) {
    return null
  }

  return hours * drip_discharge / drip_distance / tree_strip_width
}

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
    label: [field.name, field.section, field.variety, String(field.planting_year)]
      .filter((part) => part && String(part).trim() !== '')
      .join(' | '),
  }))
}

function buildVarietyOptions(varieties: VarietyRead[]): FieldOption[] {
  return varieties.map((variety) => ({
    value: variety.name,
    label: `${variety.name}${variety.group ? ` (${variety.group})` : ''}`,
  }))
}

function getSelectOptions(
  field: CreateActionField,
  fieldOptions: FieldOption[],
  varietyOptions: FieldOption[],
): FieldOption[] {
  if (field.type !== 'select') {
    return []
  }

  if (field.optionsSource === 'fields') {
    return fieldOptions
  }
  if (field.optionsSource === 'varieties') {
    return varietyOptions
  }
  return field.options ?? []
}

export default function CreateEntityModal({
  action,
  isOpen,
  initialValues,
  onClose,
}: CreateEntityModalProps) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [fields, setFields] = useState<FieldRead[]>([])
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
    setFields([])
    setErrorMessage(null)
  }, [action, initialValues, isOpen])

  useEffect(() => {
    if (!isOpen || action === null) {
      return
    }

    setValues((currentValues) => {
      const nextValues = { ...currentValues }
      let changed = false

      for (const field of action.fields) {
        if (field.type !== 'select') {
          continue
        }

        const currentValue = nextValues[String(field.id)] ?? ''
        if (currentValue !== '') {
          continue
        }

        const options = getSelectOptions(field, fieldOptions, varietyOptions)
        if (options.length === 0) {
          continue
        }

        nextValues[String(field.id)] = options[0].value
        changed = true
      }

      return changed ? nextValues : currentValues
    })
  }, [action, fieldOptions, isOpen, varietyOptions])

  useEffect(() => {
    if (!isOpen || dynamicOptionSources.size === 0) {
      return
    }

    const fetchAndSeedOptions = async () => {
      try {
        const nextFields = dynamicOptionSources.has('fields')
          ? (await api.get<FieldRead[]>('/fields')).data
          : []
        const nextVarietyOptions = dynamicOptionSources.has('varieties')
          ? buildVarietyOptions((await api.get<VarietyRead[]>('/varieties')).data)
          : []

        setFields(nextFields)
        setFieldOptions(buildFieldOptions(nextFields))
        setVarietyOptions(nextVarietyOptions)
      } catch (error) {
        console.error('Error loading select options', error)
        setErrorMessage('Die verfuegbaren Optionen konnten nicht geladen werden.')
      }
    }

    void fetchAndSeedOptions()
  }, [dynamicOptionSources, isOpen])

  const selectedField = useMemo(
    () => fields.find((field) => String(field.id) === values.field_id),
    [fields, values.field_id],
  )

  useEffect(() => {
    if (!isOpen || action?.id !== 'irrigation') {
      return
    }

    if (values.method !== 'drip') {
      return
    }

    const calculatedAmount = calculateDripAmount(selectedField, values.duration ?? '')
    if (calculatedAmount === null) {
      return
    }

    const nextAmount = String(Math.round(calculatedAmount * 100) / 100)
    if (values.amount === nextAmount) {
      return
    }

    setValues((currentValues) => {
      const refreshedAmount = calculateDripAmount(
        fields.find((field) => String(field.id) === currentValues.field_id),
        currentValues.duration ?? '',
      )

      if (currentValues.method !== 'drip' || refreshedAmount === null) {
        return currentValues
      }

      const resolvedAmount = String(Math.round(refreshedAmount * 100) / 100)
      if (currentValues.amount === resolvedAmount) {
        return currentValues
      }

      return { ...currentValues, amount: resolvedAmount }
    })
  }, [action?.id, fields, isOpen, selectedField, values.amount, values.duration, values.method])

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
      const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null
      const useSecondaryAction = submitter?.dataset.submitKind === 'secondary'
      const submission = useSecondaryAction && action.secondaryAction ? action.secondaryAction : action
      const payload = submission.buildPayload(values)
      const endpoint =
        action.id === 'irrigation' && submission.endpoint === ''
          ? `/fields/${(payload as { field_id: number }).field_id}/irrigation`
          : submission.endpoint

      await api.request({
        method: submission.method ?? 'post',
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
            {action.secondaryAction ? (
              <button
                type="submit"
                data-submit-kind="secondary"
                disabled={isSubmitting}
                className="rounded-full bg-amber-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:bg-amber-200"
              >
                {isSubmitting ? 'Speichern...' : action.secondaryAction.submitLabel}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  )
}
