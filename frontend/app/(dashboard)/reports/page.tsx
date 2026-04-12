'use client'
import { useState } from 'react'
import { Download, FileText, Users, CheckCircle, ClipboardList, AlertTriangle } from 'lucide-react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatCard, Avatar, WorkloadBar, Button, Card } from '@/components/ui'
import { useReportSummary, useWorkloadReport, useAbsenceTrend, useAuditLog } from '@/lib/hooks/useReports'
import { formatRelative } from '@/lib/utils'

export default function ReportsPage() {
  const { data: summary } = useReportSummary()
  const { data: workload = [] } = useWorkloadReport()
  const { data: absences = [] } = useAbsenceTrend()
  const [page, setPage] = useState(1)
  const { data: auditData } = useAuditLog(page)

  function handleExportCsv() {
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/reports/export/csv`
    const token = typeof window !== 'undefined' ? localStorage.getItem('edu_token') : ''
    const a = document.createElement('a')
    a.href = url
    if (token) a.href += `?token=${token}` // fallback
    a.download = 'duties.csv'
    a.click()
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Reports" description="Scheduling analytics and audit trail" />

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Total Duties"       value={summary?.totalDuties ?? 0}       icon={<ClipboardList size={18} className="text-primary-600" />} iconBg="bg-primary-50" accentColor="teal" />
        <StatCard title="Covered"            value={summary?.dutiesCovered ?? 0}     icon={<CheckCircle size={18} className="text-emerald-600" />}  iconBg="bg-emerald-50" accentColor="green" />
        <StatCard title="Substitutions Made" value={summary?.substitutionsMade ?? 0} icon={<Users size={18} className="text-blue-600" />}           iconBg="bg-blue-50"    accentColor="teal" />
        <StatCard title="Issues Pending"     value={summary?.issuesPending ?? 0}     icon={<AlertTriangle size={18} className="text-red-500" />}    iconBg="bg-red-50"     accentColor="red" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-syne font-semibold text-gray-800 mb-4">Duties &amp; Absences by Week</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={absences} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey="week" tick={{ fontSize: 11, fontFamily: 'var(--font-dm-mono)' }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="duties"   fill="#1a9189" name="Duties"   radius={[3,3,0,0]} />
              <Bar dataKey="absences" fill="#e74c3c" name="Absences" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h3 className="text-sm font-syne font-semibold text-gray-800 mb-4">Average Workload Trend</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={workload.slice(0, 8).map((w, i) => ({ name: `T${i+1}`, workload: w.workloadPct }))} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'var(--font-dm-mono)' }} />
              <YAxis tick={{ fontSize: 11 }} unit="%" />
              <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v) => [`${v}%`, 'Workload']} />
              <Line type="monotone" dataKey="workload" stroke="#1a9189" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Workload table */}
      <Card padding="none">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-syne font-semibold text-gray-800">Per-Teacher Workload</h3>
          <Button size="sm" variant="secondary" icon={<Download size={12} />} onClick={handleExportCsv}>Export CSV</Button>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 border-b border-gray-200">
            {['Teacher', 'Department', 'Duties', 'Absences', 'Subs Given', 'Workload'].map(h => (
              <th key={h} className="px-4 py-3 text-left text-xs font-mono text-gray-400 uppercase">{h}</th>
            ))}
          </tr></thead>
          <tbody className="divide-y divide-gray-100">
            {workload.map((row, i) => (
              <tr key={row.teacherId} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Avatar name={row.name} initials={row.name.slice(0,2).toUpperCase()} size="xs" index={i} />
                    <span className="text-xs font-medium text-gray-800">{row.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{row.department}</td>
                <td className="px-4 py-3 text-xs font-mono text-gray-700">{row.dutyCount}/{row.maxDuties}</td>
                <td className="px-4 py-3 text-xs font-mono text-gray-700">{row.absenceCount}</td>
                <td className="px-4 py-3 text-xs font-mono text-gray-700">{row.subCount}</td>
                <td className="px-4 py-3 w-40"><WorkloadBar value={row.workloadPct} size="sm" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Audit trail */}
      <Card padding="none">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-syne font-semibold text-gray-800">Audit Trail</h3>
          <Button size="sm" variant="secondary" icon={<FileText size={12} />} onClick={() => window.print()}>Export PDF</Button>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 border-b border-gray-200">
            {['Timestamp', 'Action', 'Actor', 'Details'].map(h => (
              <th key={h} className="px-4 py-3 text-left text-xs font-mono text-gray-400 uppercase">{h}</th>
            ))}
          </tr></thead>
          <tbody className="divide-y divide-gray-100">
            {(auditData?.logs ?? []).map(log => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-xs font-mono text-gray-400">{formatRelative(log.createdAt)}</td>
                <td className="px-4 py-3 text-xs font-mono text-gray-600">{log.action}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{log.actor}</td>
                <td className="px-4 py-3 text-xs text-gray-700">{log.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {/* Pagination */}
        {(auditData?.total ?? 0) > 10 && (
          <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
            <p className="text-xs text-gray-400 font-mono">Page {page} of {Math.ceil((auditData?.total ?? 0) / 10)}</p>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
              <Button size="sm" variant="secondary" disabled={page >= Math.ceil((auditData?.total ?? 0) / 10)} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
