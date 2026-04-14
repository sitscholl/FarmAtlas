import { useEffect, useMemo, useRef, useState } from 'react'
import { FiChevronDown, FiChevronRight } from 'react-icons/fi'

import api from '../api'
import type { GroupedFieldNode, GroupedFieldResponse, GroupedFieldSection } from '../types/groupedFields'

type GroupedFieldSelectorProps = {
  value: string
  onChange: (nextValue: string) => void
  disabled?: boolean
}

type CheckboxRowProps = {
  checked: boolean
  indeterminate?: boolean
  disabled?: boolean
  label: string
  meta?: string
  depth?: number
  expanded?: boolean
  onToggle: () => void
  onExpand?: () => void
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

function CheckboxRow({
  checked,
  indeterminate = false,
  disabled,
  label,
  meta,
  depth = 0,
  expanded,
  onToggle,
  onExpand,
}: CheckboxRowProps) {
  const checkboxRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = indeterminate
    }
  }, [indeterminate])

  return (
    <div
      className="flex items-center gap-3 rounded-2xl px-3 py-2 transition hover:bg-slate-50"
      style={{ paddingLeft: `${0.75 + depth * 1.25}rem` }}
    >
      <input
        ref={checkboxRef}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={onToggle}
        className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
      />
      <button
        type="button"
        onClick={onExpand ?? onToggle}
        disabled={disabled}
        className="min-w-0 flex-1 text-left disabled:cursor-not-allowed"
      >
        <div className="truncate text-sm font-medium text-slate-900">{label}</div>
        {meta ? <div className="text-xs text-slate-500">{meta}</div> : null}
      </button>
      {onExpand ? (
        <button
          type="button"
          onClick={onExpand}
          disabled={disabled}
          className="rounded-full p-1 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 disabled:cursor-not-allowed"
          aria-label={expanded ? 'Collapse group' : 'Expand group'}
        >
          {expanded ? <FiChevronDown className="h-4 w-4" /> : <FiChevronRight className="h-4 w-4" />}
        </button>
      ) : null}
    </div>
  )
}

function getSectionLabel(section: GroupedFieldSection) {
  return section.section?.trim() ? section.section : 'Ohne Abschnitt'
}

export default function GroupedFieldSelector({
  value,
  onChange,
  disabled = false,
}: GroupedFieldSelectorProps) {
  const [groupedFields, setGroupedFields] = useState<GroupedFieldNode[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [expandedFieldNames, setExpandedFieldNames] = useState<Record<string, boolean>>({})
  const [expandedVarietyKeys, setExpandedVarietyKeys] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const fetchGroupedFields = async () => {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await api.get<GroupedFieldResponse>('/fields/grouped')
        setGroupedFields(response.data.fields)
        setExpandedFieldNames(
          Object.fromEntries(response.data.fields.map((field) => [field.name, false])),
        )
      } catch (error) {
        console.error('Error loading grouped fields', error)
        setErrorMessage('Die gruppierten Anlagen konnten nicht geladen werden.')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchGroupedFields()
  }, [])

  const selectedFieldIds = useMemo(() => new Set(parseSelectedFieldIds(value)), [value])
  const selectedCount = selectedFieldIds.size
  const totalCount = useMemo(
    () => groupedFields.reduce((sum, field) => sum + field.field_ids.length, 0),
    [groupedFields],
  )

  const updateSelection = (fieldIds: number[], checked: boolean) => {
    const nextSelection = new Set(selectedFieldIds)

    for (const fieldId of fieldIds) {
      if (checked) {
        nextSelection.add(fieldId)
      } else {
        nextSelection.delete(fieldId)
      }
    }

    onChange(serializeSelectedFieldIds([...nextSelection]))
  }

  const getSelectionState = (fieldIds: number[]) => {
    const selectedInGroup = fieldIds.filter((fieldId) => selectedFieldIds.has(fieldId)).length

    return {
      checked: selectedInGroup === fieldIds.length && fieldIds.length > 0,
      indeterminate: selectedInGroup > 0 && selectedInGroup < fieldIds.length,
      selectedCount: selectedInGroup,
      totalCount: fieldIds.length,
    }
  }

  const toggleFieldExpansion = (fieldName: string) => {
    setExpandedFieldNames((currentState) => ({
      ...currentState,
      [fieldName]: !currentState[fieldName],
    }))
  }

  const toggleVarietyExpansion = (fieldName: string, varietyName: string) => {
    const key = `${fieldName}::${varietyName}`
    setExpandedVarietyKeys((currentState) => ({
      ...currentState,
      [key]: !currentState[key],
    }))
  }

  if (isLoading) {
    return (
      <div className="mt-2 rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        Lade gruppierte Anlagen...
      </div>
    )
  }

  if (errorMessage) {
    return (
      <div className="mt-2 rounded-[1.5rem] border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
        {errorMessage}
      </div>
    )
  }

  return (
    <div className="mt-2 rounded-[1.5rem] border border-slate-200 bg-white">
      <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-4 py-3">
        <div>
          <div className="text-sm font-medium text-slate-900">Anlagenauswahl</div>
          <div className="text-xs text-slate-500">
            {selectedCount} von {totalCount} Eintraegen ausgewaehlt
          </div>
        </div>
      </div>

      <div className="max-h-80 overflow-y-auto py-2">
        {groupedFields.map((field) => {
          const fieldSelection = getSelectionState(field.field_ids)
          const isFieldExpanded = expandedFieldNames[field.name] ?? false

          return (
            <div key={field.name} className="px-2">
              <CheckboxRow
                checked={fieldSelection.checked}
                indeterminate={fieldSelection.indeterminate}
                disabled={disabled}
                label={field.name}
                meta={`${fieldSelection.selectedCount} / ${fieldSelection.totalCount}`}
                expanded={isFieldExpanded}
                onToggle={() => updateSelection(field.field_ids, !fieldSelection.checked)}
                onExpand={() => toggleFieldExpansion(field.name)}
              />

              {isFieldExpanded
                ? field.varieties.map((variety) => {
                    const varietySelection = getSelectionState(variety.field_ids)
                    const varietyKey = `${field.name}::${variety.variety}`
                    const isVarietyExpanded = expandedVarietyKeys[varietyKey] ?? false

                    return (
                      <div key={varietyKey}>
                        <CheckboxRow
                          checked={varietySelection.checked}
                          indeterminate={varietySelection.indeterminate}
                          disabled={disabled}
                          label={variety.variety}
                          meta={`${varietySelection.selectedCount} / ${varietySelection.totalCount}`}
                          depth={1}
                          expanded={isVarietyExpanded}
                          onToggle={() => updateSelection(variety.field_ids, !varietySelection.checked)}
                          onExpand={() => toggleVarietyExpansion(field.name, variety.variety)}
                        />

                        {isVarietyExpanded
                          ? variety.sections.map((section) => {
                              const sectionFieldIds = [section.field.id]
                              const sectionSelection = getSelectionState(sectionFieldIds)
                              const sectionMeta = `${section.field.planting_year}${
                                section.field.active === false ? ' | inaktiv' : ''
                              }`

                              return (
                                <CheckboxRow
                                  key={section.field.id}
                                  checked={sectionSelection.checked}
                                  disabled={disabled}
                                  label={getSectionLabel(section)}
                                  meta={sectionMeta}
                                  depth={2}
                                  onToggle={() => updateSelection(sectionFieldIds, !sectionSelection.checked)}
                                />
                              )
                            })
                          : null}
                      </div>
                    )
                  })
                : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
