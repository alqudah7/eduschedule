import { PrismaClient } from '@prisma/client'
import { PrismaPg } from '@prisma/adapter-pg'
import * as crypto from 'crypto'
import bcrypt from 'bcryptjs'

const adapter = new PrismaPg(process.env.DATABASE_URL ?? 'postgresql://localhost:5432/eduschedule')
const prisma = new PrismaClient({ adapter })

function cuid() {
  return 'c' + crypto.randomBytes(8).toString('hex')
}

async function main() {
  console.log('Seeding EduSchedule...')

  const adminPw = await bcrypt.hash('Admin@123', 10)
  const teacherPw = await bcrypt.hash('Teacher@123', 10)

  // Clean existing data in FK-safe order
  await prisma.auditLog.deleteMany()
  await prisma.alert.deleteMany()
  await prisma.substitution.deleteMany()
  await prisma.absence.deleteMany()
  await prisma.lesson.deleteMany()
  await prisma.duty.deleteMany()
  await prisma.teacher.deleteMany()
  await prisma.user.deleteMany()

  // Admin user
  const adminUser = await prisma.user.create({
    data: {
      id: cuid(), email: 'admin@eduschedule.com',
      password: adminPw,
      name: 'Admin User', role: 'ADMIN',
    },
  })

  await prisma.teacher.create({
    data: {
      id: cuid(), userId: adminUser.id, name: 'Admin User', initials: 'AU',
      department: 'Administration', email: 'admin@eduschedule.com',
      status: 'ACTIVE', maxDuties: 0, qualifications: ['general'], subjects: [],
    },
  })

  // 8 teachers
  const teacherData = [
    { name: 'Dr. Sarah Al-Rashid',   initials: 'SR', dept: 'Mathematics',   email: 'sarah@eduschedule.com',   status: 'ACTIVE',   quals: ['general','lab','exam'],        subjects: ['Calculus','Algebra'] },
    { name: 'Mr. James Thornton',    initials: 'JT', dept: 'Science',        email: 'james@eduschedule.com',   status: 'ABSENT',   quals: ['general','lab'],               subjects: ['Physics','Chemistry'] },
    { name: 'Ms. Aisha Al-Mansoori', initials: 'AA', dept: 'English',        email: 'aisha@eduschedule.com',   status: 'ACTIVE',   quals: ['general','library'],           subjects: ['Literature','Writing'] },
    { name: 'Mr. Carlos Rivera',     initials: 'CR', dept: 'History',        email: 'carlos@eduschedule.com',  status: 'ACTIVE',   quals: ['general','sports'],            subjects: ['World History','Civics'] },
    { name: 'Ms. Priya Nair',        initials: 'PN', dept: 'Computer Sci.',  email: 'priya@eduschedule.com',   status: 'ACTIVE',   quals: ['general','lab'],               subjects: ['Programming','Robotics'] },
    { name: 'Mr. Omar Hassan',       initials: 'OH', dept: 'Physical Ed.',   email: 'omar@eduschedule.com',    status: 'ON_LEAVE', quals: ['general','sports'],            subjects: ['PE','Health'] },
    { name: 'Ms. Fatima Al-Zahra',   initials: 'FA', dept: 'Mathematics',    email: 'fatima@eduschedule.com',  status: 'ACTIVE',   quals: ['general','exam','lab'],        subjects: ['Statistics','Geometry'] },
    { name: 'Mr. David Kim',         initials: 'DK', dept: 'Science',        email: 'david@eduschedule.com',   status: 'ACTIVE',   quals: ['general','lab','sports'],      subjects: ['Biology','Environmental Sci'] },
  ]

  const teachers: Record<string, string> = {}

  for (const t of teacherData) {
    const userId = cuid()
    const teacherId = cuid()
    teachers[t.name] = teacherId
    await prisma.user.create({
      data: { id: userId, email: t.email, password: teacherPw, name: t.name, role: 'TEACHER' },
    })
    await prisma.teacher.create({
      data: {
        id: teacherId, userId, name: t.name, initials: t.initials, department: t.dept,
        email: t.email, status: t.status as any, maxDuties: 16,
        qualifications: t.quals, subjects: t.subjects,
      },
    })
  }

  const sarahId  = teachers['Dr. Sarah Al-Rashid']
  const jamesId  = teachers['Mr. James Thornton']
  const aishaId  = teachers['Ms. Aisha Al-Mansoori']
  const carlosId = teachers['Mr. Carlos Rivera']
  const priyaId  = teachers['Ms. Priya Nair']
  const fatimaId = teachers['Ms. Fatima Al-Zahra']
  const davidId  = teachers['Mr. David Kim']

  // 30 lessons
  const lessonsData = [
    { tId: sarahId,  subject: 'Calculus',        class_: 'G12A', room: 'A101',    day: 'MON', s: '08:30', e: '09:15' },
    { tId: sarahId,  subject: 'Algebra',          class_: 'G11B', room: 'A102',    day: 'WED', s: '10:00', e: '10:45' },
    { tId: sarahId,  subject: 'Calculus',         class_: 'G12A', room: 'A101',    day: 'FRI', s: '09:00', e: '09:45' },
    { tId: sarahId,  subject: 'Algebra',          class_: 'G10A', room: 'A103',    day: 'THU', s: '11:30', e: '12:15' },
    { tId: jamesId,  subject: 'Physics',          class_: 'G11A', room: 'Lab-B1',  day: 'MON', s: '09:15', e: '10:00' },
    { tId: jamesId,  subject: 'Chemistry',        class_: 'G10B', room: 'Lab-B2',  day: 'TUE', s: '10:00', e: '10:45' },
    { tId: jamesId,  subject: 'Physics',          class_: 'G12B', room: 'Lab-B1',  day: 'THU', s: '08:30', e: '09:15' },
    { tId: aishaId,  subject: 'Literature',       class_: 'G11A', room: 'B201',    day: 'MON', s: '10:45', e: '11:30' },
    { tId: aishaId,  subject: 'Writing',          class_: 'G10A', room: 'B202',    day: 'WED', s: '08:30', e: '09:15' },
    { tId: aishaId,  subject: 'Literature',       class_: 'G12B', room: 'B203',    day: 'FRI', s: '10:00', e: '10:45' },
    { tId: carlosId, subject: 'World History',    class_: 'G10B', room: 'C101',    day: 'TUE', s: '09:15', e: '10:00' },
    { tId: carlosId, subject: 'Civics',           class_: 'G11B', room: 'C102',    day: 'THU', s: '10:00', e: '10:45' },
    { tId: carlosId, subject: 'World History',    class_: 'G12A', room: 'C103',    day: 'FRI', s: '11:30', e: '12:15' },
    { tId: priyaId,  subject: 'Programming',      class_: 'G11A', room: 'Lab-C1',  day: 'MON', s: '07:45', e: '08:30' },
    { tId: priyaId,  subject: 'Robotics',         class_: 'G12A', room: 'Lab-C2',  day: 'WED', s: '13:00', e: '13:45' },
    { tId: priyaId,  subject: 'Programming',      class_: 'G10B', room: 'Lab-C1',  day: 'FRI', s: '08:30', e: '09:15' },
    { tId: priyaId,  subject: 'Robotics',         class_: 'G11B', room: 'Lab-C2',  day: 'FRI', s: '09:15', e: '10:00' },
    { tId: fatimaId, subject: 'Statistics',       class_: 'G12B', room: 'A104',    day: 'TUE', s: '08:30', e: '09:15' },
    { tId: fatimaId, subject: 'Geometry',         class_: 'G10A', room: 'A105',    day: 'THU', s: '09:15', e: '10:00' },
    { tId: fatimaId, subject: 'Statistics',       class_: 'G11A', room: 'A106',    day: 'FRI', s: '10:00', e: '10:45' },
    { tId: davidId,  subject: 'Biology',          class_: 'G10A', room: 'Lab-D1',  day: 'MON', s: '11:30', e: '12:15' },
    { tId: davidId,  subject: 'Environmental Sci',class_: 'G11B', room: 'Lab-D2',  day: 'TUE', s: '11:30', e: '12:15' },
    { tId: davidId,  subject: 'Biology',          class_: 'G12A', room: 'Lab-D1',  day: 'WED', s: '09:15', e: '10:00' },
    { tId: davidId,  subject: 'Environmental Sci',class_: 'G10B', room: 'Lab-D2',  day: 'FRI', s: '13:00', e: '13:45' },
    { tId: sarahId,  subject: 'Calculus',         class_: 'G11A', room: 'A101',    day: 'TUE', s: '07:45', e: '08:30' },
    { tId: aishaId,  subject: 'Writing',          class_: 'G11B', room: 'B204',    day: 'TUE', s: '13:00', e: '13:45' },
    { tId: carlosId, subject: 'Civics',           class_: 'G10A', room: 'C104',    day: 'MON', s: '13:00', e: '13:45' },
    { tId: fatimaId, subject: 'Geometry',         class_: 'G12A', room: 'A107',    day: 'WED', s: '11:30', e: '12:15' },
    { tId: davidId,  subject: 'Biology',          class_: 'G11A', room: 'Lab-D1',  day: 'THU', s: '11:30', e: '12:15' },
    { tId: priyaId,  subject: 'Programming',      class_: 'G12B', room: 'Lab-C1',  day: 'THU', s: '13:00', e: '13:45' },
  ]

  for (const l of lessonsData) {
    await prisma.lesson.create({
      data: { id: cuid(), teacherId: l.tId, subject: l.subject, class: l.class_, room: l.room, day: l.day as any, startTime: l.s, endTime: l.e },
    })
  }

  // Duties — conflicts first so we have the IDs
  const conflictDutyId     = cuid()
  const priyaConflictDutyId = cuid()
  const jamesLunchDutyId   = cuid()

  await prisma.duty.create({ data: { id: conflictDutyId,      name: 'Exam Hall Invigilation',      type: 'EXAM',       day: 'FRI', startTime: '09:00', endTime: '12:00', location: 'Hall A',     teacherId: sarahId, status: 'CONFLICT' } })
  await prisma.duty.create({ data: { id: priyaConflictDutyId, name: 'Robotics Exam Invigilation',  type: 'EXAM',       day: 'FRI', startTime: '09:00', endTime: '10:00', location: 'Lab-C1',    teacherId: priyaId, status: 'CONFLICT' } })
  await prisma.duty.create({ data: { id: jamesLunchDutyId,    name: 'Lunch Break Supervision',     type: 'SUPERVISION',day: 'MON', startTime: '12:30', endTime: '13:15', location: 'Cafeteria', teacherId: jamesId, status: 'SUBSTITUTE_NEEDED' } })

  const otherDuties = [
    { name: 'Morning Gate Duty',   type: 'SUPERVISION',    day: 'MON', s: '07:00', e: '07:45', loc: 'Main Gate',    tId: carlosId },
    { name: 'Morning Gate Duty',   type: 'SUPERVISION',    day: 'TUE', s: '07:00', e: '07:45', loc: 'Main Gate',    tId: fatimaId },
    { name: 'Morning Gate Duty',   type: 'SUPERVISION',    day: 'WED', s: '07:00', e: '07:45', loc: 'Main Gate',    tId: davidId  },
    { name: 'Morning Gate Duty',   type: 'SUPERVISION',    day: 'THU', s: '07:00', e: '07:45', loc: 'Main Gate',    tId: aishaId  },
    { name: 'Afternoon Gate',      type: 'SUPERVISION',    day: 'FRI', s: '14:30', e: '15:15', loc: 'Main Gate',    tId: carlosId },
    { name: 'Robotics Club',       type: 'EXTRACURRICULAR',day: 'TUE', s: '15:15', e: '16:00', loc: 'Lab-C2',       tId: priyaId  },
    { name: 'Library Reading',     type: 'EXTRACURRICULAR',day: 'WED', s: '12:15', e: '13:00', loc: 'Library',      tId: aishaId  },
    { name: 'Sports Practice',     type: 'SPORTS',         day: 'FRI', s: '14:30', e: '15:30', loc: 'Sports Field', tId: davidId  },
    { name: 'Drama Club',          type: 'EXTRACURRICULAR',day: 'THU', s: '15:15', e: '16:00', loc: 'Auditorium',   tId: aishaId  },
    { name: 'Exam Invigilation',   type: 'EXAM',           day: 'MON', s: '09:00', e: '11:00', loc: 'Hall B',       tId: fatimaId },
    { name: 'Exam Invigilation',   type: 'EXAM',           day: 'WED', s: '09:00', e: '11:00', loc: 'Hall C',       tId: davidId  },
    { name: 'Library Shift',       type: 'LIBRARY',        day: 'MON', s: '11:30', e: '12:15', loc: 'Library',      tId: sarahId  },
    { name: 'Library Shift',       type: 'LIBRARY',        day: 'TUE', s: '11:30', e: '12:15', loc: 'Library',      tId: carlosId },
    { name: 'Library Shift',       type: 'LIBRARY',        day: 'THU', s: '11:30', e: '12:15', loc: 'Library',      tId: fatimaId },
    { name: 'PE Duty',             type: 'SPORTS',         day: 'MON', s: '14:30', e: '15:30', loc: 'Gym',          tId: carlosId },
    { name: 'PE Duty',             type: 'SPORTS',         day: 'WED', s: '14:30', e: '15:30', loc: 'Gym',          tId: davidId  },
    { name: 'Basketball Practice', type: 'SPORTS',         day: 'THU', s: '14:30', e: '15:30', loc: 'Court',        tId: carlosId },
  ]

  for (const d of otherDuties) {
    await prisma.duty.create({ data: { id: cuid(), name: d.name, type: d.type as any, day: d.day as any, startTime: d.s, endTime: d.e, location: d.loc, teacherId: d.tId, status: 'CONFIRMED' } })
  }

  // 3 alerts
  await prisma.alert.create({ data: { id: cuid(), severity: 'CRITICAL', title: 'Scheduling Conflict: Exam Hall Invigilation',  message: "Dr. Sarah Al-Rashid's Exam Hall Invigilation (FRI 09:00–12:00) conflicts with Calculus G12A (FRI 09:00–09:45)",         dutyId: conflictDutyId,      resolved: false } })
  await prisma.alert.create({ data: { id: cuid(), severity: 'HIGH',     title: 'Scheduling Conflict: Robotics Exam',           message: "Ms. Priya Nair's Robotics Exam Invigilation (FRI 09:00–10:00) conflicts with Robotics G11B lesson (FRI 09:15–10:00)", dutyId: priyaConflictDutyId, resolved: false } })
  await prisma.alert.create({ data: { id: cuid(), severity: 'MEDIUM',   title: 'High Workload Warning',                        message: 'Ms. Aisha Al-Mansoori is approaching maximum duty load. Review assignments.',                                                              resolved: false } })

  // 1 open substitution for James's Lunch duty
  await prisma.substitution.create({
    data: { id: cuid(), dutyId: jamesLunchDutyId, absentTeacherId: jamesId, substituteId: null, status: 'PENDING' },
  })

  // Absence record for James
  await prisma.absence.create({ data: { id: cuid(), teacherId: jamesId, date: new Date(), reason: 'Sick leave' } })

  // 5 audit log entries
  await prisma.auditLog.create({ data: { id: cuid(), action: 'CONFLICT_DETECTED', actor: 'system',                  details: 'Conflict detected: Dr. Sarah Al-Rashid — Exam Hall Invigilation FRI' } })
  await prisma.auditLog.create({ data: { id: cuid(), action: 'MARK_ABSENT',       actor: 'admin@eduschedule.com',  details: 'Mr. James Thornton marked absent' } })
  await prisma.auditLog.create({ data: { id: cuid(), action: 'DUTY_CONFIRMED',    actor: 'admin@eduschedule.com',  details: 'Ms. Priya Nair confirmed for Robotics Club' } })
  await prisma.auditLog.create({ data: { id: cuid(), action: 'CREATE_DUTY',       actor: 'admin@eduschedule.com',  details: 'Afternoon Gate duty created for Friday' } })
  await prisma.auditLog.create({ data: { id: cuid(), action: 'CREATE_SUB_REQUEST',actor: 'system',                  details: "Sub request opened for Mr. James Thornton's Lunch Break Supervision" } })

  console.log('✅ Created admin user')
  console.log('✅ Created 8 teachers')
  console.log('✅ Created 30 lessons')
  console.log('✅ Created 20 duties')
  console.log('✅ Created 3 alerts (2 conflicts + 1 workload warning)')
  console.log('✅ Created 1 substitution request (James Thornton)')
  console.log('✅ Created 5 audit log entries')
  console.log('')
  console.log('🎉 Seed complete!')
  console.log('   Login: admin@eduschedule.com / Admin@123')
}

main().catch(e => { console.error(e); process.exit(1) }).finally(() => prisma.$disconnect())
