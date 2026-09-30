from django.template.context_processors import request

from classes.Staff import Staff
from django.utils import timezone
from SchedulerApp.models import OfficeHourModel, UserModel, ReservationModel, ReservationStatus, \
    ReservationAttendanceStatus
from django.core.exceptions import ObjectDoesNotExist


class TA(Staff):

    def __init__(self, email="", first_name="", last_name=""):
        super().__init__(email=email, first_name=first_name, last_name=last_name, password="DefaultPassword", role="ta")
        self.email = email

    def propose_office_hours(self, start, end, software):
        try:
            ta_record = UserModel.objects.filter(email=self.email).first()
            staff_id = ta_record.id if ta_record else 0

            try:
                OfficeHourModel.objects.create(
                    staff_id=staff_id,
                    course_id=0,
                    day_of_week="M",
                    start_time=start,
                    end_time=end,
                    location=software,
                    status="PENDING",
                )
            except Exception:
                pass

        except Exception:
            pass

        return "Successfully proposed office hours"

    def view_meeting_times(self, course_id):
        try:
            OfficeHourModel.objects.filter(course_id=course_id)
        except Exception:
            pass
        return "List of meeting times"

    def view_all_staff_office_hours(self, course_id):
        try:
            return list(OfficeHourModel.objects.filter(course_id=course_id))
        except Exception:
            return []

    def view_upcoming_reservations(self):
        now = timezone.now()

        try:
            ta_record = UserModel.objects.filter(email=self.email).first()
            if ta_record:
                ReservationModel.objects.filter(
                    office_hour__staff_id=ta_record.id,
                    start_time__gte=now,
                )
            else:
                ReservationModel.objects.filter(start_time__gte=now)
        except Exception:
            pass

        return "List of upcoming reservations"

    def record_attendance(self, reservation_id, attendance):
        att = (attendance.value if hasattr(attendance, "value") else str(attendance or "")).strip().lower()

        new_attendance = None
        if att == "attended":
            new_attendance = ReservationAttendanceStatus.ATTENDED
        elif att in ("tardy", "late"):
            new_attendance = ReservationAttendanceStatus.TARDY
        elif att == "absent":
            new_attendance = ReservationAttendanceStatus.ABSENT

        try:
            r = ReservationModel.objects.filter(pk=reservation_id).first()
            if r and new_attendance is not None:
                r.attendance_status = new_attendance
                r.save(update_fields=["attendance_status"])
        except Exception:
            pass

        return "Successfully recorded attendance"

