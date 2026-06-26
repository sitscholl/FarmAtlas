import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { HiOutlineBars3 } from 'react-icons/hi2'
import { IoMdAdd } from 'react-icons/io'
import { LuCloudSun, LuRefreshCw, LuTractor } from 'react-icons/lu'

import api from '../api'
import { createActions } from '../config/createActions'
import { notifyDataChanged } from '../lib/dataEvents'
import type { CreateActionConfig } from '../types/createActions'
import type {
  TreatmentSmartFarmerSyncResponse,
  TreatmentSmartFarmerSyncResult,
  WeatherCacheRefreshResponse,
  WeatherCacheRefreshStationResult,
} from '../types/generated/api'
import CreateEntityModal from './CreateEntityModal'
import FruitCountSurveyModal from './FruitCountSurveyModal'
import WorkflowSyncButton from './WorkflowSyncButton'

import styles from '../styles/Home.module.css'

type NavbarProps = {
  onToggleSidebar: () => void
}

function normalizeWorkflowStatus(status: string): 'success' | 'warning' | 'failed' {
  return status === 'failed' || status === 'warning' ? status : 'success'
}

export default function Navbar({ onToggleSidebar }: NavbarProps) {
  const [openMenu, setOpenMenu] = useState<'add' | 'sync' | null>(null)
  const [activeAction, setActiveAction] = useState<CreateActionConfig | null>(null)
  const [isFruitCountOpen, setIsFruitCountOpen] = useState(false)
  const menuContainerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (menuContainerRef.current !== null && !menuContainerRef.current.contains(event.target as Node)) {
        setOpenMenu(null)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [])

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

          <div ref={menuContainerRef} className="flex items-center gap-2">
            <div className="relative">
              <button
                type="button"
                onClick={() => setOpenMenu((current) => (current === 'sync' ? null : 'sync'))}
                className={styles.navbarButton}
                aria-label="Synchronisieren"
              >
                <LuRefreshCw />
              </button>

              {openMenu === 'sync' ? (
                <div className="absolute right-0 top-10 w-72 max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
                  <WorkflowSyncButton<TreatmentSmartFarmerSyncResponse, TreatmentSmartFarmerSyncResult>
                    ariaLabel="Smartfarmer Spritzungen synchronisieren"
                    title="Smartfarmer Spritzungen synchronisieren"
                    icon={LuTractor}
                    triggerLabel="Smartfarmer Spritzungen synchronisieren"
                    triggerClassName={[styles.interactiveLink, styles.sidebarItem].join(' ')}
                    showTriggerIcon={false}
                    onTriggered={() => setOpenMenu(null)}
                    loadingTitle="Smartfarmer Sync"
                    loadingMessage="Spritzungen werden synchronisiert."
                    successTitle="Smartfarmer Sync abgeschlossen"
                    warningTitle="Smartfarmer Sync mit Hinweisen"
                    failedTitle="Smartfarmer Sync fehlgeschlagen"
                    fallbackErrorMessage="Smartfarmer Spritzungen konnten nicht synchronisiert werden."
                    request={() => api.post<TreatmentSmartFarmerSyncResponse>('/treatments/sync-smartfarmer').then((response) => response.data)}
                    getStatus={(response) => normalizeWorkflowStatus(response.status)}
                    getMessage={(response) => response.message}
                    getDetails={(response) => response.results}
                    getDetailKey={(result) => `${result.source}-${result.season_year}`}
                    renderDetail={(result) => (
                      <>
                        {result.season_year}: {result.status}, {result.row_count ?? 0} Zeilen
                        {(result.unresolved_count ?? 0) > 0 ? `, ${result.unresolved_count} nicht zugeordnet` : ''}
                        {result.error ? `, ${result.error}` : ''}
                      </>
                    )}
                    onCompleted={(response) => {
                      if (normalizeWorkflowStatus(response.status) !== 'failed') {
                        notifyDataChanged()
                      }
                    }}
                  />

                  <WorkflowSyncButton<WeatherCacheRefreshResponse, WeatherCacheRefreshStationResult>
                    ariaLabel="Wettercache aktualisieren"
                    title="Wettercache aktualisieren"
                    icon={LuCloudSun}
                    triggerLabel="Wettercache aktualisieren"
                    triggerClassName={[styles.interactiveLink, styles.sidebarItem].join(' ')}
                    showTriggerIcon={false}
                    onTriggered={() => setOpenMenu(null)}
                    loadingTitle="Wettercache Refresh"
                    loadingMessage="Wetterdaten werden aktualisiert."
                    successTitle="Wettercache aktualisiert"
                    warningTitle="Wettercache mit Hinweisen aktualisiert"
                    failedTitle="Wettercache Refresh fehlgeschlagen"
                    fallbackErrorMessage="Der Wettercache konnte nicht aktualisiert werden."
                    request={() => api.post<WeatherCacheRefreshResponse>('/weather/cache/refresh').then((response) => response.data)}
                    getStatus={(response) => normalizeWorkflowStatus(response.status)}
                    getMessage={(response) => response.message}
                    getDetails={(response) => response.results}
                    getDetailKey={(result, index) => `${result.source_provider}-${result.source_station}-${result.cache_kind}-${index}`}
                    renderDetail={(result) => (
                      <>
                        {result.source_provider}/{result.source_station} {result.cache_kind}: {result.status}, {result.row_count ?? 0} Zeilen
                        {result.refreshed ? ', aktualisiert' : ', aktuell'}
                        {result.error ? `, ${result.error}` : ''}
                      </>
                    )}
                    onCompleted={(response) => {
                      if (normalizeWorkflowStatus(response.status) !== 'failed') {
                        notifyDataChanged()
                      }
                    }}
                  />
                </div>
              ) : null}
            </div>

            <div className="relative">
              <button
                type="button"
                onClick={() => setOpenMenu((current) => (current === 'add' ? null : 'add'))}
                className={styles.navbarButton}
                aria-label="Eintrag hinzufuegen"
              >
                <IoMdAdd />
              </button>

              {openMenu === 'add' ? (
                <div className="absolute right-0 top-10 w-64 max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
                  {createActions.map((action) => (
                    <button
                      key={action.id}
                      type="button"
                      onClick={() => {
                        setActiveAction(action)
                        setOpenMenu(null)
                      }}
                      className={[styles.interactiveLink, styles.sidebarItem].join(' ')}
                    >
                      {action.label}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => {
                      setIsFruitCountOpen(true)
                      setOpenMenu(null)
                    }}
                    className={[styles.interactiveLink, styles.sidebarItem].join(' ')}
                  >
                    Fruchtzaehlung eintragen
                  </button>
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
      <FruitCountSurveyModal
        isOpen={isFruitCountOpen}
        onClose={() => setIsFruitCountOpen(false)}
      />
    </>
  )
}
