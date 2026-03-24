import type { ReactNode } from 'react'

export type DataTableColumn<Row> = {
  id: string
  header: string
  cell: (row: Row) => ReactNode
  headerClassName?: string
  cellClassName?: string
}

type DataTableProps<Row> = {
  columns: DataTableColumn<Row>[]
  rows: Row[]
  getRowKey: (row: Row) => string | number
  emptyMessage: string
}

export default function DataTable<Row>({
  columns,
  rows,
  getRowKey,
  emptyMessage,
}: DataTableProps<Row>) {
  return (
    <div className="overflow-hidden border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.id}
                  scope="col"
                  className={`whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 ${column.headerClassName ?? ''}`}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-10 text-center text-sm text-slate-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={getRowKey(row)} className="transition hover:bg-slate-50/80">
                  {columns.map((column) => (
                    <td
                      key={column.id}
                      className={`whitespace-nowrap px-4 py-3 text-sm text-slate-700 ${column.cellClassName ?? ''}`}
                    >
                      {column.cell(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
