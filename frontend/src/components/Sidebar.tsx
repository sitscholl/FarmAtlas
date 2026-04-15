import { NavLink } from 'react-router-dom'

import { CiApple } from 'react-icons/ci'
import { GiPlantWatering } from 'react-icons/gi'
import { IoHomeOutline } from 'react-icons/io5'
import { LuTableProperties } from 'react-icons/lu'

import styles from '../styles/Home.module.css'

type SidebarProps = {
  isDesktop: boolean
  isOpen: boolean
  onClose: () => void
}

const navigationItems = [
  { to: '/', label: 'Home', icon: IoHomeOutline, end: true },
  { to: '/fields', label: 'Anlagen', icon: LuTableProperties },
  { to: '/irrigation', label: 'Bewaesserung', icon: GiPlantWatering },
  { to: '/variety', label: 'Sorten', icon: CiApple },
]

export default function Sidebar({ isDesktop, isOpen, onClose }: SidebarProps) {
  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-900/30 transition-opacity duration-300 ${
          isOpen ? 'pointer-events-auto opacity-100 md:pointer-events-none md:opacity-0' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={`fixed left-0 top-0 z-40 flex h-dvh w-[min(18rem,calc(100vw-1rem))] max-w-full flex-col border-r border-[color:var(--sidebar-border)] bg-[color:var(--sidebar)] px-4 py-6 shadow-[var(--shadow-soft)] transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:w-72`}
        aria-label="Seitenleiste"
      >
        <div className="border-b border-[color:var(--border-soft)] px-2 pb-2">
          <p className="mt-1 text-sm text-[color:var(--text-muted)]">Navigation</p>
        </div>

        <nav className="mt-6 flex flex-col gap-1">
          {navigationItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => {
                if (!isDesktop) {
                  onClose()
                }
              }}
              className={({ isActive }) =>
                [styles.interactiveLink, styles.sidebarItem, isActive ? styles.sidebarItemActive : '']
                  .filter(Boolean)
                  .join(' ')
              }
            >
              <Icon className={styles.sidebarIcon} />
              <span className={styles.interactiveLinkLabel}>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}
