import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'
import { FiChevronDown } from 'react-icons/fi'

import api from '../api'
import type { FieldDetailRead, FieldRead, PlantingDetailRead, SectionRead } from '../types/generated/api'

export type FruitCountScope =
  | { type: 'field'; field_id: number }
  | { type: 'planting'; field_id: number; planting_id: number }
  | { type: 'section'; field_id: number; planting_id: number; section_id: number }

type FruitCountScopePickerProps = {
  value: FruitCountScope | null
  onChange: (nextScope: FruitCountScope) => void
  disabled?: boolean
  fieldDetails?: FieldDetailRead[]
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

function isSameScope(left: FruitCountScope | null, right: FruitCountScope) {
  if (left === null || left.type !== right.type) {
    return false
  }

  if (right.type === 'field') {
    return left.field_id === right.field_id
  }
  if (right.type === 'planting') {
    return left.type === 'planting' && left.planting_id === right.planting_id
  }
  return left.type === 'section' && left.section_id === right.section_id
}

function getScopeLabel(
  scope: FruitCountScope | null,
  fieldDetails: FieldDetailRead[],
) {
  if (scope === null) {
    return 'Keine Auswahl'
  }

  const fieldDetail = fieldDetails.find((detail) => detail.field.id === scope.field_id)
  if (fieldDetail === undefined) {
    return scope.type
  }

  if (scope.type === 'field') {
    return `Anlage: ${fieldDetail.field.name}`
  }

  const planting = fieldDetail.plantings.find((candidate) => candidate.id === scope.planting_id)
  if (scope.type === 'planting') {
    return `Pflanzung: ${fieldDetail.field.name} | ${planting?.variety ?? scope.planting_id}`
  }

  const section = planting?.sections.find((candidate) => candidate.id === scope.section_id)
  return `Abschnitt: ${fieldDetail.field.name} | ${planting?.variety ?? scope.planting_id} | ${section?.name ?? scope.section_id}`
}

function scopeLevelLabel(scope: FruitCountScope | null) {
  if (scope?.type === 'field') {
    return 'Anlage'
  }
  if (scope?.type === 'planting') {
    return 'Pflanzung'
  }
  if (scope?.type === 'section') {
    return 'Abschnitt'
  }
  return 'Nicht gesetzt'
}

function ScopeRadio({
  checked,
  disabled,
}: {
  checked: boolean
  disabled?: boolean
}) {
  return (
    <span
      aria-hidden="true"
      className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
        checked ? 'border-sky-600' : 'border-slate-300'
      } ${disabled ? 'opacity-40' : ''}`}
    >
      <span className={`h-2 w-2 rounded-full bg-sky-600 ${checked ? 'block' : 'hidden'}`} />
    </span>
  )
}

export default function FruitCountScopePicker({
  value,
  onChange,
  disabled = false,
  fieldDetails: providedFieldDetails,
}: FruitCountScopePickerProps) {
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>(providedFieldDetails ?? [])
  const [expandedFields, setExpandedFields] = useState<Set<number>>(new Set())
  const [expandedPlantings, setExpandedPlantings] = useState<Set<number>>(new Set())
  const [isLoading, setIsLoading] = useState(providedFieldDetails === undefined)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (providedFieldDetails !== undefined) {
      setFieldDetails(sortFieldDetails(providedFieldDetails))
      setIsLoading(false)
    }
  }, [providedFieldDetails])

  useEffect(() => {
    if (providedFieldDetails !== undefined) {
      return
    }

    const fetchFields = async () => {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const fieldsResponse = await api.get<FieldRead[]>('/fields')
        const detailResponses = await Promise.all(
          fieldsResponse.data.map((field) => api.get<FieldDetailRead>(`/fields/${field.id}`)),
        )
        setFieldDetails(sortFieldDetails(detailResponses.map((response) => response.data)))
      } catch (error) {
        console.error('Error loading fields for fruit count scope picker', error)
        setErrorMessage('Die Anlagen konnten nicht geladen werden.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchFields()
  }, [providedFieldDetails])

  useEffect(() => {
    if (value === null) {
      return
    }

    setExpandedFields((current) => new Set(current).add(value.field_id))
    if (value.type === 'planting' || value.type === 'section') {
      setExpandedPlantings((current) => new Set(current).add(value.planting_id))
    }
  }, [value])

  const totalFields = fieldDetails.length
  const totalPlantings = useMemo(
    () => fieldDetails.reduce((sum, fieldDetail) => sum + fieldDetail.plantings.length, 0),
    [fieldDetails],
  )
  const totalSections = useMemo(
    () =>
      fieldDetails.reduce(
        (sum, fieldDetail) =>
          sum + fieldDetail.plantings.reduce((plantingSum, planting) => plantingSum + planting.sections.length, 0),
        0,
      ),
    [fieldDetails],
  )

  const selectScope = (scope: FruitCountScope) => {
    if (disabled) {
      return
    }
    onChange(scope)
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

  const handleSelectableRowKeyDown = (
    event: KeyboardEvent<HTMLDivElement>,
    onSelect: () => void,
  ) => {
    if (event.target !== event.currentTarget) {
      return
    }

    if (event.key !== 'Enter' && event.key !== ' ') {
      return
    }

    event.preventDefault()
    onSelect()
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

  const chevronClasses = (isExpanded: boolean) =>
    `h-5 w-5 shrink-0 text-slate-700 transition-transform ${isExpanded ? 'rotate-180' : ''}`

  return (
    <div className="mt-2 border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div>
          <div className="text-sm font-medium text-slate-900">Anlage, Pflanzung oder Abschnitt</div>
          <div className="text-xs text-slate-500">
            {totalFields} Anlagen | {totalPlantings} Pflanzungen | {totalSections} Abschnitte
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Aufloesung
          </div>
          <div className="text-sm font-semibold text-slate-900">{scopeLevelLabel(value)}</div>
        </div>
      </div>

      <div className="border-b border-slate-100 bg-slate-50/70 px-4 py-2 text-xs text-slate-600">
        {getScopeLabel(value, fieldDetails)}
      </div>

      <div>
        {fieldDetails.map((fieldDetail) => {
          const fieldScope: FruitCountScope = { type: 'field', field_id: fieldDetail.field.id }
          const fieldIsExpanded = expandedFields.has(fieldDetail.field.id)
          const fieldSelected = isSameScope(value, fieldScope)

          return (
            <div key={fieldDetail.field.id} className="border-b border-slate-100 last:border-b-0">
              <div
                role="button"
                tabIndex={0}
                onClick={() => selectScope(fieldScope)}
                onKeyDown={(event) => handleSelectableRowKeyDown(event, () => selectScope(fieldScope))}
                className={`flex w-full cursor-pointer items-center gap-3 px-4 py-1.5 text-left transition hover:bg-slate-50 ${
                  fieldSelected ? 'bg-sky-50/70' : ''
                }`}
              >
                <ScopeRadio checked={fieldSelected} disabled={disabled} />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-slate-900">{fieldDetail.field.name}</div>
                  <div className="text-xs text-slate-500">{fieldDetail.field.group}</div>
                </div>
                <span className="shrink-0 text-sm font-medium tabular-nums text-slate-400">
                  {fieldDetail.plantings.length}
                </span>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    toggleFieldExpansion(fieldDetail.field.id)
                  }}
                  disabled={fieldDetail.plantings.length === 0}
                  className="shrink-0 p-1 text-slate-700 transition hover:text-slate-950 disabled:cursor-not-allowed disabled:text-slate-300"
                  aria-label={`${fieldDetail.field.name} ${fieldIsExpanded ? 'einklappen' : 'ausklappen'}`}
                  aria-expanded={fieldIsExpanded}
                >
                  <FiChevronDown className={chevronClasses(fieldIsExpanded)} aria-hidden="true" />
                </button>
              </div>

              {fieldIsExpanded ? (
                <div className="border-t border-slate-100 bg-slate-50/60">
                  {fieldDetail.plantings.length === 0 ? (
                    <div className="px-12 py-1 text-xs text-slate-500">
                      Keine Pflanzungen vorhanden.
                    </div>
                  ) : (
                    fieldDetail.plantings.map((planting: PlantingDetailRead) => {
                      const plantingScope: FruitCountScope = {
                        type: 'planting',
                        field_id: fieldDetail.field.id,
                        planting_id: planting.id,
                      }
                      const plantingIsExpanded = expandedPlantings.has(planting.id)
                      const plantingSelected = isSameScope(value, plantingScope)

                      return (
                        <div key={planting.id} className="border-t border-slate-100 first:border-t-0">
                          <div
                            role="button"
                            tabIndex={0}
                            onClick={() => selectScope(plantingScope)}
                            onKeyDown={(event) => handleSelectableRowKeyDown(event, () => selectScope(plantingScope))}
                            className={`flex w-full cursor-pointer items-center gap-3 py-1.5 pl-10 pr-4 text-left transition hover:bg-slate-100/70 ${
                              plantingSelected ? 'bg-sky-50/80' : ''
                            }`}
                          >
                            <ScopeRadio checked={plantingSelected} disabled={disabled} />
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-medium text-slate-800">{planting.variety}</div>
                            </div>
                            <span className="shrink-0 text-sm font-medium tabular-nums text-slate-400">
                              {planting.sections.length}
                            </span>
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation()
                                togglePlantingExpansion(planting.id)
                              }}
                              disabled={planting.sections.length === 0}
                              className="shrink-0 p-1 text-slate-700 transition hover:text-slate-950 disabled:cursor-not-allowed disabled:text-slate-300"
                              aria-label={`${planting.variety} ${plantingIsExpanded ? 'einklappen' : 'ausklappen'}`}
                              aria-expanded={plantingIsExpanded}
                            >
                              <FiChevronDown className={chevronClasses(plantingIsExpanded)} aria-hidden="true" />
                            </button>
                          </div>

                          {plantingIsExpanded ? (
                            <div className="bg-white">
                              {planting.sections.length === 0 ? (
                                <div className="py-1 pl-20 pr-4 text-xs text-slate-500">
                                  Keine Abschnitte vorhanden.
                                </div>
                              ) : (
                                planting.sections.map((section: SectionRead) => {
                                  const sectionScope: FruitCountScope = {
                                    type: 'section',
                                    field_id: fieldDetail.field.id,
                                    planting_id: planting.id,
                                    section_id: section.id,
                                  }
                                  const sectionSelected = isSameScope(value, sectionScope)

                                  return (
                                    <div
                                      key={section.id}
                                      role="button"
                                      tabIndex={0}
                                      onClick={() => selectScope(sectionScope)}
                                      onKeyDown={(event) => handleSelectableRowKeyDown(event, () => selectScope(sectionScope))}
                                      className={`flex cursor-pointer items-start gap-3 border-t border-slate-100 py-1.5 pl-20 pr-4 transition hover:bg-slate-50 ${
                                        sectionSelected ? 'bg-sky-50/70' : ''
                                      }`}
                                    >
                                      <ScopeRadio checked={sectionSelected} disabled={disabled} />
                                      <div className="min-w-0">
                                        <div className="text-sm font-medium text-slate-800">{section.name}</div>
                                      </div>
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
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
