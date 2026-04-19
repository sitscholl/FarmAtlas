import { useEffect, useMemo, useState } from 'react'

import api from '../api'
import type { FieldRead } from '../types/generated/api'

type GroupedFieldSelectorProps = {
  value: string
  onChange: (nextValue: string) => void
  disabled?: boolean
}

function parseSelectedFieldIds(value: string) {
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

function serializeSelectedFieldIds(fieldIds: number[]) {
  return JSON.stringify([...new Set(fieldIds)].sort((left, right) => left - right))
}

export default function GroupedFieldSelector({
  value,
  onChange,
  disabled = false,
}: GroupedFieldSelectorProps) {
  const [fields, setFields] = useState<FieldRead[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchFields = async () => {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await api.get<FieldRead[]>('/fields')
        setFields(
          response.data
            .slice()
            .sort((left, right) => {
              const groupCompare = left.group.localeCompare(right.group, 'de-DE')
              return groupCompare !== 0
                ? groupCompare
                : left.name.localeCompare(right.name, 'de-DE')
            }),
        )
      } catch (error) {
        console.error('Error loading fields', error)
        setErrorMessage('Die Anlagen konnten nicht geladen werden.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchFields()
  }, [])

  const selectedFieldIds = useMemo(() => new Set(parseSelectedFieldIds(value)), [value])

  const totalCount = fields.length
  const selectedCount = selectedFieldIds.size
  const allSelected = totalCount > 0 && selectedCount === totalCount

  const toggleField = (fieldId: number) => {
    const nextSelection = new Set(selectedFieldIds)
    if (nextSelection.has(fieldId)) {
      nextSelection.delete(fieldId)
    } else {
      nextSelection.add(fieldId)
    }
    onChange(serializeSelectedFieldIds([...nextSelection]))
  }

  const toggleAll = () => {
    if (allSelected) {
      onChange('[]')
      return
    }
    onChange(serializeSelectedFieldIds(fields.map((field) => field.id)))
  }

  if (isLoading) {
    return (
      <div className="mt-2 border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        Lade Anlagen...
      </div>
    )
  }

  if (errorMessage) {
    return (
      <div className="mt-2 border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
        {errorMessage}
      </div>
    )
  }

  return (
    <div className="mt-2 border border-slate-200 bg-white">
      <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-4 py-3">
        <div>
          <div className="text-sm font-medium text-slate-900">Anlagenauswahl</div>
          <div className="text-xs text-slate-500">
            {selectedCount} von {totalCount} Anlagen ausgewaehlt
          </div>
        </div>
        <button
          type="button"
          onClick={toggleAll}
          disabled={disabled || totalCount === 0}
          className="border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
        >
          {allSelected ? 'Alle abwaehlen' : 'Alle auswaehlen'}
        </button>
      </div>

      <div className="max-h-80 overflow-y-auto">
        {fields.map((field) => (
          <label
            key={field.id}
            className="flex cursor-pointer items-start gap-3 border-b border-slate-100 px-4 py-3 transition last:border-b-0 hover:bg-slate-50"
          >
            <input
              type="checkbox"
              checked={selectedFieldIds.has(field.id)}
              disabled={disabled}
              onChange={() => toggleField(field.id)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
            />
            <div className="min-w-0">
              <div className="text-sm font-medium text-slate-900">{field.name}</div>
              <div className="text-xs text-slate-500">
                {field.group} | {field.reference_station}
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}
