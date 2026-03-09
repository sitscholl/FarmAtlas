type AppleField = {
  id: number
  name: string
  year: number
  water_balance: number
}

const fields: AppleField[] = [
    {
        id: 1,
        name: "Parleng",
        year: 2010,
        water_balance: 30
    },
    {
        id: 2,
        name: "Gänsacker",
        year: 2015,
        water_balance: 20
    },
    {
        id: 4,
        name: "Gasslwiese",
        year: 2020,
        water_balance: 10
    }
]

export default function Home() {
    return (
        <main className="min-h-screen w-screen justify-center">
            <div className="max-w-3xl justify-center border">
                <div className="mx-auto text-center mt-16">
                <h1 className="text-4xl font-bold mb-6">
                    Welcome to My App 🚀
                </h1>
                <p className="text-gray-600 mb-8">
                    This is the landing page of your FastAPI + React application.
                </p>
                </div>

                <div className="grid grid-cols-3 gap-6">
                    {fields.map((field) => (
                        <div className="border bg-white/60 p-4">
                            <p>{field.name}</p>
                            <p>{field.year}</p>
                            <p>{field.water_balance}</p>
                        </div>
                    ))}
                </div>
            </div>
        </main>
    )
}