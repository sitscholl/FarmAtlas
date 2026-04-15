import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'

import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import FieldDetail from './pages/FieldDetail'
import FieldsTablePage from './pages/FieldsTablePage'
import Home from './pages/Home'
import IrrigationTablePage from './pages/IrrigationTablePage'
import VarietyTablePage from './pages/VarietyTablePage'

export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      <div className={`min-h-screen transition-[padding] duration-300 ${isSidebarOpen ? 'md:pl-72' : 'md:pl-0'}`}>
        <Navbar onToggleSidebar={() => setIsSidebarOpen((isOpen) => !isOpen)} />

        <main className="mx-auto flex min-h-[calc(100vh-4.5rem)] w-full max-w-6xl px-6 py-10">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/fields" element={<FieldsTablePage />} />
            <Route path="/irrigation" element={<IrrigationTablePage />} />
            <Route path="/variety" element={<VarietyTablePage />} />
            <Route path="/fields/:fieldId" element={<FieldDetail />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
