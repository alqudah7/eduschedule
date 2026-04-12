from app.config import settings


class NotificationService:
    @staticmethod
    def send_substitution_request(
        teacher_email: str, teacher_name: str, duty_name: str, duty_time: str
    ) -> None:
        if not settings.RESEND_API_KEY:
            return
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": "noreply@eduschedule.com",
                "to": teacher_email,
                "subject": f"Substitution Request: {duty_name}",
                "html": (
                    f"<p>Dear {teacher_name},</p>"
                    f"<p>You have been requested to cover <strong>{duty_name}</strong> "
                    f"at {duty_time}. Please log in to EduSchedule to accept or decline.</p>"
                ),
            })
        except Exception:
            pass  # Non-fatal: email is best-effort

    @staticmethod
    def send_conflict_alert(admin_email: str, teacher_name: str, duty_name: str) -> None:
        if not settings.RESEND_API_KEY:
            return
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": "noreply@eduschedule.com",
                "to": admin_email,
                "subject": f"Scheduling Conflict: {duty_name}",
                "html": (
                    f"<p>A scheduling conflict has been detected for "
                    f"<strong>{teacher_name}</strong> on duty <strong>{duty_name}</strong>. "
                    f"Please log in to resolve.</p>"
                ),
            })
        except Exception:
            pass
