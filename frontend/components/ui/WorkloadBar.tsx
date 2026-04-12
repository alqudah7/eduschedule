'use client'
import { useEffect, useState } from 'react'
import clsx from 'clsx'

type WorkloadBarProps = {
  value: number
  max?: number
  showLabel?: boolean
  size?: 'sm' | 'md'
}

function getColor(pct: number) {
  if (pct <= 60) return 'bg-emerald-500'
  if (pct <= 85) return 'bg-amber-500'
  return 'bg-red-500'
}

export function WorkloadBar({ value, max = 100, showLabel = true, size = 'md' }: WorkloadBarProps) {
  const [width, setWidth] = useState(0)
  const pct = Math.min(100, Math.round((value / max) * 100))

  useEffect(() => {
    const t = setTimeout(() => setWidth(pct), 50)
    return () => clearTimeout(t)
  }, [pct])

  return (
    <div className="flex items-center gap-2">
      <div className={clsx('flex-1 bg-gray-200 rounded-full overflow-hidden', size === 'sm' ? 'h-1.5' : 'h-2')}>
        <div
          className={clsx('rounded-full transition-all duration-500 ease-out', getColor(pct))}
          style={{ width: `${width}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono text-gray-500 w-9 text-right shrink-0">{pct}%</span>
      )}
    </div>
  )
}
