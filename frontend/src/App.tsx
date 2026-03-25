import { Route, Routes } from 'react-router-dom'

import Navbar from './components/Navbar'
import FieldDetail from './pages/FieldDetail'
import FieldsTablePage from './pages/FieldsTablePage'
import Home from './pages/Home'
import IrrigationTablePage from './pages/IrrigationTablePage'

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Navbar />

      <main className="flex min-h-screen w-screen items-center justify-center px-6 py-10">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/fields" element={<FieldsTablePage />} />
          <Route path="/irrigation" element={<IrrigationTablePage />} />
          <Route path="/fields/:fieldId" element={<FieldDetail />} />
        </Routes>
      </main>
    </div>
  )
}
