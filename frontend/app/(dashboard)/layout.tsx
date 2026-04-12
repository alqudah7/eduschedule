'use client'
import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

const PAGE_TITLES: Record<string, string> = {
  '/dashboard':     'Dashboard',
  '/teachers':      'Teachers',
  '/schedule':      'Schedule',
  '/duties':        'Duties',
  '/substitutions': 'Substitutions',
  '/alerts':        'Alerts',
  '/reports':       'Reports',
  '/settings':      'Settings',
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const title = PAGE_TITLES[pathname] ?? PAGE_TITLES[Object.keys(PAGE_TITLES).find(k => pathname.startsWith(k)) ?? ''] ?? 'EduSchedule'

  // Read user from localStorage (set on login)
  const [user, setUser] = useState<{ name: string; role: string } | null>(null)
  useEffect(() => {
    try {
      const stored = localStorage.getItem('edu_user')
      if (stored) setUser(JSON.parse(stored))
    } catch {}
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <Sidebar user={user} alertCount={0} />
        <Topbar title={title} user={user} alertCount={0} />
        <main
          className="pt-[60px] pl-60 min-h-screen transition-all duration-200"
          id="main-content"
        >
          <div className="p-6">{children}</div>
        </main>
      </div>
      <Toaster
        position="top-right"
        toastOptions={{ style: { fontSize: '13px', fontFamily: 'var(--font-dm-sans)' } }}
      />
    </QueryClientProvider>
  )
}
