'use client'
import { useState } from 'react'
import { Bell, ChevronDown, LogOut } from 'lucide-react'
import { Avatar } from '@/components/ui'
import clsx from 'clsx'

type TopbarProps = {
  title: string
  alertCount?: number
  user?: { name: string; role: string } | null
}

export function Topbar({ title, alertCount = 0, user }: TopbarProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const today = new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <header className="fixed top-0 right-0 left-0 h-[60px] bg-white border-b border-gray-200 z-20 flex items-center px-6 gap-4">
      <div className="flex-1">
        <h1 className="text-lg font-syne font-bold text-gray-900">{title}</h1>
      </div>

      <span className="text-xs font-mono text-gray-600 hidden md:block">{today}</span>

      {/* Alert bell */}
      <button className="relative p-2 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors" aria-label={`${alertCount} alerts`}>
        <Bell size={16} />
        {alertCount > 0 && (
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        )}
      </button>

      {/* User dropdown */}
      {user && (
        <div className="relative">
          <button
            onClick={() => setMenuOpen(o => !o)}
            className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-gray-50 transition-colors"
            aria-label="User menu"
          >
            <Avatar name={user.name} initials={user.name.slice(0, 2).toUpperCase()} size="xs" index={7} />
            <span className="text-xs font-medium text-gray-700 hidden md:block max-w-24 truncate">{user.name}</span>
            <ChevronDown size={12} className="text-gray-500" />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-md z-50 py-1">
                <div className="px-3 py-2 border-b border-gray-100">
                  <p className="text-xs font-medium text-gray-900 truncate">{user.name}</p>
                  <p className="text-xs text-gray-600 font-mono capitalize">{user.role.toLowerCase()}</p>
                </div>
                <button
                  onClick={() => { setMenuOpen(false); window.location.href = '/login' }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  )
}
