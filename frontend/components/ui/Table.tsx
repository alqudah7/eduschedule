'use client'
import clsx from 'clsx'
import { SkeletonTableRows } from './Skeleton'

type Column<T> = {
  key: string
  header: string
  render?: (row: T) => React.ReactNode
  width?: string
}

type TableProps<T> = {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyState?: React.ReactNode
  onRowClick?: (row: T) => void
  stickyHeader?: boolean
}

export function Table<T extends { id?: string }>({
  columns, data, loading, emptyState, onRowClick, stickyHeader,
}: TableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className={clsx(stickyHeader && 'sticky top-0 z-10')}>
            {columns.map(col => (
              <th
                key={col.key}
                style={col.width ? { width: col.width } : undefined}
                className="px-4 py-3 text-left text-xs font-mono font-medium text-gray-500 uppercase tracking-wide bg-gray-50 border-b border-gray-200"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {loading ? (
            <SkeletonTableRows rows={5} cols={columns.length} />
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>
                {emptyState}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={(row as { id?: string }).id ?? i}
                onClick={() => onRowClick?.(row)}
                className={clsx(
                  'bg-white transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-gray-50',
                )}
              >
                {columns.map(col => (
                  <td key={col.key} className="px-4 py-3 text-gray-700 align-middle">
                    {col.render
                      ? col.render(row)
                      : (row as Record<string, unknown>)[col.key] as React.ReactNode}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
