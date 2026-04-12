export type Role = 'ADMIN' | 'MANAGER' | 'TEACHER'
export type TeacherStatus = 'ACTIVE' | 'ABSENT' | 'ON_LEAVE' | 'INACTIVE'
export type DutyType = 'SUPERVISION' | 'EXTRACURRICULAR' | 'EXAM' | 'LIBRARY' | 'SPORTS'
export type DutyStatus = 'CONFIRMED' | 'SUBSTITUTE_NEEDED' | 'CONFLICT' | 'UNASSIGNED' | 'CANCELLED'
export type WeekDay = 'MON' | 'TUE' | 'WED' | 'THU' | 'FRI'
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
export type SubStatus = 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'CANCELLED'

export interface User { id: string; email: string; name: string; role: Role }

export interface Teacher {
  id: string; name: string; initials: string; department: string; email: string
  phone?: string; status: TeacherStatus; maxDuties: number
  qualifications: string[]; subjects: string[]
  dutyCount: number; workloadPct: number; createdAt: string; updatedAt?: string
}

export interface Duty {
  id: string; name: string; type: DutyType; day: WeekDay
  startTime: string; endTime: string; location: string
  teacherId?: string; teacher?: Partial<Teacher>; status: DutyStatus
  notes?: string; createdAt: string; updatedAt?: string
}

export interface Lesson {
  id: string; teacherId: string; subject: string; class: string
  room: string; day: WeekDay; startTime: string; endTime: string
}

export interface Substitution {
  id: string; dutyId: string; duty?: Partial<Duty>
  absentTeacherId: string; absentTeacher?: Partial<Teacher>
  substituteId?: string; substitute?: Partial<Teacher>
  status: SubStatus; requestedAt: string; resolvedAt?: string; notes?: string
}

export interface SubstituteSuggestion {
  teacher: Partial<Teacher> & { id: string; name: string; initials: string }
  loadPct: number; score: number
}

export interface Alert {
  id: string; severity: Severity; title: string; message: string
  dutyId?: string; duty?: Partial<Duty>; resolved: boolean; createdAt: string
}

export interface AlertSummary {
  critical: number; high: number; medium: number; low: number; info: number; total: number
}

export interface ScheduleCell {
  type: 'lesson' | 'duty' | 'conflict' | 'free'
  lesson?: Partial<Lesson>; duty?: Partial<Duty>
}

export type WeekGrid = Record<WeekDay, Record<string, ScheduleCell>>

export interface ReportSummary {
  totalTeachers: number; activeToday: number; totalDuties: number
  issuesPending: number; dutiesCovered: number; substitutionsMade: number; conflictsResolved: number
}

export interface WorkloadReport {
  teacherId: string; name: string; department: string
  dutyCount: number; maxDuties: number; workloadPct: number
  absenceCount: number; subCount: number
}

export interface AuditLog {
  id: string; action: string; actor: string; details: string; createdAt: string
}

export type BadgeVariant = 'teal' | 'green' | 'amber' | 'red' | 'blue' | 'gray' | 'purple' | 'orange'
