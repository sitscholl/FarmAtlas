import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { HiOutlineBars3 } from 'react-icons/hi2'
import { IoMdAdd } from 'react-icons/io'

import { createActions } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import CreateEntityModal from './CreateEntityModal'

import styles from '../styles/Home.module.css'

type NavbarProps = {
  onToggleSidebar: () => void
}

export default function Navbar({ onToggleSidebar }: NavbarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [activeAction, setActiveAction] = useState<CreateActionConfig | null>(null)
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
      </nav>

      <CreateEntityModal
        action={activeAction}
        isOpen={activeAction !== null}
        onClose={() => setActiveAction(null)}
      />
    </>
  )
}
