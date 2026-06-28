import { FiAlertTriangle, FiX } from 'react-icons/fi'

import api from '../api'
import { formatWorkflowWarning, type WorkflowMessage } from '../lib/workflowWarnings'
import type {
  WaterBalanceSeriesPoint,
  WaterBalanceSeriesResponse,
  WorkflowErrorRead,
} from '../types/generated/api'
import WaterBalanceChart from './WaterBalanceChart'

export const WATER_BALANCE_FORECAST_DAYS = 5

export type WaterBalanceFieldRef = {
  id: number
  name: string
}

export type WaterBalanceModalState = {
  field: WaterBalanceFieldRef
  data: WaterBalanceSeriesPoint[]
  workflowMessages: WorkflowMessage[]
  isLoading: boolean
  errorMessage: string | null
}

function formatWorkflowError(error: WorkflowErrorRead): WorkflowMessage {
  return {
    kind: 'error',
    message: error.message,
  }
}

export function buildWaterBalanceLoadingState(field: WaterBalanceFieldRef): WaterBalanceModalState {
  return {
    field,
    data: [],
    workflowMessages: [],
    isLoading: true,
    errorMessage: null,
  }
}

export async function fetchWaterBalanceModalState(field: WaterBalanceFieldRef): Promise<WaterBalanceModalState> {
  try {
    const response = await api.get<WaterBalanceSeriesResponse>(
      `/fields/${field.id}/water-balance/series`,
      {
        params: { forecast_days: WATER_BALANCE_FORECAST_DAYS },
      },
    )
    const workflowMessages = [
      ...(response.data.warnings ?? []).map(formatWorkflowWarning),
      ...(response.data.errors ?? []).map(formatWorkflowError),
    ]
    const data = response.data.data ?? []
    return {
      field,
      data,
      workflowMessages,
      isLoading: false,
      errorMessage: data.length === 0 && workflowMessages.length === 0 ? 'Keine Wasserbilanzdaten vorhanden.' : null,
    }
  } catch (error) {
    console.error(`Error fetching water balance for field ${field.id}`, error)
    return {
      field,
      data: [],
      workflowMessages: [],
      isLoading: false,
      errorMessage: 'Die Wasserbilanz konnte nicht geladen werden.',
    }
  }
}

export default function WaterBalanceModal({
  state,
  onClose,
}: {
  state: WaterBalanceModalState | null
  onClose: () => void
}) {
  if (state === null) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-sm sm:flex sm:items-center sm:justify-center sm:px-4 sm:py-4"
      onClick={onClose}
    >
      <div
        className="flex h-dvh w-full flex-col overflow-hidden bg-white sm:max-h-[calc(100vh-2rem)] sm:max-w-6xl sm:border sm:border-slate-200 sm:shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-100 px-4 py-4 sm:px-6 sm:pt-6 sm:pb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">
              Wasserbilanz
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900">
              {state.field.name}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            aria-label="Popup schliessen"
          >
            <FiX className="h-5 w-5" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3 sm:px-6 sm:py-6">
          {state.isLoading ? (
            <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center text-slate-500">
              Lade Wasserbilanz...
            </div>
          ) : state.errorMessage ? (
            <div className="border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
              {state.errorMessage}
            </div>
          ) : (
            <div className="space-y-3">
              {state.workflowMessages.length > 0 ? (
                <div className="space-y-2">
                  {state.workflowMessages.map((message) => (
                    <div
                      key={`${message.kind}-${message.message}`}
                      className={
                        message.kind === 'error'
                          ? 'flex items-start gap-2 border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800'
                          : 'flex items-start gap-2 border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900'
                      }
                    >
                      <FiAlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                      <span>{message.message}</span>
                    </div>
                  ))}
                </div>
              ) : null}
              <WaterBalanceChart data={state.data} reservedForecastDays={WATER_BALANCE_FORECAST_DAYS} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
