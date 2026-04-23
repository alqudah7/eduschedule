export type Role = 'ADMIN' | 'MANAGER' | 'TEACHER'
export type TeacherStatus = 'ACTIVE' | 'ABSENT' | 'ON_LEAVE' | 'INACTIVE'
export type DutyType = 'SUPERVISION' | 'EXTRACURRICULAR' | 'EXAM' | 'LIBRARY' | 'SPORTS' | 'MORNING_SUPERVISION' | 'LUNCH_SUPERVISION' | 'EXAM_DUTY' | 'LAB_SUPERVISION' | 'SPORTS_SUPERVISION' | 'DISMISSAL_DUTY'
export type DutyCategory = 'ARRIVAL' | 'DISMISSAL' | 'BREAK' | 'CLASS_COVER' | 'SUPERVISION' | 'EXAM' | 'LIBRARY' | 'SPORTS'
export type DutyStatus = 'CONFIRMED' | 'SUBSTITUTE_NEEDED' | 'CONFLICT' | 'UNASSIGNED' | 'CANCELLED'
export type WeekDay = 'SUN' | 'MON' | 'TUE' | 'WED' | 'THU' | 'SUNDAY' | 'MONDAY' | 'TUESDAY' | 'WEDNESDAY' | 'THURSDAY'
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
export type SubStatus = 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'CANCELLED'
export type SchoolLevel = 'ELEMENTARY' | 'MIDDLE' | 'HIGH' | 'ALL'

export interface User { id: string; email: string; name: string; role: Role }

export interface Teacher {
  id: string; name: string; initials: string; department: string; email: string
  phone?: string; status: TeacherStatus; maxDuties: number
  qualifications: string[]; subjects: string[]
  schoolLevel: SchoolLevel
  dutyCount: number; workloadPct: number; createdAt: string; updatedAt?: string
}

export interface Duty {
  id: string; name: string; type: DutyType; day: WeekDay
  startTime: string; endTime: string; location: string
  teacherId?: string; teacher?: Partial<Teacher>; status: DutyStatus
  dutyCategory: DutyCategory
  notes?: string; createdAt: string; updatedAt?: string
}

export interface Lesson {
  id: string; teacherId: string; subject: string; class: string
  room: string; day: WeekDay; startTime: string; endTime: string
  schoolLevel: SchoolLevel
}

export interface Substitution {
  id: string; dutyId: string; duty?: Partial<Duty>
  absentTeacherId: string; absentTeacher?: Partial<Teacher>
  substituteId?: string; substitute?: Partial<Teacher>
  status: SubStatus; requestedAt: string; resolvedAt?: string; notes?: string
}

export interface SubstituteSuggestion {
  teacher: Partial<Teacher> & { id: string; name: string; initials: string }
  loadPct: number
  score: number
  tier: 0 | 1 | 2 | 3
  tierLabel: string
  subjectMatch: boolean
  levelMatch: boolean
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

export type AttendanceStatus = 'present' | 'absent' | 'late'

export interface TeacherAttendanceRow {
  teacher_id: string
  name: string
  initials: string
  department: string
  subjects: string[]
  attendance_id: string | null
  status: AttendanceStatus | null
  note: string | null
}

export interface AttendanceSummary {
  date: string
  total: number
  present: number
  absent: number
  late: number
  unmarked: number
}
