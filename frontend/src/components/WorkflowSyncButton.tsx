import { useState } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

import type { IconType } from 'react-icons'

import { getApiErrorMessage } from '../lib/apiErrors'
import styles from '../styles/Home.module.css'

type WorkflowStatus = 'loading' | 'success' | 'warning' | 'failed'

type WorkflowDialogState<TDetail> = {
  status: WorkflowStatus
  title: string
  message: string
  details?: TDetail[]
}

type WorkflowSyncButtonProps<TResponse, TDetail> = {
  ariaLabel: string
  title: string
  icon: IconType
  loadingTitle: string
  loadingMessage: string
  successTitle: string
  warningTitle: string
  failedTitle: string
  fallbackErrorMessage: string
  request: () => Promise<TResponse>
  getStatus: (response: TResponse) => Exclude<WorkflowStatus, 'loading'>
  getMessage: (response: TResponse) => string
  getDetails?: (response: TResponse) => TDetail[]
  renderDetail?: (detail: TDetail) => ReactNode
  getDetailKey?: (detail: TDetail, index: number) => string
  onCompleted?: (response: TResponse) => void
}

function titleForStatus(
  status: WorkflowStatus,
  titles: Pick<
    WorkflowSyncButtonProps<unknown, unknown>,
    'loadingTitle' | 'successTitle' | 'warningTitle' | 'failedTitle'
  >,
) {
  if (status === 'failed') {
    return titles.failedTitle
  }
  if (status === 'warning') {
    return titles.warningTitle
  }
  if (status === 'loading') {
    return titles.loadingTitle
  }
  return titles.successTitle
}

export default function WorkflowSyncButton<TResponse, TDetail>({
  ariaLabel,
  title,
  icon: Icon,
  loadingTitle,
  loadingMessage,
  fallbackErrorMessage,
  request,
  getStatus,
  getMessage,
  getDetails,
  renderDetail,
  getDetailKey,
  onCompleted,
  ...titles
}: WorkflowSyncButtonProps<TResponse, TDetail>) {
  const [isRunning, setIsRunning] = useState(false)
  const [dialog, setDialog] = useState<WorkflowDialogState<TDetail> | null>(null)

  const runWorkflow = async () => {
    if (isRunning) {
      return
    }

    setIsRunning(true)
    setDialog({
      status: 'loading',
      title: loadingTitle,
      message: loadingMessage,
    })

    try {
      const response = await request()
      const status = getStatus(response)
      onCompleted?.(response)
      setDialog({
        status,
        title: titleForStatus(status, { loadingTitle, ...titles }),
        message: getMessage(response),
        details: getDetails?.(response),
      })
    } catch (error) {
      setDialog({
        status: 'failed',
        title: titles.failedTitle,
        message: getApiErrorMessage(error, fallbackErrorMessage),
      })
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={runWorkflow}
        disabled={isRunning}
        className={`${styles.navbarButton} disabled:cursor-not-allowed disabled:opacity-60`}
        aria-label={ariaLabel}
        title={title}
      >
        <Icon className={isRunning ? 'animate-pulse' : ''} />
      </button>

      {dialog ? createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/30 px-4">
          <div className="w-full max-w-md border border-slate-200 bg-white p-5 shadow-xl">
            <div className="flex items-start gap-3">
              <div
                className={[
                  'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
                  dialog.status === 'failed'
                    ? 'bg-rose-50 text-rose-700'
                    : dialog.status === 'warning'
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-emerald-50 text-emerald-700',
                ].join(' ')}
              >
                <Icon className={dialog.status === 'loading' ? 'animate-pulse' : ''} />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-sm font-semibold text-slate-900">{dialog.title}</h2>
                <p className="mt-1 text-sm text-slate-700">{dialog.message}</p>

                {dialog.details && dialog.details.length > 0 && renderDetail ? (
                  <div className="mt-3 max-h-44 overflow-auto border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
                    {dialog.details.map((detail, index) => (
                      <div key={getDetailKey?.(detail, index) ?? String(index)} className="py-1">
                        {renderDetail(detail)}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>

            {dialog.status !== 'loading' ? (
              <div className="mt-5 flex justify-end">
                <button
                  type="button"
                  onClick={() => setDialog(null)}
                  className="border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Schliessen
                </button>
              </div>
            ) : null}
          </div>
        </div>,
        document.body,
      ) : null}
    </>
  )
}
