import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { HiOutlineBars3 } from 'react-icons/hi2'
import { IoMdAdd } from 'react-icons/io'
import { LuRefreshCw } from 'react-icons/lu'

import api from '../api'
import { createActions } from '../config/createActions'
import { getApiErrorMessage } from '../lib/apiErrors'
import { notifyDataChanged } from '../lib/dataEvents'
import type { CreateActionConfig } from '../types/createActions'
import CreateEntityModal from './CreateEntityModal'

import styles from '../styles/Home.module.css'

type NavbarProps = {
  onToggleSidebar: () => void
}

type SmartFarmerSyncResult = {
  workflow_name: string
  source: string
  season_year: number
  status: string
  row_count: number
  unresolved_count: number
  error: string | null
  metadata: Record<string, unknown>
}

type SmartFarmerSyncResponse = {
  status: 'success' | 'warning' | 'failed' | string
  message: string
  results: SmartFarmerSyncResult[]
}

type SyncDialogState = {
  status: 'loading' | 'success' | 'warning' | 'failed'
  title: string
  message: string
  details?: SmartFarmerSyncResult[]
}

export default function Navbar({ onToggleSidebar }: NavbarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [activeAction, setActiveAction] = useState<CreateActionConfig | null>(null)
  const [isSyncingSmartFarmer, setIsSyncingSmartFarmer] = useState(false)
  const [syncDialog, setSyncDialog] = useState<SyncDialogState | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (containerRef.current !== null && !containerRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const handleSmartFarmerSync = async () => {
    if (isSyncingSmartFarmer) {
      return
    }

    setIsSyncingSmartFarmer(true)
    setSyncDialog({
      status: 'loading',
      title: 'Smartfarmer Sync',
      message: 'Spritzungen werden synchronisiert.',
    })

    try {
      const response = await api.post<SmartFarmerSyncResponse>('/treatments/sync-smartfarmer')
      const data = response.data
      const status = data.status === 'failed' || data.status === 'warning' ? data.status : 'success'
      if (status !== 'failed') {
        notifyDataChanged()
      }
      setSyncDialog({
        status,
        title:
          status === 'failed'
            ? 'Smartfarmer Sync fehlgeschlagen'
            : status === 'warning'
              ? 'Smartfarmer Sync mit Hinweisen'
              : 'Smartfarmer Sync abgeschlossen',
        message: data.message,
        details: data.results,
      })
    } catch (error) {
      setSyncDialog({
        status: 'failed',
        title: 'Smartfarmer Sync fehlgeschlagen',
        message: getApiErrorMessage(error, 'Smartfarmer Spritzungen konnten nicht synchronisiert werden.'),
      })
    } finally {
      setIsSyncingSmartFarmer(false)
    }
  }

  return (
    <>
      <nav className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 shadow-sm backdrop-blur">
        <div className="flex w-full items-center justify-between gap-3 px-4 py-3 sm:gap-6 sm:px-6">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={onToggleSidebar}
              className={styles.navbarButton}
              aria-label="Navigation umschalten"
            >
              <HiOutlineBars3 className="text-lg" />
            </button>

            <Link className="truncate text-base font-semibold tracking-tight text-slate-900 sm:text-lg" to="/">
              FarmAtlas
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSmartFarmerSync}
              disabled={isSyncingSmartFarmer}
              className={`${styles.navbarButton} disabled:cursor-not-allowed disabled:opacity-60`}
              aria-label="Smartfarmer Spritzungen Syncronisieren"
              title="Smartfarmer Spritzungen Syncronisieren"
            >
              <LuRefreshCw className={isSyncingSmartFarmer ? 'animate-spin' : ''} />
            </button>

            <div ref={containerRef} className="relative">
              <button
                type="button"
                onClick={() => setIsMenuOpen((isOpen) => !isOpen)}
                className={styles.navbarButton}
                aria-label="Eintrag hinzufuegen"
              >
                <IoMdAdd />
              </button>

              {isMenuOpen ? (
                <div className="absolute right-0 top-10 w-64 max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
                  {createActions.map((action) => (
                    <button
                      key={action.id}
                      type="button"
                      onClick={() => {
                        setActiveAction(action)
                        setIsMenuOpen(false)
                      }}
                      className={[styles.interactiveLink, styles.sidebarItem].join(' ')}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </nav>

      <CreateEntityModal
        action={activeAction}
        isOpen={activeAction !== null}
        onClose={() => setActiveAction(null)}
      />

      {syncDialog ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/30 px-4">
          <div className="w-full max-w-md border border-slate-200 bg-white p-5 shadow-xl">
            <div className="flex items-start gap-3">
              <div
                className={[
                  'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
                  syncDialog.status === 'failed'
                    ? 'bg-red-50 text-red-700'
                    : syncDialog.status === 'warning'
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-emerald-50 text-emerald-700',
                ].join(' ')}
              >
                <LuRefreshCw className={syncDialog.status === 'loading' ? 'animate-spin' : ''} />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-sm font-semibold text-slate-900">{syncDialog.title}</h2>
                <p className="mt-1 text-sm text-slate-700">{syncDialog.message}</p>

                {syncDialog.details && syncDialog.details.length > 0 ? (
                  <div className="mt-3 max-h-44 overflow-auto border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
                    {syncDialog.details.map((result) => (
                      <div key={`${result.source}-${result.season_year}`} className="py-1">
                        {result.season_year}: {result.status}, {result.row_count} Zeilen
                        {result.unresolved_count > 0 ? `, ${result.unresolved_count} nicht zugeordnet` : ''}
                        {result.error ? `, ${result.error}` : ''}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>

            {syncDialog.status !== 'loading' ? (
              <div className="mt-5 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSyncDialog(null)}
                  className="border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Schliessen
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  )
}
