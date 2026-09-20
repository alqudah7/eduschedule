from app.models.teacher import User, Teacher
from app.models.duty import Duty
from app.models.lesson import Lesson
from app.models.substitution import Substitution
from app.models.alert import Alert, AuditLog
from app.models.attendance import TeacherAttendance

__all__ = ["User", "Teacher", "Duty", "Lesson", "Substitution",
           "Alert", "AuditLog", "TeacherAttendance"]
