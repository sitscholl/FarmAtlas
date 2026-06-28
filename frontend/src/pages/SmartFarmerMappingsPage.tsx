import { useCallback, useEffect, useMemo, useState } from 'react'
import { LuLink2, LuRefreshCw, LuTrash2 } from 'react-icons/lu'

import api from '../api'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import { getApiErrorMessage } from '../lib/apiErrors'
import {
  type FieldDetailRead,
  type TreatmentSectionAliasRead,
} from '../types/generated/api'
import {
  buildScopeOptions,
  CURRENT_SEASON_YEAR,
  fetchFieldDetails,
  SMARTFARMER_SOURCE,
} from './cropProtectionShared'

export default function SmartFarmerMappingsPage() {
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [aliases, setAliases] = useState<TreatmentSectionAliasRead[]>([])
  const [unresolvedNames, setUnresolvedNames] = useState<string[]>([])
  const [aliasSelections, setAliasSelections] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isAliasSubmitting, setIsAliasSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [aliasMessage, setAliasMessage] = useState<string | null>(null)
  const [aliasErrorMessage, setAliasErrorMessage] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true)
      const [
        fieldDetailResults,
        unresolvedResponse,
        aliasesResponse,
      ] = await Promise.all([
        fetchFieldDetails(),
        api.get<string[]>('/treatments/unresolved-sections', {
          params: { season_year: CURRENT_SEASON_YEAR },
        }),
        api.get<TreatmentSectionAliasRead[]>('/treatments/section-aliases'),
      ])

      setFieldDetails(fieldDetailResults)
      setUnresolvedNames(unresolvedResponse.data)
      setAliases(aliasesResponse.data)
      setErrorMessage(null)
    } catch (error) {
      console.error('Error loading SmartFarmer mappings', error)
      setErrorMessage('SmartFarmer Zuordnungen konnten nicht geladen werden.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  useEffect(() => {
    const handleDataChanged = () => {
      void fetchData()
    }

    window.addEventListener(DATA_CHANGED_EVENT, handleDataChanged)
    return () => window.removeEventListener(DATA_CHANGED_EVENT, handleDataChanged)
  }, [fetchData])

  const scopeOptions = useMemo(() => buildScopeOptions(fieldDetails), [fieldDetails])
  const sectionScopeOptions = useMemo(
    () => scopeOptions.filter((option) => option.type === 'section'),
    [scopeOptions],
  )
  const sectionLabelsById = useMemo(
    () => Object.fromEntries(sectionScopeOptions.map((option) => [option.id, option.label])),
    [sectionScopeOptions],
  )

  const handleSaveAlias = async (externalSectionName: string) => {
    const sectionId = Number(aliasSelections[externalSectionName])
    if (!Number.isFinite(sectionId) || sectionId <= 0) {
      setAliasErrorMessage('Bitte zuerst einen Farm Atlas Abschnitt auswaehlen.')
      return
    }

    setIsAliasSubmitting(true)
    setAliasMessage(null)
    setAliasErrorMessage(null)
    try {
      await api.post('/treatments/section-aliases', {
        source: SMARTFARMER_SOURCE,
        external_section_name: externalSectionName,
        section_id: sectionId,
      })
      setAliasSelections((currentSelections) => {
        const nextSelections = { ...currentSelections }
        delete nextSelections[externalSectionName]
        return nextSelections
      })
      setAliasMessage('SmartFarmer Zuordnung gespeichert.')
      notifyDataChanged()
      await fetchData()
    } catch (error) {
      console.error('Error saving treatment section alias', error)
      setAliasErrorMessage(getApiErrorMessage(error, 'Die SmartFarmer Zuordnung konnte nicht gespeichert werden.'))
    } finally {
      setIsAliasSubmitting(false)
    }
  }

  const handleDeleteAlias = async (alias: TreatmentSectionAliasRead) => {
    setIsAliasSubmitting(true)
    setAliasMessage(null)
    setAliasErrorMessage(null)
    try {
      await api.delete(`/treatments/section-aliases/${alias.id}`)
      setAliasMessage('SmartFarmer Zuordnung geloescht.')
      notifyDataChanged()
      await fetchData()
    } catch (error) {
      console.error('Error deleting treatment section alias', error)
      setAliasErrorMessage(getApiErrorMessage(error, 'Die SmartFarmer Zuordnung konnte nicht geloescht werden.'))
    } finally {
      setIsAliasSubmitting(false)
    }
  }

  return (
    <section className="w-full max-w-7xl">
      <div className="px-2 py-4 sm:px-6 sm:py-6 lg:p-8">
        <div className="flex flex-col gap-4 border-b border-black pb-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Pflanzenschutz
            </p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 sm:text-4xl">
              SmartFarmer Zuordnungen
            </h1>
          </div>
          <button
            type="button"
            onClick={() => void fetchData()}
            className="inline-flex items-center gap-2 border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <LuRefreshCw className="h-4 w-4" />
            Aktualisieren
          </button>
        </div>

        {errorMessage ? (
          <div className="mt-5 border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <section className="mt-8">
          <div className="mb-3 flex items-center gap-2">
            <LuLink2 className="h-5 w-5 text-slate-500" />
            <h2 className="text-xl font-semibold text-slate-900">SmartFarmer - FarmAtlas Zuordnungen</h2>
          </div>
          {isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
              Lade SmartFarmer Zuordnungen...
            </div>
          ) : (
            <div className="min-w-0 border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <h3 className="text-lg font-semibold text-slate-900">SmartFarmer Zuordnung</h3>
                <span className="border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-600">
                  {unresolvedNames.length} offen
                </span>
              </div>
              {aliasErrorMessage ? (
                <div className="mt-3 border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {aliasErrorMessage}
                </div>
              ) : null}
              {aliasMessage ? (
                <div className="mt-3 border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  {aliasMessage}
                </div>
              ) : null}

              <div className="mt-4">
                <div className="text-sm font-semibold text-slate-900">Offene Anlagen</div>
                <div className="mt-2 grid gap-2">
                  {unresolvedNames.length === 0 ? (
                    <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                      Keine offenen SmartFarmer Anlagen.
                    </div>
                  ) : (
                    unresolvedNames.map((externalName) => (
                      <div key={externalName} className="border border-slate-200 bg-slate-50 p-3">
                        <div className="break-words text-sm font-semibold text-slate-900">{externalName}</div>
                        <div className="mt-2 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                          <select
                            value={aliasSelections[externalName] ?? ''}
                            onChange={(event) =>
                              setAliasSelections((currentSelections) => ({
                                ...currentSelections,
                                [externalName]: event.target.value,
                              }))
                            }
                            className="w-full border border-slate-200 bg-white px-3 py-2 text-sm"
                          >
                            <option value="">Abschnitt auswaehlen</option>
                            {sectionScopeOptions.map((option) => (
                              <option key={option.key} value={option.id}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            onClick={() => void handleSaveAlias(externalName)}
                            disabled={isAliasSubmitting}
                            className="inline-flex items-center justify-center border border-sky-700 bg-sky-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                          >
                            Zuordnen
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="mt-5">
                <div className="text-sm font-semibold text-slate-900">Bestehende Zuordnungen</div>
                <div className="mt-2 grid gap-2">
                  {aliases.length === 0 ? (
                    <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                      Keine SmartFarmer Zuordnungen vorhanden.
                    </div>
                  ) : (
                    aliases.map((alias) => (
                      <div
                        key={alias.id}
                        className="grid gap-2 border border-slate-200 bg-white p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
                      >
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-slate-900">
                            {alias.external_section_name}
                          </div>
                          <div className="mt-1 truncate text-sm text-slate-500">
                            {sectionLabelsById[alias.section_id] ?? `Abschnitt ${alias.section_id}`}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => void handleDeleteAlias(alias)}
                          disabled={isAliasSubmitting}
                          className="inline-flex items-center justify-center gap-1 border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 disabled:opacity-60"
                        >
                          <LuTrash2 className="h-4 w-4" />
                          Loeschen
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </section>
  )
}
