import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { createActions } from '../config/createActions'
import type { CreateActionConfig } from '../types/createActions'
import CreateEntityModal from './CreateEntityModal'

import { IoMdAdd } from "react-icons/io";
import { IoHomeOutline } from "react-icons/io5";
import { LuTableProperties } from 'react-icons/lu'
import { GiPlantWatering } from 'react-icons/gi'

export default function Navbar() {
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
      <nav className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 py-3 shadow-sm backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6">
          <div className="flex items-center gap-5">
            <Link className="inline-flex items-center gap-2 text-gray-700 hover:text-sky-500" to="/">
              <IoHomeOutline /> Home
            </Link>
            <Link className="inline-flex items-center gap-2 text-gray-700 hover:text-sky-500" to="/fields">
              <LuTableProperties /> Anlagen
            </Link>
            <Link className="inline-flex items-center gap-2 text-gray-700 hover:text-sky-500" to="/irrigation">
              <GiPlantWatering /> Bewaesserung
            </Link>
          </div>

          <div ref={containerRef} className="relative">
            <button
              type="button"
              onClick={() => setIsMenuOpen((isOpen) => !isOpen)}
              className="flex h-8 w-8 items-center justify-center border border-slate-200 rounded-full z-50 text-slate-700 shadow-sm transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700"
              aria-label="Eintrag hinzufügen"
            >
              <IoMdAdd />
            </button>

            {isMenuOpen ? (
              <div className="absolute right-0 top-11 w-64 overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
                {createActions.map((action) => (
                  <button
                    key={action.id}
                    type="button"
                    onClick={() => {
                      setActiveAction(action)
                      setIsMenuOpen(false)
                    }}
                    className="block bg-white w-full px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:bg-sky-50 hover:text-sky-700"
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
