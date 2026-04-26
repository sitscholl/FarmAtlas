import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'

import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import FieldDetail from './pages/FieldDetail'
import FieldsTablePage from './pages/FieldsTablePage'
import Home from './pages/Home'
import IrrigationTablePage from './pages/IrrigationTablePage'
import NutrientsTablePage from './pages/NutrientsTablePage'
import VegetationTablePage from './pages/VegetationTablePage'
import VarietyTablePage from './pages/VarietyTablePage'

const getIsDesktopViewport = () => {
  if (typeof window === 'undefined') {
    return false
  }

  return window.matchMedia('(min-width: 768px)').matches
}

export default function App() {
  const [isDesktop, setIsDesktop] = useState(getIsDesktopViewport)
  const [isSidebarOpen, setIsSidebarOpen] = useState(getIsDesktopViewport)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 768px)')

    const handleMediaQueryChange = (event: MediaQueryList | MediaQueryListEvent) => {
      const matches = 'matches' in event ? event.matches : mediaQuery.matches
      setIsDesktop(matches)
      setIsSidebarOpen(matches)
    }

    handleMediaQueryChange(mediaQuery)

    const onChange = (event: MediaQueryListEvent) => handleMediaQueryChange(event)
    mediaQuery.addEventListener('change', onChange)

    return () => mediaQuery.removeEventListener('change', onChange)
  }, [])

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-slate-50 text-slate-900">
      <Sidebar isDesktop={isDesktop} isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      <div
        className={`min-h-screen w-full transition-[padding] duration-300 ${
          isDesktop && isSidebarOpen ? 'md:pl-72' : 'md:pl-0'
        }`}
      >
        <Navbar onToggleSidebar={() => setIsSidebarOpen((isOpen) => !isOpen)} />

        <main className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-7xl justify-center px-4 py-6 sm:px-6 sm:py-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/fields" element={<FieldsTablePage />} />
            <Route path="/irrigation" element={<IrrigationTablePage />} />
            <Route path="/vegetation" element={<VegetationTablePage />} />
            <Route path="/nutrients" element={<NutrientsTablePage />} />
            <Route path="/variety" element={<VarietyTablePage />} />
            <Route path="/fields/:fieldId" element={<FieldDetail />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
