import { useEffect, useMemo, useRef, useState } from 'react'

import api from '../api'
import type { FieldDetailRead, FieldRead, PlantingDetailRead, SectionRead } from '../types/generated/api'

type SelectionMode = 'fields' | 'sections'

type GroupedFieldSelectorProps = {
  value: string
  onChange: (nextValue: string) => void
  disabled?: boolean
  selectionMode?: SelectionMode
}

type IndeterminateCheckboxProps = {
  checked: boolean
  indeterminate?: boolean
  disabled?: boolean
  onChange: () => void
  className?: string
}

function IndeterminateCheckbox({
  checked,
  indeterminate = false,
  disabled = false,
  onChange,
  className,
}: IndeterminateCheckboxProps) {
  const ref = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (ref.current !== null) {
      ref.current.indeterminate = indeterminate
    }
  }, [indeterminate])

  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      disabled={disabled}
      onChange={onChange}
      className={className}
    />
  )
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

function serializeSelectedIds(ids: number[]) {
  return JSON.stringify([...new Set(ids)].sort((left, right) => left - right))
}

function getFieldSectionIds(fieldDetail: FieldDetailRead) {
  return fieldDetail.plantings.flatMap((planting) => planting.sections.map((section) => section.id))
}

function getPlantingSectionIds(planting: PlantingDetailRead) {
  return planting.sections.map((section) => section.id)
}

function sortFields(fields: FieldRead[]) {
  return fields
    .slice()
    .sort((left, right) => {
      const groupCompare = left.group.localeCompare(right.group, 'de-DE')
      return groupCompare !== 0
        ? groupCompare
        : left.name.localeCompare(right.name, 'de-DE')
    })
}

function sortFieldDetails(fieldDetails: FieldDetailRead[]) {
  return fieldDetails
    .slice()
    .sort((left, right) => {
      const groupCompare = left.field.group.localeCompare(right.field.group, 'de-DE')
      return groupCompare !== 0
        ? groupCompare
        : left.field.name.localeCompare(right.field.name, 'de-DE')
    })
}

function SelectionCount({
  selectedCount,
  totalCount,
  noun,
}: {
  selectedCount: number
  totalCount: number
  noun: string
}) {
  return (
    <div className="text-xs text-slate-500">
      {selectedCount} von {totalCount} {noun} ausgewaehlt
    </div>
  )
}

export default function GroupedFieldSelector({
  value,
  onChange,
  disabled = false,
  selectionMode = 'fields',
}: GroupedFieldSelectorProps) {
  const [fields, setFields] = useState<FieldRead[]>([])
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [expandedFields, setExpandedFields] = useState<Set<number>>(new Set())
  const [expandedPlantings, setExpandedPlantings] = useState<Set<number>>(new Set())
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchFields = async () => {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        if (selectionMode === 'fields') {
          const response = await api.get<FieldRead[]>('/fields')
          setFields(sortFields(response.data))
          setFieldDetails([])
          return
        }

        const fieldsResponse = await api.get<FieldRead[]>('/fields')
        const details = await Promise.all(
          fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
        )
        setFields([])
        setFieldDetails(sortFieldDetails(details.map((response) => response.data)))
      } catch (error) {
        console.error('Error loading fields', error)
        setErrorMessage(
          selectionMode === 'fields'
            ? 'Die Anlagen konnten nicht geladen werden.'
            : 'Die Abschnitte konnten nicht geladen werden.',
        )
      } finally {
        setIsLoading(false)
      }
    }

    void fetchFields()
  }, [selectionMode])

  const selectedIds = useMemo(() => new Set(parseSelectedIds(value)), [value])

  const totalCount = useMemo(
    () =>
      selectionMode === 'fields'
        ? fields.length
        : fieldDetails.reduce((count, fieldDetail) => count + getFieldSectionIds(fieldDetail).length, 0),
    [fieldDetails, fields.length, selectionMode],
  )
  const selectedCount = selectedIds.size
  const allSelected = totalCount > 0 && selectedCount === totalCount

  const updateSelection = (nextSelection: Set<number>) => {
    onChange(serializeSelectedIds([...nextSelection]))
  }

  const toggleIds = (ids: number[]) => {
    if (ids.length === 0) {
      return
    }

    const nextSelection = new Set(selectedIds)
    const allIdsSelected = ids.every((id) => nextSelection.has(id))
    ids.forEach((id) => {
      if (allIdsSelected) {
        nextSelection.delete(id)
      } else {
        nextSelection.add(id)
      }
    })
    updateSelection(nextSelection)
  }

  const toggleField = (fieldId: number) => {
    toggleIds([fieldId])
  }

  const toggleAll = () => {
    if (allSelected) {
      onChange('[]')
      return
    }

    if (selectionMode === 'fields') {
      onChange(serializeSelectedIds(fields.map((field) => field.id)))
      return
    }

    onChange(
      serializeSelectedIds(
        fieldDetails.flatMap((fieldDetail) => getFieldSectionIds(fieldDetail)),
      ),
    )
  }

  const toggleFieldExpansion = (fieldId: number) => {
    setExpandedFields((current) => {
      const next = new Set(current)
      if (next.has(fieldId)) {
        next.delete(fieldId)
      } else {
        next.add(fieldId)
      }
      return next
    })
  }

  const togglePlantingExpansion = (plantingId: number) => {
    setExpandedPlantings((current) => {
      const next = new Set(current)
      if (next.has(plantingId)) {
        next.delete(plantingId)
      } else {
        next.add(plantingId)
      }
      return next
    })
  }

  if (isLoading) {
    return (
      <div className="mt-2 border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        {selectionMode === 'fields' ? 'Lade Anlagen...' : 'Lade Abschnitte...'}
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

  const checkboxClasses = 'mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400'

  return (
    <div className="mt-2 border border-slate-200 bg-white">
      <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-4 py-3">
        <div>
          <div className="text-sm font-medium text-slate-900">
            {selectionMode === 'fields' ? 'Anlagenauswahl' : 'Abschnittsauswahl'}
          </div>
          <SelectionCount
            selectedCount={selectedCount}
            totalCount={totalCount}
            noun={selectionMode === 'fields' ? 'Anlagen' : 'Abschnitten'}
          />
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
        {selectionMode === 'fields' ? (
          fields.map((field) => (
            <label
              key={field.id}
              className="flex cursor-pointer items-start gap-3 border-b border-slate-100 px-4 py-3 transition last:border-b-0 hover:bg-slate-50"
            >
              <IndeterminateCheckbox
                checked={selectedIds.has(field.id)}
                disabled={disabled}
                onChange={() => toggleField(field.id)}
                className={checkboxClasses}
              />
              <div className="min-w-0">
                <div className="text-sm font-medium text-slate-900">{field.name}</div>
                <div className="text-xs text-slate-500">
                  {field.group} | {field.reference_station}
                </div>
              </div>
            </label>
          ))
        ) : (
          fieldDetails.map((fieldDetail) => {
            const fieldSectionIds = getFieldSectionIds(fieldDetail)
            const selectedFieldSectionCount = fieldSectionIds.filter((id) => selectedIds.has(id)).length
            const isExpanded = expandedFields.has(fieldDetail.field.id)

            return (
              <div key={fieldDetail.field.id} className="border-b border-slate-100 last:border-b-0">
                <div className="flex items-start gap-2 px-4 py-3 transition hover:bg-slate-50">
                  <button
                    type="button"
                    onClick={() => toggleFieldExpansion(fieldDetail.field.id)}
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border border-slate-200 bg-white text-xs font-semibold text-slate-600 transition hover:bg-slate-100"
                    aria-label={`${fieldDetail.field.name} ${isExpanded ? 'einklappen' : 'ausklappen'}`}
                  >
                    {isExpanded ? '-' : '+'}
                  </button>
                  <IndeterminateCheckbox
                    checked={fieldSectionIds.length > 0 && selectedFieldSectionCount === fieldSectionIds.length}
                    indeterminate={selectedFieldSectionCount > 0 && selectedFieldSectionCount < fieldSectionIds.length}
                    disabled={disabled || fieldSectionIds.length === 0}
                    onChange={() => toggleIds(fieldSectionIds)}
                    className={checkboxClasses}
                  />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-900">{fieldDetail.field.name}</div>
                    <div className="text-xs text-slate-500">
                      {fieldDetail.field.group} | {fieldDetail.field.reference_station} | {fieldSectionIds.length} Abschnitte
                    </div>
                  </div>
                </div>

                {isExpanded ? (
                  <div className="border-t border-slate-100 bg-slate-50/60">
                    {fieldDetail.plantings.length === 0 ? (
                      <div className="px-12 py-3 text-xs text-slate-500">
                        Keine Pflanzungen vorhanden.
                      </div>
                    ) : (
                      fieldDetail.plantings.map((planting) => {
                        const plantingSectionIds = getPlantingSectionIds(planting)
                        const selectedPlantingSectionCount = plantingSectionIds.filter((id) => selectedIds.has(id)).length
                        const isPlantingExpanded = expandedPlantings.has(planting.id)

                        return (
                          <div key={planting.id} className="border-t border-slate-100 first:border-t-0">
                            <div className="flex items-start gap-2 py-3 pl-10 pr-4 transition hover:bg-slate-100/70">
                              <button
                                type="button"
                                onClick={() => togglePlantingExpansion(planting.id)}
                                className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border border-slate-200 bg-white text-xs font-semibold text-slate-600 transition hover:bg-slate-100"
                                aria-label={`${planting.variety} ${isPlantingExpanded ? 'einklappen' : 'ausklappen'}`}
                              >
                                {isPlantingExpanded ? '-' : '+'}
                              </button>
                              <IndeterminateCheckbox
                                checked={plantingSectionIds.length > 0 && selectedPlantingSectionCount === plantingSectionIds.length}
                                indeterminate={selectedPlantingSectionCount > 0 && selectedPlantingSectionCount < plantingSectionIds.length}
                                disabled={disabled || plantingSectionIds.length === 0}
                                onChange={() => toggleIds(plantingSectionIds)}
                                className={checkboxClasses}
                              />
                              <div className="min-w-0">
                                <div className="text-sm font-medium text-slate-800">{planting.variety}</div>
                                <div className="text-xs text-slate-500">
                                  {planting.sections.length} Abschnitte | {planting.active ? 'Aktiv' : 'Inaktiv'}
                                </div>
                              </div>
                            </div>

                            {isPlantingExpanded ? (
                              <div className="bg-white">
                                {planting.sections.length === 0 ? (
                                  <div className="py-3 pl-20 pr-4 text-xs text-slate-500">
                                    Keine Abschnitte vorhanden.
                                  </div>
                                ) : (
                                  planting.sections.map((section: SectionRead) => (
                                    <label
                                      key={section.id}
                                      className="flex cursor-pointer items-start gap-3 border-t border-slate-100 py-3 pl-20 pr-4 transition hover:bg-slate-50"
                                    >
                                      <IndeterminateCheckbox
                                        checked={selectedIds.has(section.id)}
                                        disabled={disabled}
                                        onChange={() => toggleIds([section.id])}
                                        className={checkboxClasses}
                                      />
                                      <div className="min-w-0">
                                        <div className="text-sm font-medium text-slate-800">{section.name}</div>
                                        <div className="text-xs text-slate-500">
                                          Pflanzjahr {section.planting_year} | {section.active ? 'Aktiv' : 'Inaktiv'}
                                        </div>
                                      </div>
                                    </label>
                                  ))
                                )}
                              </div>
                            ) : null}
                          </div>
                        )
                      })
                    )}
                  </div>
                ) : null}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
