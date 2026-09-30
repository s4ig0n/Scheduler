from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db.models import Q
from SchedulerApp.models import (
    ReservationModel as ReservationModel,
    ReservationStatus,
    OfficeHourModel,
    UserModel, CourseModel, ReservationAttendanceStatus
)


class Reservation:
    def __init__(
            self,
            office_hour_id=None,
            student_id=None,
            course_id=None,
            start_time=None,
            end_time=None,
            status=None,
    ):
        self.office_hour_id = office_hour_id
        self.student_id = student_id
        self.course_id = course_id
        self.start_time = start_time
        self.end_time = end_time
        self.status = status


    # ------------------------------------------------------------
    # CREATE RESERVATION
    # ------------------------------------------------------------
    @staticmethod
    def create_reservation(
            office_hour_id,
            student_id,
            course_id,  # NEW PARAMETER
            start_time,
            end_time=None,
            status="Reserved",
            duration_blocks=None,
    ):
        # Validation
        if not isinstance(office_hour_id, int) or office_hour_id <= 0:
            raise ValueError("Invalid office_hour_id")

        if not isinstance(student_id, int) or student_id <= 0:
            raise ValueError("Invalid student_id")

        if not isinstance(course_id, int) or course_id <= 0:
            raise ValueError("Invalid course_id")

        if not isinstance(start_time, datetime):
            raise ValueError("start_time must be a datetime")

        if end_time is not None and not isinstance(end_time, datetime):
            raise ValueError("end_time must be a datetime when provided")


        if duration_blocks is not None and end_time is None:
            if not isinstance(duration_blocks, int):
                raise ValueError("duration_blocks must be an int")
            if duration_blocks <= 0:
                raise ValueError("duration_blocks must be positive")

            end_time = start_time + timedelta(minutes=15 * duration_blocks)

        if end_time is None:
            end_time = start_time + timedelta(hours=1)

        # Fetch objects
        office_hour = OfficeHourModel.objects.get(pk=office_hour_id)
        student = UserModel.objects.get(pk=student_id)
        course = CourseModel.objects.get(pk=course_id)

        # ------------------------------------------------------------
        # CHECK IF STUDENT ALREADY HAS A RESERVATION FOR THIS COURSE
        # ------------------------------------------------------------

        now = timezone.now()

        existing = ReservationModel.objects.filter(
            student=student,
            course=course,
            status=ReservationStatus.RESERVED,
            start_time__gte=now  # ONLY upcoming reservations matter
        ).exists()

        if existing:
            raise ValueError("Student already has an upcoming reservation for this course.")


        # Normalize status
        normalized_status = status.capitalize() if isinstance(status, str) else status

        # Create reservation
        new_res = ReservationModel.objects.create(
            office_hour=office_hour,
            student=student,
            course=course,
            start_time=start_time,
            end_time=end_time,
            status=normalized_status,
        )

        return new_res.pk

    @staticmethod
    def update_attendance_status_for_staff(staff_user, reservation_id: int, attendance: str) -> bool:
        """
        Staff can update attendance_status ONLY for reservations that belong to their office hours.
        Returns True if updated, False otherwise.
        """

        if not staff_user:
            return False

        # Normalize
        att = (attendance or "").strip().lower()

        allowed_map = {
            "attended": ReservationAttendanceStatus.ATTENDED,
            "absent": ReservationAttendanceStatus.ABSENT,
            "tardy": ReservationAttendanceStatus.TARDY,
            "late": ReservationAttendanceStatus.TARDY,
        }

        if att not in allowed_map:
            return False

        try:
            r = (
                ReservationModel.objects
                .select_related("office_hour", "office_hour__staff_id")
                .get(pk=reservation_id)
            )
        except ReservationModel.DoesNotExist:
            return False

        # Security: reservation must belong to THIS staff member
        if not r.office_hour or r.office_hour.staff_id_id != staff_user.id:
            return False

        r.attendance_status = allowed_map[att]
        r.save()
        return True

    # ------------------------------------------------------------
    # CANCEL RESERVATION
    # ------------------------------------------------------------
    def cancel_reservation(self, reservation_id):
        """
        Sets the reservation's status to 'Canceled'.
        Returns True if successful, False if not found.
        """

        try:
            res = ReservationModel.objects.get(pk=reservation_id)
        except ReservationModel.DoesNotExist:
            return False

        res.status = ReservationStatus.CANCELED
        res.save()
        return True

    # ------------------------------------------------------------
    # GETTERS
    # ------------------------------------------------------------
    def get_staff_id(self, reservation_id):
        """
        Returns the staff_id from the linked OfficeHourModel.
        """

        try:
            res = ReservationModel.objects.get(pk=reservation_id)
        except ReservationModel.DoesNotExist:
            return None

        return res.office_hour.staff_id

    def get_officehour_id(self, reservation_id):
        """
        Returns the office_hour_id.
        """

        try:
            res = ReservationModel.objects.get(pk=reservation_id)
        except ReservationModel.DoesNotExist:
            return None

        return res.office_hour.office_hour_id

    def get_status(self, reservation_id):
        """
        Returns the reservation status string.
        """

        try:
            res = ReservationModel.objects.get(pk=reservation_id)
        except ReservationModel.DoesNotExist:
            return None

        return res.status.lower()

    def get_start_datetime(self, reservation_id):
        """
        Returns start_time as datetime.
        """
        try:
            res = ReservationModel.objects.get(pk=reservation_id)
        except ReservationModel.DoesNotExist:
            return None

        return res.start_time

    def get_end_datetime(self, reservation_id):
        """
        Returns end_time as datetime.
        """
        try:
            res = ReservationModel.objects.get(pk=reservation_id)
        except ReservationModel.DoesNotExist:
            return None

        return res.end_time

    @staticmethod
    def get_report_reservations_for_instructor(
        instructor_user,
        course_code: str = "",
        student_email: str = "",
        order: str = "recent",
    ):
        """
        Returns ReservationModel queryset for tardy/absent (report) reservations visible to instructor.
        Filters:
          - course_code (optional)
          - student_email (optional, exact match)
        Order:
          - 'recent' (default): newest first by start_time
          - 'oldest': oldest first by start_time
        """
        qs = (
            ReservationModel.objects
            .filter(
                course__instructorId=instructor_user.id,  # <-- FIX: instructor owns the course
                attendance_status__in=[
                    ReservationAttendanceStatus.ABSENT,
                    ReservationAttendanceStatus.TARDY,
                ],
            )
            .select_related("student", "course", "office_hour", "office_hour__staff_id")
        )

        course_code = (course_code or "").strip()
        student_email = (student_email or "").strip().lower()
        order = (order or "recent").strip().lower()

        if course_code:

            try:
                qs = qs.filter(course__code=int(course_code))
            except ValueError:
                # if user typed non-int, force empty result instead of crashing
                qs = qs.none()

        if student_email:
            qs = qs.filter(student__email__iexact=student_email)

        if order == "oldest":
            qs = qs.order_by("start_time")
        else:
            qs = qs.order_by("-start_time")

        return qs