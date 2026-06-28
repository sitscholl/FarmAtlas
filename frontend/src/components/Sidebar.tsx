import { NavLink } from 'react-router-dom'

import { CiApple } from 'react-icons/ci'
import { GiPlantWatering } from 'react-icons/gi'
import { MdWaterDrop } from 'react-icons/md'
import type { IconType } from 'react-icons'
import { IoHomeOutline } from 'react-icons/io5'
import { LuLeaf, LuShieldAlert, LuTableProperties, LuTrees } from 'react-icons/lu'

import styles from '../styles/Home.module.css'

type SidebarProps = {
  isDesktop: boolean
  isOpen: boolean
  onClose: () => void
}

type NavigationItem = {
  to: string
  label: string
  icon: IconType
  end?: boolean
}

type NavigationGroup = {
  label: string
  items: NavigationItem[]
}

const homeItem: NavigationItem = { to: '/', label: 'Home', icon: IoHomeOutline, end: true }

const navigationGroups: NavigationGroup[] = [
  {
    label: 'Wasserbilanz',
    items: [
      { to: '/water-balance', label: 'Wasserbilanz', icon: MdWaterDrop },
      { to: '/irrigation', label: 'Bewaesserung', icon: GiPlantWatering },
    ],
  },
  {
    label: 'Pflanzenschutz',
    items: [
      { to: '/crop-protection', label: 'Pflanzenschutz', icon: LuShieldAlert },
    ],
  },
  {
    label: 'Statistik',
    items: [
      { to: '/field-statistics', label: 'Feldstatistik', icon: LuTableProperties },
      { to: '/zaehlungen', label: 'Zaehlungen', icon: LuTableProperties },
      { to: '/jahreswerte', label: 'Jahreswerte', icon: LuTableProperties },
    ],
  },
  {
    label: 'Datenbank',
    items: [
      { to: '/fields', label: 'Anlagen', icon: LuTableProperties },
      { to: '/vegetation', label: 'Vegetation', icon: LuTrees },
      { to: '/nutrients', label: 'Naehrstoffe', icon: LuLeaf },
      { to: '/variety', label: 'Sorten', icon: CiApple },
    ],
  },
]

function SidebarLink({
  item,
  isDesktop,
  onClose,
}: {
  item: NavigationItem
  isDesktop: boolean
  onClose: () => void
}) {
  const { to, label, icon: Icon, end } = item

  return (
    <NavLink
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
  )
}

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
        className={`fixed left-0 top-0 z-40 flex h-dvh w-[min(18rem,calc(100vw-1rem))] max-w-full flex-col border-r border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-6 shadow-md transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:w-72`}
        aria-label="Seitenleiste"
      >
        <div className="shrink-0 border-b border-[color:var(--color-border)] px-2 pb-2">
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">Navigation</p>
        </div>

        <nav className="mt-6 flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto pr-1 pb-2">
          <div className="flex flex-col gap-1">
            <SidebarLink item={homeItem} isDesktop={isDesktop} onClose={onClose} />
          </div>

          {navigationGroups.map((group) => (
            <section key={group.label} className="flex flex-col gap-1" aria-labelledby={`sidebar-${group.label}`}>
              <h2
                id={`sidebar-${group.label}`}
                className="px-2 text-xs font-semibold uppercase tracking-[0.22em] text-[color:var(--color-text-muted)]"
              >
                {group.label}
              </h2>
              <div className="mt-1 flex flex-col gap-1">
                {group.items.map((item) => (
                  <SidebarLink
                    key={item.to}
                    item={item}
                    isDesktop={isDesktop}
                    onClose={onClose}
                  />
                ))}
              </div>
            </section>
          ))}
        </nav>
      </aside>
    </>
  )
}
