import { useCallback, useEffect, useMemo, useState } from 'react'
import { LuListChecks, LuPencil, LuPlus, LuRefreshCw, LuTrash2 } from 'react-icons/lu'

import api from '../api'
import { DATA_CHANGED_EVENT, notifyDataChanged } from '../lib/dataEvents'
import {
  type CropProtectionRuleRead,
  type FieldDetailRead,
} from '../types/generated/api'
import {
  buildRuleForm,
  buildRulePayload,
  buildScopeOptions,
  cloneMetricInputs,
  emptyMetricInputs,
  emptyRuleForm,
  fetchFieldDetails,
  metricLabels,
  metricTypes,
  type MetricType,
  type RuleFormMetricState,
} from './cropProtectionShared'

export default function RegelnPage() {
  const [rules, setRules] = useState<CropProtectionRuleRead[]>([])
  const [fieldDetails, setFieldDetails] = useState<FieldDetailRead[]>([])
  const [productNames, setProductNames] = useState<string[]>([])
  const [form, setForm] = useState(emptyRuleForm)
  const [selectedScopeKeys, setSelectedScopeKeys] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true)
      const [
        rulesResponse,
        productsResponse,
        fieldDetailResults,
      ] = await Promise.all([
        api.get<CropProtectionRuleRead[]>('/crop-protection/rules'),
        api.get<string[]>('/treatments/products'),
        fetchFieldDetails(),
      ])

      setRules(rulesResponse.data)
      setProductNames(productsResponse.data)
      setFieldDetails(fieldDetailResults)
      setErrorMessage(null)
    } catch (error) {
      console.error('Error loading crop protection rules', error)
      setErrorMessage('Pflanzenschutzregeln konnten nicht geladen werden.')
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
  const scopeLabelsByKey = useMemo(
    () => Object.fromEntries(scopeOptions.map((option) => [option.key, option.label])),
    [scopeOptions],
  )

  const selectedScopeSet = useMemo(() => new Set(selectedScopeKeys), [selectedScopeKeys])
  const addedScopeKeySet = useMemo(
    () => new Set(form.scopes.map((scope) => `${scope.scope_type}-${scope.scope_id}`)),
    [form.scopes],
  )

  const handleSelectRule = (rule: CropProtectionRuleRead) => {
    setForm(buildRuleForm(rule))
    setSelectedScopeKeys([])
  }

  const handleNewRule = () => {
    setForm({
      ...emptyRuleForm,
      metricInputs: cloneMetricInputs(emptyMetricInputs),
    })
    setSelectedScopeKeys([])
  }

  const handleToggleScopeSelection = (scopeKey: string) => {
    setSelectedScopeKeys((currentKeys) =>
      currentKeys.includes(scopeKey)
        ? currentKeys.filter((key) => key !== scopeKey)
        : [...currentKeys, scopeKey],
    )
  }

  const handleSelectAllSections = () => {
    setSelectedScopeKeys(
      sectionScopeOptions
        .map((option) => option.key)
        .filter((key) => !addedScopeKeySet.has(key)),
    )
  }

  const handleAddSelectedScopes = () => {
    const selectedOptions = sectionScopeOptions.filter((option) => selectedScopeSet.has(option.key))
    if (selectedOptions.length === 0) {
      return
    }

    setForm((currentForm) => {
      const currentScopeKeys = new Set(currentForm.scopes.map((scope) => `${scope.scope_type}-${scope.scope_id}`))
      const nextScopes = selectedOptions
        .filter((option) => !currentScopeKeys.has(option.key))
        .map((option) => ({ scope_type: option.type, scope_id: option.id }))

      return {
        ...currentForm,
        scopes: [...currentForm.scopes, ...nextScopes],
      }
    })
    setSelectedScopeKeys([])
  }

  const handleSaveRule = async () => {
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      const payload = buildRulePayload(form)
      if (form.id === null) {
        await api.post('/crop-protection/rules', payload)
      } else {
        await api.put(`/crop-protection/rules/${form.id}`, payload)
      }
      notifyDataChanged()
      await fetchData()
      handleNewRule()
    } catch (error) {
      console.error('Error saving crop protection rule', error)
      setErrorMessage('Die Pflanzenschutzregel konnte nicht gespeichert werden.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteRule = async () => {
    if (form.id === null) {
      return
    }
    const confirmed = window.confirm(`Soll die Regel "${form.name}" wirklich geloescht werden?`)
    if (!confirmed) {
      return
    }
    setIsSubmitting(true)
    try {
      await api.delete(`/crop-protection/rules/${form.id}`)
      notifyDataChanged()
      await fetchData()
      handleNewRule()
    } catch (error) {
      console.error('Error deleting crop protection rule', error)
      setErrorMessage('Die Pflanzenschutzregel konnte nicht geloescht werden.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleMetricChange = (
    metricType: MetricType,
    updates: Partial<RuleFormMetricState>,
  ) => {
    setForm((currentForm) => ({
      ...currentForm,
      metricInputs: {
        ...currentForm.metricInputs,
        [metricType]: {
          ...currentForm.metricInputs[metricType],
          ...updates,
        },
      },
    }))
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
              Regeln
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

        <div className="mt-8 mb-3 flex items-center gap-2">
          <LuListChecks className="h-5 w-5 text-slate-500" />
          <h2 className="text-xl font-semibold text-slate-900">Pflanzenschutz Regeln</h2>
        </div>

        {isLoading ? (
          <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
            Lade Regeln...
          </div>
        ) : (
          <section className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="min-w-0 border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <h2 className="text-xl font-semibold text-slate-900">Bestehende Regeln</h2>
                <button
                  type="button"
                  onClick={handleNewRule}
                  className="inline-flex items-center gap-1 border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800"
                >
                  <LuPlus className="h-4 w-4" />
                  Neu
                </button>
              </div>
              <div className="mt-3 grid gap-2">
                {rules.length === 0 ? (
                  <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
                    Keine Regeln vorhanden.
                  </div>
                ) : (
                  rules.map((rule) => (
                    <button
                      key={rule.id}
                      type="button"
                      onClick={() => handleSelectRule(rule)}
                      className={`border px-4 py-3 text-left transition hover:bg-slate-50 ${
                        form.id === rule.id ? 'border-slate-900 bg-slate-50' : 'border-slate-200 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-slate-900">{rule.name}</div>
                          <div className="mt-1 text-sm text-slate-500">
                            {rule.products.length} Produkte | {rule.scopes.length} Bereiche
                          </div>
                        </div>
                        <span className={`text-xs font-semibold ${rule.enabled ? 'text-emerald-700' : 'text-slate-400'}`}>
                          {rule.enabled ? 'Aktiv' : 'Inaktiv'}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>

            <div className="min-w-0 border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <h2 className="text-xl font-semibold text-slate-900">
                  {form.id === null ? 'Neue Regel' : 'Regel bearbeiten'}
                </h2>
                {form.id !== null ? (
                  <button
                    type="button"
                    onClick={handleDeleteRule}
                    disabled={isSubmitting}
                    className="inline-flex items-center gap-1 border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 disabled:opacity-60"
                  >
                    <LuTrash2 className="h-4 w-4" />
                    Loeschen
                  </button>
                ) : null}
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Name</span>
                  <input
                    value={form.name}
                    onChange={(event) => setForm((currentForm) => ({ ...currentForm, name: event.target.value }))}
                    className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Saisonstart</span>
                  <input
                    type="date"
                    value={form.seasonStart}
                    onChange={(event) => setForm((currentForm) => ({ ...currentForm, seasonStart: event.target.value }))}
                    className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Saisonende</span>
                  <input
                    type="date"
                    value={form.seasonEnd}
                    onChange={(event) => setForm((currentForm) => ({ ...currentForm, seasonEnd: event.target.value }))}
                    className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                  />
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={form.enabled}
                    onChange={(event) => setForm((currentForm) => ({ ...currentForm, enabled: event.target.checked }))}
                    className="h-5 w-5"
                  />
                  <span className="text-sm font-medium text-slate-700">Aktiv</span>
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Logik</span>
                  <select
                    value={form.logic}
                    onChange={(event) => setForm((currentForm) => ({ ...currentForm, logic: event.target.value as 'any' | 'all' }))}
                    className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                  >
                    <option value="any">Eine Metrik reicht</option>
                    <option value="all">Alle Metriken</option>
                  </select>
                </label>
              </div>

              <label className="mt-4 block">
                <span className="text-sm font-medium text-slate-700">Produkte</span>
                <textarea
                  value={form.productsText}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, productsText: event.target.value }))}
                  rows={3}
                  placeholder={productNames.slice(0, 4).join(', ')}
                  className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                />
              </label>

              <div className="mt-4">
                <div className="text-sm font-medium text-slate-700">Bereiche</div>
                <div className="mt-2 border border-slate-200 bg-slate-50">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Abschnitte waehlen
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={handleSelectAllSections}
                        className="border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700"
                      >
                        Alle Auswaehlen
                      </button>
                      <button
                        type="button"
                        onClick={() => setSelectedScopeKeys([])}
                        className="border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-500"
                      >
                        Auswahl leeren
                      </button>
                    </div>
                  </div>
                  <div className="max-h-72 overflow-y-auto p-2">
                    {sectionScopeOptions.length === 0 ? (
                      <div className="px-3 py-6 text-sm text-slate-500">
                        Keine Abschnitte verfuegbar.
                      </div>
                    ) : (
                      <div className="grid gap-1">
                        {sectionScopeOptions.map((option) => {
                          const alreadyAdded = addedScopeKeySet.has(option.key)
                          return (
                            <label
                              key={option.key}
                              className={`flex items-start gap-3 px-3 py-2 text-sm ${
                                alreadyAdded ? 'text-slate-400' : 'text-slate-700 hover:bg-white'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={selectedScopeSet.has(option.key)}
                                disabled={alreadyAdded}
                                onChange={() => handleToggleScopeSelection(option.key)}
                                className="mt-0.5 h-4 w-4"
                              />
                              <span>{option.label}</span>
                            </label>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
                <div className="mt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={handleAddSelectedScopes}
                    className="inline-flex items-center justify-center gap-1 border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold"
                  >
                    <LuPlus className="h-4 w-4" />
                    Hinzufuegen
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {form.scopes.map((scope) => {
                    const key = `${scope.scope_type}-${scope.scope_id}`
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() =>
                          setForm((currentForm) => ({
                            ...currentForm,
                            scopes: currentForm.scopes.filter(
                              (candidate) => !(candidate.scope_type === scope.scope_type && candidate.scope_id === scope.scope_id),
                            ),
                          }))
                        }
                        className="border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700"
                      >
                        {scopeLabelsByKey[key] ?? key} x
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="mt-5 grid gap-3">
                {metricTypes.map((metricType) => {
                  const metric = form.metricInputs[metricType]
                  return (
                    <div key={metricType} className="border border-slate-200 bg-slate-50 p-3">
                      <label className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={metric.enabled}
                          onChange={(event) => handleMetricChange(metricType, { enabled: event.target.checked })}
                          className="h-5 w-5"
                        />
                        <span className="font-semibold text-slate-900">{metricLabels[metricType]}</span>
                      </label>
                      <div className="mt-3 grid gap-3 sm:grid-cols-3">
                        <label className="block">
                          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Faellig</span>
                          <input
                            type="number"
                            value={metric.threshold}
                            onChange={(event) => handleMetricChange(metricType, { threshold: event.target.value })}
                            className="mt-1 w-full border border-slate-200 px-3 py-2 text-sm"
                          />
                        </label>
                        <label className="block">
                          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Bald</span>
                          <input
                            type="number"
                            value={metric.warningThreshold}
                            onChange={(event) => handleMetricChange(metricType, { warningThreshold: event.target.value })}
                            className="mt-1 w-full border border-slate-200 px-3 py-2 text-sm"
                          />
                        </label>
                        {metricType === 'gdd_since' ? (
                          <label className="block">
                            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Basis C</span>
                            <input
                              type="number"
                              value={metric.baseTemperature}
                              onChange={(event) => handleMetricChange(metricType, { baseTemperature: event.target.value })}
                              className="mt-1 w-full border border-slate-200 px-3 py-2 text-sm"
                            />
                          </label>
                        ) : null}
                      </div>
                    </div>
                  )
                })}
              </div>

              <label className="mt-4 block">
                <span className="text-sm font-medium text-slate-700">Notizen</span>
                <textarea
                  value={form.notes}
                  onChange={(event) => setForm((currentForm) => ({ ...currentForm, notes: event.target.value }))}
                  rows={2}
                  className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm"
                />
              </label>

              <div className="mt-5 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={handleNewRule}
                  className="border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600"
                >
                  Zuruecksetzen
                </button>
                <button
                  type="button"
                  onClick={() => void handleSaveRule()}
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-2 border border-sky-700 bg-sky-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  <LuPencil className="h-4 w-4" />
                  {isSubmitting ? 'Speichern...' : 'Speichern'}
                </button>
              </div>
            </div>
          </section>
        )}
      </div>
    </section>
  )
}
