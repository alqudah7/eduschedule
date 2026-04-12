'use client'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import clsx from 'clsx'
import {
  LayoutDashboard, Users, Calendar, ClipboardList, RefreshCcw,
  Bell, BarChart3, Settings, ChevronLeft, ChevronRight,
} from 'lucide-react'
import { Avatar } from '@/components/ui'

const NAV_MAIN = [
  { href: '/dashboard',      label: 'Dashboard',      icon: LayoutDashboard },
  { href: '/teachers',       label: 'Teachers',        icon: Users },
  { href: '/schedule',       label: 'Schedule',        icon: Calendar },
  { href: '/duties',         label: 'Duties',          icon: ClipboardList },
  { href: '/substitutions',  label: 'Substitutions',   icon: RefreshCcw },
]

const NAV_MANAGEMENT = [
  { href: '/alerts',   label: 'Alerts',   icon: Bell,      badge: true },
  { href: '/reports',  label: 'Reports',  icon: BarChart3 },
]

const NAV_SYSTEM = [
  { href: '/settings', label: 'Settings', icon: Settings },
]

type NavItemProps = {
  href: string
  label: string
  icon: React.ElementType
  collapsed: boolean
  badge?: boolean
  alertCount?: number
}

function NavItem({ href, label, icon: Icon, collapsed, badge, alertCount }: NavItemProps) {
  const pathname = usePathname()
  const isActive = pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
  return (
    <Link
      href={href}
      title={collapsed ? label : undefined}
      className={clsx(
        'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all duration-150',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
        isActive
          ? 'bg-primary-50 text-primary-700 font-medium border-l-[3px] border-primary-500 pl-[calc(0.75rem-3px)]'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 border-l-[3px] border-transparent pl-[calc(0.75rem-3px)]',
      )}
    >
      <Icon size={16} className="shrink-0" />
      {!collapsed && <span className="flex-1 truncate">{label}</span>}
      {!collapsed && badge && alertCount && alertCount > 0 ? (
        <span className="bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center font-mono">
          {alertCount > 9 ? '9+' : alertCount}
        </span>
      ) : null}
    </Link>
  )
}

type SidebarProps = { alertCount?: number; user?: { name: string; role: string } | null }

export function Sidebar({ alertCount = 0, user }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 h-screen bg-white border-r border-gray-200 flex flex-col z-30 transition-all duration-200',
        collapsed ? 'w-[60px]' : 'w-60',
      )}
    >
      {/* Logo area */}
      <div className={clsx('flex items-center border-b border-gray-200 shrink-0', collapsed ? 'justify-center px-3 h-16' : 'px-5 h-16')}>
        {/* LOGO PLACEHOLDER — expects ~120px wide × 32px tall asset */}
        {!collapsed && (
          <span className="font-syne font-bold text-base text-gray-900 tracking-tight">EduSchedule</span>
        )}
        {collapsed && <span className="font-syne font-bold text-sm text-primary-600">ES</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-0.5">
        {!collapsed && (
          <p className="text-xs font-mono text-gray-400 uppercase tracking-wider px-3 mb-2">Main</p>
        )}
        {NAV_MAIN.map(item => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}

        {!collapsed && (
          <p className="text-xs font-mono text-gray-400 uppercase tracking-wider px-3 mt-4 mb-2">Management</p>
        )}
        {collapsed && <div className="my-2 border-t border-gray-100" />}
        {NAV_MANAGEMENT.map(item => (
          <NavItem key={item.href} {...item} collapsed={collapsed} alertCount={alertCount} />
        ))}

        {!collapsed && (
          <p className="text-xs font-mono text-gray-400 uppercase tracking-wider px-3 mt-4 mb-2">System</p>
        )}
        {collapsed && <div className="my-2 border-t border-gray-100" />}
        {NAV_SYSTEM.map(item => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}
      </nav>

      {/* User card */}
      {user && !collapsed && (
        <div className="border-t border-gray-200 p-4 shrink-0">
          <div className="flex items-center gap-3">
            <Avatar name={user.name} initials={user.name.slice(0, 2).toUpperCase()} size="sm" index={7} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">{user.name}</p>
              <p className="text-xs text-gray-400 font-mono capitalize">{user.role.toLowerCase()}</p>
            </div>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(c => !c)}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="border-t border-gray-200 py-3 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors shrink-0"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  )
}
