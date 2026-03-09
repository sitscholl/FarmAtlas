import { Link } from 'react-router-dom'

export default function Navbar() {
  return (
    <nav className="bg-white shadow py-2">
      <div className="max-w-4xl mx-auto flex gap-6">
        <Link className="text-gray-700 hover:text-indigo-600" to="/">
          Home
        </Link>
      </div>
    </nav>
  )
}