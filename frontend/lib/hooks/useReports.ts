import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { ReportSummary, WorkloadReport, AuditLog } from '@/lib/types'

export function useReportSummary() {
  return useQuery({
    queryKey: ['reports', 'summary'],
    queryFn: async () => {
      const { data } = await api.get('/api/reports/summary')
      return {
        totalTeachers: data.total_teachers, activeToday: data.active_today,
        totalDuties: data.total_duties, issuesPending: data.issues_pending,
        dutiesCovered: data.duties_covered, substitutionsMade: data.substitutions_made,
        conflictsResolved: data.conflicts_resolved,
      } as ReportSummary
    },
  })
}

export function useWorkloadReport() {
  return useQuery({
    queryKey: ['reports', 'workload'],
    queryFn: async () => {
      const { data } = await api.get('/api/reports/workload')
      return (data as Record<string,unknown>[]).map(d => ({
        teacherId: d.teacher_id, name: d.name, department: d.department,
        dutyCount: d.duty_count, maxDuties: d.max_duties,
        workloadPct: d.workload_pct, absenceCount: d.absence_count, subCount: d.sub_count,
      })) as WorkloadReport[]
    },
  })
}

export function useAbsenceTrend() {
  return useQuery({
    queryKey: ['reports', 'absences'],
    queryFn: async () => {
      const { data } = await api.get('/api/reports/absences')
      return data as { week: string; duties: number; absences: number }[]
    },
  })
}

export function useAuditLog(page = 1) {
  return useQuery({
    queryKey: ['reports', 'audit-log', page],
    queryFn: async () => {
      const { data } = await api.get(`/api/reports/audit-log?page=${page}&limit=10`)
      return { logs: data.logs as AuditLog[], total: data.total as number }
    },
  })
}
