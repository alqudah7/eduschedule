import type { WeekDay, DutyType, Severity } from './types'

export const DAYS: { key: WeekDay; label: string; short: string }[] = [
  { key: 'MON', label: 'Monday',    short: 'Mon' },
  { key: 'TUE', label: 'Tuesday',   short: 'Tue' },
  { key: 'WED', label: 'Wednesday', short: 'Wed' },
  { key: 'THU', label: 'Thursday',  short: 'Thu' },
  { key: 'FRI', label: 'Friday',    short: 'Fri' },
]

export const TIME_SLOTS = [
  '07:00', '07:45', '08:30', '09:15', '10:00', '10:45',
  '11:30', '12:15', '13:00', '13:45', '14:30', '15:15',
]

export const DUTY_TYPE_CONFIG: Record<DutyType, { label: string; color: string }> = {
  SUPERVISION:        { label: 'Supervision',        color: 'blue'   },
  EXTRACURRICULAR:    { label: 'Extracurricular',    color: 'purple' },
  EXAM:               { label: 'Exam',               color: 'amber'  },
  LIBRARY:            { label: 'Library',            color: 'green'  },
  SPORTS:             { label: 'Sports',             color: 'orange' },
  MORNING_SUPERVISION:{ label: 'Morning Supervision',color: 'blue'   },
  LUNCH_SUPERVISION:  { label: 'Lunch Supervision',  color: 'teal'   },
  EXAM_DUTY:          { label: 'Exam Duty',          color: 'amber'  },
  LAB_SUPERVISION:    { label: 'Lab Supervision',    color: 'green'  },
  SPORTS_SUPERVISION: { label: 'Sports Supervision', color: 'orange' },
  DISMISSAL_DUTY:     { label: 'Dismissal Duty',     color: 'purple' },
}

export const QUALIFICATIONS = ['general', 'lab', 'sports', 'library', 'exam']

export const SEVERITY_CONFIG: Record<Severity, { colorClass: string; bgClass: string; borderClass: string; label: string }> = {
  CRITICAL: { colorClass: 'text-red-700',     bgClass: 'bg-red-50',     borderClass: 'border-red-200',    label: 'Critical' },
  HIGH:     { colorClass: 'text-amber-700',   bgClass: 'bg-amber-50',   borderClass: 'border-amber-200',  label: 'High' },
  MEDIUM:   { colorClass: 'text-blue-700',    bgClass: 'bg-blue-50',    borderClass: 'border-blue-200',   label: 'Medium' },
  LOW:      { colorClass: 'text-gray-700',    bgClass: 'bg-gray-50',    borderClass: 'border-gray-200',   label: 'Low' },
  INFO:     { colorClass: 'text-primary-700', bgClass: 'bg-primary-50', borderClass: 'border-primary-200',label: 'Info' },
}

export const STATUS_BADGE: Record<string, string> = {
  ACTIVE:            'teal',
  ABSENT:            'red',
  ON_LEAVE:          'amber',
  INACTIVE:          'gray',
  CONFIRMED:         'green',
  SUBSTITUTE_NEEDED: 'amber',
  CONFLICT:          'red',
  UNASSIGNED:        'gray',
  CANCELLED:         'gray',
  PENDING:           'amber',
  ACCEPTED:          'green',
  DECLINED:          'red',
}
