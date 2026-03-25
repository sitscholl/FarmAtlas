import { useEffect, useState, type ReactNode } from 'react'

export type DataTableColumn<Row> = {
  id: string
  header: string
  cell: (row: Row) => ReactNode
  headerClassName?: string
  cellClassName?: string
}

export type DataTableFilter = {
  id: string
  label: string
  type: 'text' | 'select' | 'date'
  value: string
  placeholder?: string
  options?: Array<{
    label: string
    value: string
  }>
}

export type DataTableSummaryCell<Row> = {
  columnId: string
  content: ReactNode | ((rows: Row[]) => ReactNode)
  className?: string
}

type DataTableProps<Row> = {
  columns: DataTableColumn<Row>[]
  rows: Row[]
  getRowKey: (row: Row) => string | number
  emptyMessage: string
  filters?: DataTableFilter[]
  onFilterChange?: (filterId: string, value: string) => void
  onResetFilters?: () => void
  summaryCells?: DataTableSummaryCell<Row>[]
  selectedRowKey?: string | number | null
  onRowSelect?: (row: Row | null) => void
}

export default function DataTable<Row>({
  columns,
  rows,
  getRowKey,
  emptyMessage,
  filters = [],
  onFilterChange,
  onResetFilters,
  summaryCells = [],
  selectedRowKey: controlledSelectedRowKey,
  onRowSelect,
}: DataTableProps<Row>) {
  const hasFilters = filters.length > 0
  const hasSummaryRow = summaryCells.length > 0 && rows.length > 0
  const [uncontrolledSelectedRowKey, setUncontrolledSelectedRowKey] = useState<
    string | number | null
  >(null)
  const selectedRowKey =
    controlledSelectedRowKey !== undefined
      ? controlledSelectedRowKey
      : uncontrolledSelectedRowKey

  useEffect(() => {
    if (selectedRowKey === null) {
      return
    }

    const stillExists = rows.some((row) => getRowKey(row) === selectedRowKey)
    if (!stillExists) {
      if (controlledSelectedRowKey === undefined) {
        setUncontrolledSelectedRowKey(null)
      }
      onRowSelect?.(null)
    }
  }, [controlledSelectedRowKey, getRowKey, onRowSelect, rows, selectedRowKey])

  const handleRowSelect = (row: Row) => {
    if (controlledSelectedRowKey === undefined) {
      setUncontrolledSelectedRowKey(getRowKey(row))
    }
    onRowSelect?.(row)
  }

  return (
    <div className="overflow-hidden border border-slate-200 bg-white shadow-sm">
      {hasFilters ? (
        <div className="border-b border-slate-200 bg-slate-50/80 px-4 py-4">
          <div className="flex flex-wrap items-end gap-4">
            {filters.map((filter) => (
              <label key={filter.id} className="min-w-[10rem] flex-1">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {filter.label}
                </span>
                {filter.type === 'select' ? (
                  <select
                    value={filter.value}
                    onChange={(event) => onFilterChange?.(filter.id, event.target.value)}
                    className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
                  >
                    {(filter.options ?? []).map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={filter.type}
                    value={filter.value}
                    onChange={(event) => onFilterChange?.(filter.id, event.target.value)}
                    placeholder={filter.placeholder}
                    className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
                  />
                )}
              </label>
            ))}
            {onResetFilters ? (
              <button
                type="button"
                onClick={onResetFilters}
                className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
              >
                Filter zuruecksetzen
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
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
              rows.map((row) => {
                const rowKey = getRowKey(row)
                const isSelected = selectedRowKey === rowKey

                return (
                  <tr
                    key={rowKey}
                    className={`cursor-pointer transition hover:bg-slate-300/80 ${isSelected ? 'bg-slate-300/80' : ''}`}
                    onClick={() => handleRowSelect(row)}
                  >
                    {columns.map((column) => (
                      <td
                        key={column.id}
                        className={`whitespace-nowrap px-4 py-3 text-sm text-slate-700 ${column.cellClassName ?? ''}`}
                      >
                        {column.cell(row)}
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
          {hasSummaryRow ? (
            <tfoot className="border-t border-slate-200 bg-slate-50">
              <tr>
                {columns.map((column) => {
                  const summaryCell = summaryCells.find(
                    (cell) => cell.columnId === column.id,
                  )
                  const content =
                    summaryCell === undefined
                      ? null
                      : typeof summaryCell.content === 'function'
                        ? summaryCell.content(rows)
                        : summaryCell.content

                  return (
                    <td
                      key={column.id}
                      className={`whitespace-nowrap px-4 py-3 text-sm font-semibold text-slate-700 ${column.cellClassName ?? ''} ${summaryCell?.className ?? ''}`}
                    >
                      {content}
                    </td>
                  )
                })}
              </tr>
            </tfoot>
          ) : null}
        </table>
      </div>
    </div>
  )
}
