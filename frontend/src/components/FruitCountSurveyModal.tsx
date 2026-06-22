import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { FiRefreshCw, FiTrash2, FiX } from 'react-icons/fi'

import api from '../api'
import { getApiErrorMessage } from '../lib/apiErrors'
import { notifyDataChanged } from '../lib/dataEvents'
import type {
  FieldDetailRead,
  FruitCountSampleCreate,
  FruitCountSampleRead,
  FruitCountSurveyDraftCreate,
  FruitCountSurveyRead,
} from '../types/generated/api'
import FruitCountScopePicker, { type FruitCountScope } from './FruitCountScopePicker'

type FruitCountSurveyModalProps = {
  isOpen: boolean
  initialScope?: FruitCountScope | null
  fieldDetails?: FieldDetailRead[]
  onClose: () => void
}

type SampleRowStatus = 'saved' | 'saving' | 'error'

type SampleRow = {
  localId: string
  id?: number
  tree_label: string
  apple_count: string
  notes: string
  status: SampleRowStatus
  error?: string
}

type StoredDraft = {
  surveyId: number | null
  scope: FruitCountScope | null
  date: string
  seasonYear: string
  timingCode: string
  method: string
  observer: string
  notes: string
  includeInAggregation: boolean
  samples: SampleRow[]
}

const STORAGE_KEY = 'farmatlas:fruit-count-survey-draft'
const TIMING_BEFORE_HAND_THINNING = 'Vor Handausdünnung'
const TIMING_AFTER_HAND_THINNING = 'Nach Handausdünnung'
const TIMING_OPTIONS = [TIMING_BEFORE_HAND_THINNING, TIMING_AFTER_HAND_THINNING] as const

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10)
}

function defaultTimingCodeForDate(date: string) {
  const [, monthValue, dayValue] = date.split('-').map((part) => Number(part))
  if (Number.isInteger(monthValue) && Number.isInteger(dayValue)) {
    return monthValue > 8 || (monthValue === 8 && dayValue > 1)
      ? TIMING_AFTER_HAND_THINNING
      : TIMING_BEFORE_HAND_THINNING
  }

  return TIMING_BEFORE_HAND_THINNING
}

function normalizeTimingCode(value: string, date: string) {
  return TIMING_OPTIONS.some((option) => option === value)
    ? value
    : defaultTimingCodeForDate(date)
}

function currentSeasonYear() {
  return String(new Date().getFullYear())
}

function emptyStoredDraft(initialScope?: FruitCountScope | null): StoredDraft {
  const date = todayIsoDate()
  return {
    surveyId: null,
    scope: initialScope ?? null,
    date,
    seasonYear: currentSeasonYear(),
    timingCode: defaultTimingCodeForDate(date),
    method: '',
    observer: '',
    notes: '',
    includeInAggregation: true,
    samples: [],
  }
}

function optionalText(value: string) {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

function getScopePayload(scope: FruitCountScope) {
  return {
    field_id: scope.type === 'field' ? scope.field_id : null,
    planting_id: scope.type === 'planting' ? scope.planting_id : null,
    section_id: scope.type === 'section' ? scope.section_id : null,
  }
}

function serializeStoredDraft(draft: StoredDraft) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(draft))
}

function readStoredDraft() {
  try {
    const storedValue = localStorage.getItem(STORAGE_KEY)
    if (storedValue === null) {
      return null
    }
    return JSON.parse(storedValue) as StoredDraft
  } catch {
    return null
  }
}

function removeStoredDraft() {
  localStorage.removeItem(STORAGE_KEY)
}

function newLocalId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export default function FruitCountSurveyModal({
  isOpen,
  initialScope,
  fieldDetails,
  onClose,
}: FruitCountSurveyModalProps) {
  const [surveyId, setSurveyId] = useState<number | null>(null)
  const surveyIdRef = useRef<number | null>(null)
  const draftPromiseRef = useRef<Promise<number> | null>(null)
  const hasRemoteChangesRef = useRef(false)
  const hasManualTimingCodeRef = useRef(false)
  const [scope, setScope] = useState<FruitCountScope | null>(initialScope ?? null)
  const [date, setDate] = useState(todayIsoDate)
  const [seasonYear, setSeasonYear] = useState(currentSeasonYear)
  const [timingCode, setTimingCode] = useState(() => defaultTimingCodeForDate(todayIsoDate()))
  const [method, setMethod] = useState('')
  const [observer, setObserver] = useState('')
  const [notes, setNotes] = useState('')
  const [includeInAggregation, setIncludeInAggregation] = useState(true)
  const [treeLabel, setTreeLabel] = useState('')
  const [appleCount, setAppleCount] = useState('')
  const [sampleNotes, setSampleNotes] = useState('')
  const [samples, setSamples] = useState<SampleRow[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [hasRestoredDraft, setHasRestoredDraft] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const storedDraft = readStoredDraft()
    const nextDraft = storedDraft ?? emptyStoredDraft(initialScope)
    const resolvedScope = storedDraft?.scope ?? initialScope ?? nextDraft.scope

    setSurveyId(nextDraft.surveyId)
    surveyIdRef.current = nextDraft.surveyId
    draftPromiseRef.current = null
    hasRemoteChangesRef.current = false
    hasManualTimingCodeRef.current = storedDraft !== null
    setScope(resolvedScope)
    setDate(nextDraft.date)
    setSeasonYear(nextDraft.seasonYear)
    setTimingCode(normalizeTimingCode(nextDraft.timingCode, nextDraft.date))
    setMethod(nextDraft.method)
    setObserver(nextDraft.observer)
    setNotes(nextDraft.notes)
    setIncludeInAggregation(nextDraft.includeInAggregation)
    setSamples(nextDraft.samples ?? [])
    setTreeLabel('')
    setAppleCount('')
    setSampleNotes('')
    setErrorMessage(null)
    setHasRestoredDraft(storedDraft !== null)
  }, [initialScope, isOpen])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    serializeStoredDraft({
      surveyId,
      scope,
      date,
      seasonYear,
      timingCode,
      method,
      observer,
      notes,
      includeInAggregation,
      samples,
    })
  }, [date, includeInAggregation, isOpen, method, notes, observer, samples, scope, seasonYear, surveyId, timingCode])

  const summary = useMemo(() => {
    const counts = samples
      .map((sample) => Number(sample.apple_count))
      .filter((count) => Number.isFinite(count))
    const total = counts.reduce((sum, count) => sum + count, 0)
    const mean = counts.length === 0 ? null : total / counts.length
    return {
      count: counts.length,
      total,
      mean,
      min: counts.length === 0 ? null : Math.min(...counts),
      max: counts.length === 0 ? null : Math.max(...counts),
    }
  }, [samples])

  const buildDraftPayload = (): FruitCountSurveyDraftCreate | null => {
    if (scope === null) {
      setErrorMessage('Bitte Anlage, Pflanzung oder Abschnitt auswaehlen.')
      return null
    }

    const parsedSeasonYear = Number(seasonYear)
    if (!Number.isInteger(parsedSeasonYear) || parsedSeasonYear < 1900) {
      setErrorMessage('Bitte ein gueltiges Jahr eingeben.')
      return null
    }

    if (date.trim() === '') {
      setErrorMessage('Bitte ein Datum eingeben.')
      return null
    }

    if (timingCode.trim() === '') {
      setErrorMessage('Bitte einen Zeitpunkt eingeben.')
      return null
    }

    return {
      season_year: parsedSeasonYear,
      date,
      timing_code: timingCode.trim(),
      ...getScopePayload(scope),
      method: optionalText(method),
      observer: optionalText(observer),
      notes: optionalText(notes),
      include_in_aggregation: includeInAggregation,
      quality_flag: null,
    }
  }

  const ensureDraft = async () => {
    if (surveyIdRef.current !== null) {
      return surveyIdRef.current
    }

    if (draftPromiseRef.current !== null) {
      return draftPromiseRef.current
    }

    const payload = buildDraftPayload()
    if (payload === null) {
      throw new Error('Survey metadata is incomplete.')
    }

    draftPromiseRef.current = api
      .post<FruitCountSurveyRead>('/fruit-counts/surveys/drafts', payload)
      .then((response) => {
        surveyIdRef.current = response.data.id
        setSurveyId(response.data.id)
        return response.data.id
      })
      .finally(() => {
        draftPromiseRef.current = null
      })

    return draftPromiseRef.current
  }

  const saveSample = async (row: SampleRow) => {
    setSamples((currentRows) =>
      currentRows.map((currentRow) =>
        currentRow.localId === row.localId
          ? { ...currentRow, status: 'saving', error: undefined }
          : currentRow,
      ),
    )

    try {
      const activeSurveyId = await ensureDraft()
      const payload: FruitCountSampleCreate = {
        tree_label: optionalText(row.tree_label),
        apple_count: Number(row.apple_count),
        notes: optionalText(row.notes),
      }
      const response = await api.post<FruitCountSampleRead>(
        `/fruit-counts/surveys/${activeSurveyId}/samples`,
        payload,
      )
      setSamples((currentRows) =>
        currentRows.map((currentRow) =>
          currentRow.localId === row.localId
            ? {
                ...currentRow,
                id: response.data.id,
                status: 'saved',
                error: undefined,
              }
            : currentRow,
        ),
      )
      hasRemoteChangesRef.current = true
    } catch (error) {
      console.error('Error saving fruit count sample', error)
      setSamples((currentRows) =>
        currentRows.map((currentRow) =>
          currentRow.localId === row.localId
            ? {
                ...currentRow,
                status: 'error',
                error: getApiErrorMessage(error, 'Die Zaehlung konnte nicht gespeichert werden.'),
              }
            : currentRow,
        ),
      )
    }
  }

  const handleAddSample = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage(null)

    const parsedAppleCount = Number(appleCount)
    if (!Number.isInteger(parsedAppleCount) || parsedAppleCount < 0) {
      setErrorMessage('Bitte eine ganze, nicht-negative Anzahl eingeben.')
      return
    }

    const row: SampleRow = {
      localId: newLocalId(),
      tree_label: treeLabel.trim(),
      apple_count: String(parsedAppleCount),
      notes: sampleNotes.trim(),
      status: 'saving',
    }

    setSamples((currentRows) => [...currentRows, row])
    setTreeLabel('')
    setAppleCount('')
    setSampleNotes('')
    await saveSample(row)
  }

  const handleRetry = async (row: SampleRow) => {
    await saveSample(row)
  }

  const handleDeleteSample = async (row: SampleRow) => {
    if (row.id === undefined) {
      setSamples((currentRows) => currentRows.filter((currentRow) => currentRow.localId !== row.localId))
      return
    }

    setSamples((currentRows) =>
      currentRows.map((currentRow) =>
        currentRow.localId === row.localId ? { ...currentRow, status: 'saving' } : currentRow,
      ),
    )

    try {
      await api.delete(`/fruit-counts/samples/${row.id}`)
      setSamples((currentRows) => currentRows.filter((currentRow) => currentRow.localId !== row.localId))
      hasRemoteChangesRef.current = true
    } catch (error) {
      console.error(`Error deleting fruit count sample ${row.id}`, error)
      setSamples((currentRows) =>
        currentRows.map((currentRow) =>
          currentRow.localId === row.localId
            ? {
                ...currentRow,
                status: 'error',
                error: getApiErrorMessage(error, 'Die Zaehlung konnte nicht geloescht werden.'),
              }
            : currentRow,
        ),
      )
    }
  }

  const handleClose = () => {
    const hasUnsavedRows = samples.some((sample) => sample.status !== 'saved')
    if (!hasUnsavedRows) {
      removeStoredDraft()
    }
    if (hasRemoteChangesRef.current) {
      notifyDataChanged()
      hasRemoteChangesRef.current = false
    }
    onClose()
  }

  const handleDiscardLocalDraft = () => {
    removeStoredDraft()
    const nextDraft = emptyStoredDraft(initialScope)
    setSurveyId(nextDraft.surveyId)
    surveyIdRef.current = nextDraft.surveyId
    draftPromiseRef.current = null
    hasManualTimingCodeRef.current = false
    setScope(nextDraft.scope)
    setDate(nextDraft.date)
    setSeasonYear(nextDraft.seasonYear)
    setTimingCode(nextDraft.timingCode)
    setMethod(nextDraft.method)
    setObserver(nextDraft.observer)
    setNotes(nextDraft.notes)
    setIncludeInAggregation(nextDraft.includeInAggregation)
    setSamples([])
    setHasRestoredDraft(false)
  }

  const handleDateChange = (nextDate: string) => {
    setDate(nextDate)
    if (!hasManualTimingCodeRef.current) {
      setTimingCode(defaultTimingCodeForDate(nextDate))
    }
  }

  const handleTimingCodeChange = (nextTimingCode: string) => {
    hasManualTimingCodeRef.current = true
    setTimingCode(nextTimingCode)
  }

  if (!isOpen) {
    return null
  }

  const inputClasses =
    'mt-2 w-full border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100'

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-sm sm:flex sm:items-center sm:justify-center sm:px-4 sm:py-4"
      onClick={handleClose}
    >
      <div
        className="flex h-dvh w-full flex-col overflow-hidden bg-white sm:max-h-[calc(100vh-2rem)] sm:max-w-3xl sm:rounded-[2rem] sm:border sm:border-slate-200 sm:shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-100 px-4 py-4 sm:border-b-0 sm:px-6 sm:pt-6 sm:pb-0 sm:p-7">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              Neuer Eintrag
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900">
              Fruchtzaehlung
            </h2>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            aria-label="Modal schliessen"
          >
            <FiX className="h-5 w-5" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:mt-6 sm:px-6 sm:pt-0 sm:pb-0 sm:pr-7">
          {hasRestoredDraft ? (
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <span>Lokaler Entwurf wiederhergestellt.</span>
              <button
                type="button"
                onClick={handleDiscardLocalDraft}
                className="border border-amber-300 bg-white px-3 py-1.5 text-sm font-semibold text-amber-950 transition hover:bg-amber-100"
              >
                Entwurf verwerfen
              </button>
            </div>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="lg:col-span-2">
              <span className="text-sm font-medium text-slate-700">Bezugsflaeche</span>
              <FruitCountScopePicker
                value={scope}
                onChange={setScope}
                disabled={surveyId !== null}
                fieldDetails={fieldDetails}
              />
              {surveyId !== null ? (
                <div className="mt-2 text-xs text-slate-500">
                  Die Bezugsflaeche ist nach dem ersten gespeicherten Zaehlwert fixiert.
                </div>
              ) : null}
            </div>

            <label className="block">
              <span className="text-sm font-medium text-slate-700">Datum</span>
              <input
                type="date"
                value={date}
                onChange={(event) => handleDateChange(event.target.value)}
                disabled={surveyId !== null}
                className={inputClasses}
                required
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Jahr</span>
              <input
                type="number"
                value={seasonYear}
                onChange={(event) => setSeasonYear(event.target.value)}
                disabled={surveyId !== null}
                className={inputClasses}
                step="1"
                required
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Zeitpunkt</span>
              <select
                value={timingCode}
                onChange={(event) => handleTimingCodeChange(event.target.value)}
                disabled={surveyId !== null}
                className={inputClasses}
                required
              >
                {TIMING_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Methode</span>
              <input
                type="text"
                value={method}
                onChange={(event) => setMethod(event.target.value)}
                disabled={surveyId !== null}
                className={inputClasses}
                placeholder="Stichprobe"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Person</span>
              <input
                type="text"
                value={observer}
                onChange={(event) => setObserver(event.target.value)}
                disabled={surveyId !== null}
                className={inputClasses}
              />
            </label>
            <label className="flex items-center gap-3 pt-8">
              <input
                type="checkbox"
                checked={includeInAggregation}
                onChange={(event) => setIncludeInAggregation(event.target.checked)}
                disabled={surveyId !== null}
                className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
              />
              <span className="text-sm font-medium text-slate-700">In Aggregation verwenden</span>
            </label>
            <label className="block lg:col-span-2">
              <span className="text-sm font-medium text-slate-700">Notizen</span>
              <input
                type="text"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                disabled={surveyId !== null}
                className={inputClasses}
              />
            </label>
          </div>

          <form className="mt-6 border border-slate-200 bg-slate-50 p-4" onSubmit={handleAddSample}>
            <div className="grid gap-3 lg:grid-cols-[1fr_10rem_1.4fr_auto]">
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Baum</span>
                <input
                  type="text"
                  value={treeLabel}
                  onChange={(event) => setTreeLabel(event.target.value)}
                  className={inputClasses}
                  placeholder="1"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Anzahl</span>
                <input
                  type="number"
                  value={appleCount}
                  onChange={(event) => setAppleCount(event.target.value)}
                  className={inputClasses}
                  step="1"
                  min="0"
                  required
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Notiz</span>
                <input
                  type="text"
                  value={sampleNotes}
                  onChange={(event) => setSampleNotes(event.target.value)}
                  className={inputClasses}
                />
              </label>
              <div className="flex items-end">
                <button
                  type="submit"
                  className="w-full rounded-full bg-sky-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-sky-700"
                >
                  Speichern
                </button>
              </div>
            </div>
          </form>

          {errorMessage ? (
            <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_16rem]">
            <div className="border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">Gespeicherte Zaehlwerte</h3>
              </div>
              {samples.length === 0 ? (
                <div className="px-4 py-8 text-sm text-slate-500">
                  Noch keine Zaehlwerte erfasst.
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {samples.map((sample, index) => (
                    <div key={sample.localId} className="grid gap-3 px-4 py-3 text-sm sm:grid-cols-[4rem_1fr_6rem_auto] sm:items-center">
                      <div className="font-semibold text-slate-400">#{index + 1}</div>
                      <div className="min-w-0">
                        <div className="font-medium text-slate-900">
                          {sample.tree_label || 'Ohne Baumlabel'}
                        </div>
                        {sample.notes ? <div className="text-xs text-slate-500">{sample.notes}</div> : null}
                        {sample.error ? <div className="mt-1 text-xs text-rose-700">{sample.error}</div> : null}
                      </div>
                      <div className="font-semibold tabular-nums text-slate-900">{sample.apple_count}</div>
                      <div className="flex items-center justify-between gap-3 sm:justify-end">
                        <span
                          className={`text-xs font-semibold ${
                            sample.status === 'saved'
                              ? 'text-emerald-700'
                              : sample.status === 'saving'
                                ? 'text-slate-500'
                                : 'text-rose-700'
                          }`}
                        >
                          {sample.status === 'saved' ? 'Gespeichert' : sample.status === 'saving' ? 'Speichert...' : 'Fehler'}
                        </span>
                        {sample.status === 'error' ? (
                          <button
                            type="button"
                            onClick={() => handleRetry(sample)}
                            className="p-2 text-slate-600 transition hover:text-slate-950"
                            aria-label="Zaehlwert erneut speichern"
                          >
                            <FiRefreshCw />
                          </button>
                        ) : null}
                        <button
                          type="button"
                          onClick={() => handleDeleteSample(sample)}
                          disabled={sample.status === 'saving'}
                          className="p-2 text-rose-600 transition hover:text-rose-800 disabled:cursor-not-allowed disabled:text-slate-300"
                          aria-label="Zaehlwert loeschen"
                        >
                          <FiTrash2 />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Zusammenfassung</p>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-slate-500">Proben</div>
                  <div className="text-xl font-semibold text-slate-900">{summary.count}</div>
                </div>
                <div>
                  <div className="text-slate-500">Summe</div>
                  <div className="text-xl font-semibold text-slate-900">{summary.total}</div>
                </div>
                <div>
                  <div className="text-slate-500">Mittel</div>
                  <div className="text-xl font-semibold text-slate-900">
                    {summary.mean === null ? 'n/a' : summary.mean.toFixed(1)}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">Min/Max</div>
                  <div className="text-xl font-semibold text-slate-900">
                    {summary.min === null || summary.max === null ? 'n/a' : `${summary.min}/${summary.max}`}
                  </div>
                </div>
              </div>
              {surveyId !== null ? (
                <div className="mt-4 border-t border-slate-200 pt-3 text-xs text-slate-500">
                  Survey #{surveyId}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-100 bg-white px-4 py-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:mt-6 sm:flex sm:justify-end sm:gap-3 sm:px-6 sm:pt-4 sm:pb-6">
          <button
            type="button"
            onClick={handleClose}
            className="w-full rounded-full border border-slate-200 px-5 py-3 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 sm:w-auto"
          >
            Schliessen
          </button>
        </div>
      </div>
    </div>
  )
}
