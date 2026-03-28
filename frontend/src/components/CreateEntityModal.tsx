import { type FormEvent, useEffect, useMemo, useState } from 'react'

import api from '../api'
import { notifyDataChanged } from '../lib/dataEvents'
import type { FieldRead } from '../types/generated/api'
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
    label: `${field.name}${field.section ? ` (${field.section})` : ''}`,
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
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const needsFieldOptions = useMemo(
    () => action?.fields.some((field) => field.type === 'select' && field.optionsSource === 'fields') ?? false,
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
    if (!isOpen || !needsFieldOptions) {
      return
    }

    const fetchFields = async () => {
      try {
        const response = await api.get<FieldRead[]>('/fields')
        const options = buildFieldOptions(response.data)
        setFieldOptions(options)
        setValues((currentValues) => {
          if (currentValues.field_id || options.length === 0) {
            return currentValues
          }
          return { ...currentValues, field_id: options[0].value }
        })
      } catch (error) {
        console.error('Error loading field options', error)
        setErrorMessage('Die verfuegbaren Anlagen konnten nicht geladen werden.')
      }
    }

    void fetchFields()
  }, [isOpen, needsFieldOptions])

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
      const options = field.optionsSource === 'fields' ? fieldOptions : (field.options ?? [])

      return (
        <select
          id={String(field.id)}
          value={values[String(field.id)] ?? ''}
          onChange={(event) => handleChange(String(field.id), event.target.value)}
          className={commonClasses}
          required={field.required ?? true}
        >
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
