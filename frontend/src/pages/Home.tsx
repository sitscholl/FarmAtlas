import FieldBox from '../components/FieldBox'

type AppleField = {
  id: number
  name: string
  year: number
  water_balance: number
}

const fields: AppleField[] = [
  {
    id: 1,
    name: 'Parleng',
    year: 2010,
    water_balance: 30,
  },
  {
    id: 2,
    name: 'Gansacker',
    year: 2015,
    water_balance: 20,
  },
  {
    id: 4,
    name: 'Gasslwiese',
    year: 2020,
    water_balance: 10,
  }
]

export default function Home() {
  return (
    <section className="relative max-w-5xl">

      <div className="relative rounded-3xl border border-slate-200/70 bg-white/70 p-8 shadow-xl backdrop-blur">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-400">
            Anlagen Übersicht
          </p>
          <h1 className="mt-4 text-4xl font-semibold text-slate-900 sm:text-5xl">
            Oberlenghof
          </h1>
        </div>

        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map((field) => (
            <FieldBox
              key={field.id}
              name={field.name}
              year={field.year}
              waterBalance={field.water_balance}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
