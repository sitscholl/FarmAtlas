import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { FiX } from 'react-icons/fi'

import api from '../api'
import GroupedFieldSelector from './GroupedFieldSelector'
import { notifyDataChanged } from '../lib/dataEvents'
import { getApiErrorMessage, getBulkMutationMessage } from '../lib/apiErrors'
import type { FieldRead, PhenologicalStageDefinition, VarietyRead } from '../types/generated/api'
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
          const defaultValue =
            field.required === false
              ? field.defaultValue ?? ''
              : field.defaultValue ?? today
          return [field.id, String(defaultValue)]
        }

        return [field.id, String('defaultValue' in field ? (field.defaultValue ?? '') : '')]
      }),
    ),
    ...initialValues,
  }
}

function buildFieldOptions(fields: FieldRead[]): FieldOption[] {
  return fields.map((field) => ({
    value: String(field.id),
    label: [field.group, field.name]
      .filter((part) => String(part).trim() !== '')
      .join(' | '),
  }))
}

function buildVarietyOptions(
  varieties: VarietyRead[],
  { includeEmpty = false }: { includeEmpty?: boolean } = {},
): FieldOption[] {
  const options = varieties.map((variety) => ({
    value: variety.name,
    label: `${variety.name}${variety.group ? ` (${variety.group})` : ''}`,
  }))

  return includeEmpty
    ? [{ value: '', label: 'Standardwert' }, ...options]
    : options
}

function buildPhenologicalStageOptions(stages: PhenologicalStageDefinition[]): FieldOption[] {
  return stages
    .slice()
    .sort((left, right) => left.sort_order - right.sort_order)
    .map((stage) => ({
      value: stage.code,
      label: stage.bbch_code === null || stage.bbch_code === undefined
        ? stage.label
        : `${stage.label} (BBCH ${stage.bbch_code})`,
    }))
}

function getSelectOptions(
  field: CreateActionField,
  fieldOptions: readonly FieldOption[],
  varietyOptions: readonly FieldOption[],
  optionalVarietyOptions: readonly FieldOption[],
  phenologicalStageOptions: readonly FieldOption[],
): readonly FieldOption[] {
  if (field.type !== 'select') {
    return []
  }

  if (field.optionsSource === 'fields') {
    return fieldOptions
  }
  if (field.optionsSource === 'varieties') {
    return varietyOptions
  }
  if (field.optionsSource === 'varietiesOptional') {
    return optionalVarietyOptions
  }
  if (field.optionsSource === 'phenologicalStages') {
    return phenologicalStageOptions
  }
  return field.options ?? []
}

function parseSelectedIds(value: string) {
  if (value.trim() === '') {
    return []
  }

  try {
    const parsed = JSON.parse(value) as unknown
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed
      .map((entry) => Number(entry))
      .filter((entry) => Number.isInteger(entry) && entry > 0)
  } catch {
    return []
  }
}

export default function CreateEntityModal({
  action,
  isOpen,
  initialValues,
  onClose,
}: CreateEntityModalProps) {
  const [values, setValues] = useState<Record<string, string>>({})
  const hasManualIrrigationAmountRef = useRef(false)
  const [fields, setFields] = useState<FieldRead[]>([])
  const [fieldOptions, setFieldOptions] = useState<FieldOption[]>([])
  const [varietyOptions, setVarietyOptions] = useState<FieldOption[]>([])
  const [optionalVarietyOptions, setOptionalVarietyOptions] = useState<FieldOption[]>([])
  const [phenologicalStageOptions, setPhenologicalStageOptions] = useState<FieldOption[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const needsFieldCatalog = useMemo(
    () =>
      action?.id === 'irrigation' ||
      action?.fields.some(
        (field) =>
          (field.type === 'select' && field.optionsSource === 'fields') ||
          (field.type === 'custom' && field.renderer === 'groupedFieldSelector'),
      ) === true,
    [action],
  )

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
    hasManualIrrigationAmountRef.current = false
    setFields([])
    setFieldOptions([])
    setVarietyOptions([])
    setOptionalVarietyOptions([])
    setPhenologicalStageOptions([])
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

        const options = getSelectOptions(
          field,
          fieldOptions,
          varietyOptions,
          optionalVarietyOptions,
          phenologicalStageOptions,
        )
        if (options.length === 0) {
          continue
        }

        nextValues[String(field.id)] = options[0].value
        changed = true
      }

      return changed ? nextValues : currentValues
    })
  }, [action, fieldOptions, isOpen, optionalVarietyOptions, phenologicalStageOptions, varietyOptions])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    if (dynamicOptionSources.size === 0 && !needsFieldCatalog) {
      return
    }

    const fetchAndSeedOptions = async () => {
      try {
        const varietiesData =
          dynamicOptionSources.has('varieties') || dynamicOptionSources.has('varietiesOptional')
            ? (await api.get<VarietyRead[]>('/varieties')).data
            : []
        const phenologicalStagesData = dynamicOptionSources.has('phenologicalStages')
          ? (await api.get<PhenologicalStageDefinition[]>('/phenological-stages')).data
          : []
        const nextFields = needsFieldCatalog || dynamicOptionSources.has('fields')
          ? (await api.get<FieldRead[]>('/fields')).data
          : []
        const nextVarietyOptions = dynamicOptionSources.has('varieties')
          ? buildVarietyOptions(varietiesData)
          : []
        const nextOptionalVarietyOptions = dynamicOptionSources.has('varietiesOptional')
          ? buildVarietyOptions(varietiesData, { includeEmpty: true })
          : []

        setFields(nextFields)
        setFieldOptions(buildFieldOptions(nextFields))
        setVarietyOptions(nextVarietyOptions)
        setOptionalVarietyOptions(nextOptionalVarietyOptions)
        setPhenologicalStageOptions(buildPhenologicalStageOptions(phenologicalStagesData))
      } catch (error) {
        console.error('Error loading select options', error)
        setErrorMessage('Die verfuegbaren Optionen konnten nicht geladen werden.')
      }
    }

    void fetchAndSeedOptions()
  }, [dynamicOptionSources, isOpen, needsFieldCatalog])

  const selectedFieldIds = useMemo(
    () => parseSelectedIds(values.field_ids ?? ''),
    [values.field_ids],
  )

  const selectedField = useMemo(
    () => {
      if (values.field_id) {
        return fields.find((field) => String(field.id) === values.field_id)
      }

      if (selectedFieldIds.length === 1) {
        return fields.find((field) => field.id === selectedFieldIds[0])
      }

      return undefined
    },
    [fields, selectedFieldIds, values.field_id],
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
      const currentSelectedFieldIds = parseSelectedIds(currentValues.field_ids ?? '')
      const fieldForCalculation = currentValues.field_id
        ? fields.find((field) => String(field.id) === currentValues.field_id)
        : currentSelectedFieldIds.length === 1
          ? fields.find((field) => field.id === currentSelectedFieldIds[0])
          : undefined

      const refreshedAmount = calculateDripAmount(
        fieldForCalculation,
        currentValues.duration ?? '',
      )

      if (currentValues.method !== 'drip' || refreshedAmount === null) {
        return currentValues
      }

      const resolvedAmount = String(Math.round(refreshedAmount * 100) / 100)
      if (hasManualIrrigationAmountRef.current) {
        return currentValues
      }

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
    if (action?.id === 'irrigation') {
      if (fieldId === 'amount') {
        hasManualIrrigationAmountRef.current = true
      } else if (fieldId === 'field_id' || fieldId === 'field_ids' || fieldId === 'duration' || fieldId === 'method') {
        hasManualIrrigationAmountRef.current = false
      }
    }

    setValues((currentValues) => ({ ...currentValues, [fieldId]: nextValue }))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)

    try {
      const missingRequiredField = action.fields.find((field) => {
        if (field.required === false) {
          return false
        }

        if (field.type !== 'custom') {
          return false
        }

        const currentValue = values[String(field.id)] ?? ''
        if (currentValue.trim() === '') {
          return true
        }

        return parseSelectedIds(currentValue).length === 0
      })

      if (missingRequiredField) {
        setErrorMessage(`"${missingRequiredField.label}" ist erforderlich.`)
        return
      }

      const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null
      const useSecondaryAction = submitter?.dataset.submitKind === 'secondary'
      const submission = useSecondaryAction && action.secondaryAction ? action.secondaryAction : action
      const payload = submission.buildPayload(values)
      const endpoint =
        action.id === 'irrigation' && submission.endpoint === ''
          ? `/fields/${(payload as { field_id: number }).field_id}/irrigation`
          : submission.endpoint

      const response = await api.request({
        method: submission.method ?? 'post',
        url: endpoint,
        data: payload,
      })
      const bulkMutationMessage = getBulkMutationMessage(response.data)
      notifyDataChanged()
      if (bulkMutationMessage !== null) {
        setErrorMessage(bulkMutationMessage)
        return
      }
      onClose()
    } catch (error) {
      console.error(`Error saving ${action.id}`, error)
      setErrorMessage(getApiErrorMessage(error, 'Die Daten konnten nicht gespeichert werden.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const renderField = (field: CreateActionField) => {
    const commonClasses =
      'mt-2 w-full border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100'

    if (field.type === 'custom') {
      if (field.renderer === 'groupedFieldSelector') {
        return (
          <GroupedFieldSelector
            value={values[String(field.id)] ?? ''}
            onChange={(nextValue) => handleChange(String(field.id), nextValue)}
            disabled={isSubmitting}
            selectionMode={field.selectionMode ?? 'fields'}
          />
        )
      }

      return null
    }

    if (field.type === 'select') {
      const options =
        field.optionsSource === 'fields'
          ? fieldOptions
          : field.optionsSource === 'varieties'
            ? varietyOptions
            : field.optionsSource === 'varietiesOptional'
              ? optionalVarietyOptions
              : field.optionsSource === 'phenologicalStages'
                ? phenologicalStageOptions
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
    <div
      className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-sm sm:flex sm:items-center sm:justify-center sm:px-4 sm:py-4"
      onClick={onClose}
    >
      <div
        className="flex h-dvh w-full flex-col overflow-hidden bg-white sm:max-h-[calc(100vh-2rem)] sm:max-w-xl sm:rounded-[2rem] sm:border sm:border-slate-200 sm:shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-100 px-4 py-4 sm:border-b-0 sm:px-6 sm:pt-6 sm:pb-0 sm:p-7">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              {action.method === 'put' ? 'Eintrag bearbeiten' : 'Neuer Eintrag'}
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900">
              {action.title}
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

        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={handleSubmit}
        >
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:mt-6 sm:px-6 sm:pt-0 sm:pb-0 sm:pr-7">
            <div className="grid gap-4 lg:grid-cols-2">
              {action.fields.map((field) =>
                field.type === 'custom' ? (
                  <div key={String(field.id)} className="block lg:col-span-2">
                    <span className="text-sm font-medium text-slate-700">{field.label}</span>
                    {renderField(field)}
                  </div>
                ) : (
                  <label key={String(field.id)} htmlFor={String(field.id)} className="block">
                    <span className="text-sm font-medium text-slate-700">{field.label}</span>
                    {renderField(field)}
                  </label>
                ),
              )}
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
              className="hidden rounded-full border border-slate-200 px-5 py-3 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 sm:inline-flex"
            >
              Abbrechen
            </button>
            <div className="flex flex-col-reverse gap-3 sm:flex-row">
              <button
                type="button"
                onClick={onClose}
                className="rounded-full border border-slate-200 px-5 py-3 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 sm:hidden"
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
          </div>
        </form>
      </div>
    </div>
  )
}
