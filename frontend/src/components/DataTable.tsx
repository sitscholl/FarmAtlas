import { useMemo, useState, type ReactNode } from 'react'
import { FiChevronDown, FiChevronUp } from 'react-icons/fi'

type DataTableSortDirection = 'asc' | 'desc'
type DataTableSortValue = string | number | boolean | Date | null | undefined

export type DataTableColumn<Row> = {
  id: string
  header: string
  cell: (row: Row) => ReactNode
  sortValue?: (row: Row) => DataTableSortValue
  sortable?: boolean
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

function getDefaultSortValue<Row>(row: Row, columnId: string): DataTableSortValue {
  if (row === null || typeof row !== 'object') {
    return null
  }

  const value = (row as Record<string, unknown>)[columnId]
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean' ||
    value instanceof Date ||
    value === null ||
    value === undefined
  ) {
    return value
  }

  return null
}

function extractTextFromNode(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number' || typeof node === 'bigint') {
    return String(node)
  }
  if (Array.isArray(node)) {
    return node.map(extractTextFromNode).join(' ')
  }
  if (node !== null && typeof node === 'object' && 'props' in node) {
    const props = node.props as { children?: ReactNode }
    return props.children === undefined ? '' : extractTextFromNode(props.children)
  }
  return ''
}

function getColumnSortValue<Row>(column: DataTableColumn<Row>, row: Row): DataTableSortValue {
  const explicitValue = column.sortValue?.(row)
  if (explicitValue !== null && explicitValue !== undefined) {
    return explicitValue
  }

  const defaultValue = getDefaultSortValue(row, column.id)
  if (defaultValue !== null && defaultValue !== undefined) {
    return defaultValue
  }

  return extractTextFromNode(column.cell(row)).trim() || null
}

function compareSortValues(left: DataTableSortValue, right: DataTableSortValue) {
  if (left === null || left === undefined) {
    return right === null || right === undefined ? 0 : 1
  }
  if (right === null || right === undefined) {
    return -1
  }

  if (left instanceof Date || right instanceof Date) {
    const leftTime = left instanceof Date ? left.getTime() : new Date(String(left)).getTime()
    const rightTime = right instanceof Date ? right.getTime() : new Date(String(right)).getTime()
    return leftTime - rightTime
  }

  if (typeof left === 'number' && typeof right === 'number') {
    return left - right
  }

  if (typeof left === 'boolean' && typeof right === 'boolean') {
    return Number(left) - Number(right)
  }

  return String(left).localeCompare(String(right), 'de-DE', {
    numeric: true,
    sensitivity: 'base',
  })
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
  const [sortState, setSortState] = useState<{
    columnId: string
    direction: DataTableSortDirection
  } | null>(null)
  const [uncontrolledSelectedRowKey, setUncontrolledSelectedRowKey] = useState<
    string | number | null
  >(null)
  const candidateSelectedRowKey =
    controlledSelectedRowKey !== undefined
      ? controlledSelectedRowKey
      : uncontrolledSelectedRowKey
  const selectedRowKey =
    candidateSelectedRowKey !== null && rows.some((row) => getRowKey(row) === candidateSelectedRowKey)
      ? candidateSelectedRowKey
      : null

  const sortedRows = useMemo(() => {
    if (sortState === null) {
      return rows
    }

    const column = columns.find((candidate) => candidate.id === sortState.columnId)
    if (column === undefined || column.sortable === false) {
      return rows
    }

    const directionMultiplier = sortState.direction === 'asc' ? 1 : -1
    return rows
      .map((row, index) => ({ row, index }))
      .sort((left, right) => {
        const leftValue = getColumnSortValue(column, left.row)
        const rightValue = getColumnSortValue(column, right.row)
        const leftMissing = leftValue === null || leftValue === undefined
        const rightMissing = rightValue === null || rightValue === undefined
        if (leftMissing || rightMissing) {
          if (leftMissing && rightMissing) {
            return left.index - right.index
          }
          return leftMissing ? 1 : -1
        }
        const comparison = compareSortValues(leftValue, rightValue)
        return comparison === 0
          ? left.index - right.index
          : comparison * directionMultiplier
      })
      .map((entry) => entry.row)
  }, [columns, rows, sortState])

  const handleSort = (column: DataTableColumn<Row>) => {
    if (column.sortable === false) {
      return
    }

    setSortState((current) => {
      if (current?.columnId === column.id) {
        return {
          columnId: column.id,
          direction: current.direction === 'asc' ? 'desc' : 'asc',
        }
      }

      return { columnId: column.id, direction: 'asc' }
    })
  }

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
              {columns.map((column) => {
                const isSorted = sortState?.columnId === column.id
                const sortDirection = isSorted ? sortState.direction : undefined
                return (
                  <th
                    key={column.id}
                    scope="col"
                    aria-sort={
                      sortDirection === undefined
                        ? 'none'
                        : sortDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                    }
                    className={`whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 ${column.headerClassName ?? ''}`}
                  >
                    {column.sortable === false ? (
                      column.header
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleSort(column)}
                        className="inline-flex items-center gap-1 text-inherit transition hover:text-slate-900"
                      >
                        <span>{column.header}</span>
                        <span className="inline-flex h-4 w-4 items-center justify-center">
                          {isSorted ? (
                            sortDirection === 'asc' ? (
                              <FiChevronUp aria-hidden="true" />
                            ) : (
                              <FiChevronDown aria-hidden="true" />
                            )
                          ) : null}
                        </span>
                      </button>
                    )}
                  </th>
                )
              })}
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
              sortedRows.map((row) => {
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
                        ? summaryCell.content(sortedRows)
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
