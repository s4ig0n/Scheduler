from classes.Staff import Staff
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from SchedulerApp.models import (
    OfficeHourModel,
    UserModel,
    ReservationModel,
    ReservationStatus,
    CourseModel,
    StudentEnrollmentModel,
    UserRole,
    CourseOfficeHourAssignmentModel,
    ReservationAttendanceStatus
)


class Instructor(Staff):

    def __init__(self, email="", first_name="", last_name=""):
        # Ensure attributes exist even if Staff doesn't set them
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

        super().__init__(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password="pass",
            role=UserRole.INSTRUCTOR
        )

    # ------------------------------------------------------------------
    # PROPOSE OFFICE HOURS - Currently is not being used.
    # ------------------------------------------------------------------
    def propose_office_hours(self, start, end, software):
        try:
            instructor_record = UserModel.objects.filter(email=self.email).first()
            if not instructor_record:
                return "Error: Instructor not found"

            try:
                course = CourseModel.objects.first()

                if not course:
                    return "Error: No course available"

                OfficeHourModel.objects.create(
                    staff_id=instructor_record,
                    day_of_week="M",
                    start_time=start,
                    end_time=end,
                    location=software,
                    status="APPROVED",
                )
            except Exception as e:
                return f"Error: Failed to create office hour - {str(e)}"

        except Exception as e:
            return f"Error: {str(e)}"

        return "Successfully proposed office hours"

    # ------------------------------------------------------------------
    # VIEW MEETING TIMES
    # ------------------------------------------------------------------
    def view_meeting_times(self, course_id):
        """
        View approved office hours for a course.
        Updated to work with course code (IntegerField primary key).
        """
        try:
            course = CourseModel.objects.filter(code=course_id).first()
            if not course:
                return []

            # Get office hours through the many-to-many relationship
            # Also include office hours not yet linked to any course for backwards compatibility
            linked_office_hours = course.office_hours.filter(status="APPROVED")

            # If no results from many-to-many, fall back to checking all approved office hours
            # (This handles cases where office hours exist but aren't linked via CourseOfficeHourAssignmentModel)
            if not linked_office_hours.exists():
                # Get instructor for this course
                instructor_record = UserModel.objects.filter(id=course.instructorId).first()
                if instructor_record:
                    # Return all approved office hours for this instructor
                    all_office_hours = OfficeHourModel.objects.filter(
                        staff_id=instructor_record,
                        status="APPROVED"
                    )
                    return list(all_office_hours)

            return list(linked_office_hours)

        except Exception:
            return []

    def view_all_staff_office_hours(self, course_id):
        """
        View all staff office hours for a course.
        Updated to work with course code.
        """
        try:
            course = CourseModel.objects.filter(code=course_id).first()
            if not course:
                return []

            # Get all office hours through the many-to-many relationship
            return list(course.office_hours.all())
        except Exception:
            return []

    # ------------------------------------------------------------------
    # VIEW UPCOMING RESERVATIONS
    # ------------------------------------------------------------------
    def view_upcoming_reservations(self):
        now = timezone.now()
        try:
            instructor_record = UserModel.objects.filter(email=self.email).first()

            if instructor_record:
                reservations = ReservationModel.objects.filter(
                    office_hour__staff_id=instructor_record,
                    start_time__gte=now,
                )
                return list(reservations)
            else:
                return []

        except Exception:
            return []

    # ------------------------------------------------------------------
    # RECORD ATTENDANCE
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # APPROVE OFFICE HOURS
    # ------------------------------------------------------------------
    def approve_office_hours(self, ta_id, office_hour_id):
        try:
            office_hour = OfficeHourModel.objects.filter(
                office_hour_id=office_hour_id
            ).first()

            if not office_hour:
                return "Error: Office hour not found"

            if office_hour.status != "PENDING":
                return "Error: Can only approve pending office hours"

            office_hour.status = "APPROVED"
            office_hour.save()
            return "Successfully approved office hours"

        except Exception as e:
            return f"Error: Failed to approve office hours - {str(e)}"

    # ------------------------------------------------------------------
    # VIEW TARDY REPORT
    # ------------------------------------------------------------------
    def view_tardy_report(self, course_id):
        """
        View tardy and absence reports for students in a course.
        Updated to work with course code and many-to-many relationships.
        """
        try:
            course = CourseModel.objects.filter(code=course_id).first()
            if not course:
                return []

            # Get all office hours for this course through many-to-many
            office_hours = course.office_hours.all()

            # If no office hours linked, try getting them by instructor
            if not office_hours.exists():
                instructor_record = UserModel.objects.filter(id=course.instructorId).first()
                if instructor_record:
                    office_hours = OfficeHourModel.objects.filter(staff_id=instructor_record)

            if not office_hours.exists():
                return []


            reports = ReservationModel.objects.filter(
                course__course_assignments__staff=self,
                attendance_status__in=[
                    ReservationAttendanceStatus.ABSENT,
                    ReservationAttendanceStatus.TARDY,
                ]
            ).order_by("-timestamp")

            return list(reports)

        except Exception:
            return []

    # ------------------------------------------------------------------
    # UPLOAD STUDENT DATA
    # ------------------------------------------------------------------
    def upload_student_data(self, email_list, course_code):
        """
        Upload/import student data in bulk.
        Automatically enrolls students in the specified course.

        Args:
            email_list: List of student email addresses
            course_code: Course code (integer) or CourseModel object
        """
        results = {
            "created": 0,
            "linked": 0,
            "errors": [],
        }

        # Handle both course code (int) and CourseModel object
        if isinstance(course_code, int):
            course = CourseModel.objects.filter(code=course_code).first()
            if not course:
                # Don't return early - still validate emails even if course doesn't exist
                course = None
        else:
            course = course_code

        for raw_email in email_list:
            try:
                email = (raw_email or "").strip().lower()
                if not email:
                    continue

                # Validate email format BEFORE checking course
                try:
                    validate_email(email)
                except ValidationError:
                    results["errors"].append(f"Invalid email format: {email}")
                    continue

                # Now check if course exists (after email validation)
                if course is None:
                    results["errors"].append(f"Course not found")
                    continue

                # Check if student already exists
                student = UserModel.objects.filter(
                    email=email,
                    role=UserRole.STUDENT
                ).first()

                if not student:
                    # Create new student with email as temporary password
                    temp_password = email

                    try:
                        student = UserModel.objects.create(
                            email=email,
                            password=temp_password,
                            role=UserRole.STUDENT,
                        )
                        results["created"] += 1
                    except Exception as e:
                        results["errors"].append(
                            f"Failed to create student: {email} - {str(e)}"
                        )
                        continue

                # Enroll student in the course (get_or_create prevents duplicates)
                enrollment, created = StudentEnrollmentModel.objects.get_or_create(
                    student=student,
                    course=course,
                )
                results["linked"] += 1

            except Exception as e:
                results["errors"].append(
                    f"Unexpected error for {raw_email}: {str(e)}"
                )

        return results

    # ------------------------------------------------------------------
    # EDIT STUDENT DATA
    # ------------------------------------------------------------------
    def edit_student_data(self, student_id, updated_data):
        try:
            student = UserModel.objects.filter(
                id=student_id,
                role=UserRole.STUDENT,
            ).first()

            if not student:
                return "Error: Student not found"

            email = updated_data.get("email", "").strip()
            first_name = updated_data.get("first_name", "").strip()
            last_name = updated_data.get("last_name", "").strip()

            if not email or not first_name or not last_name:
                return "Error: This field is required"

            try:
                validate_email(email)
            except ValidationError:
                return "Error: Invalid email format"

            existing = UserModel.objects.filter(email=email).exclude(
                id=student_id
            ).first()
            if existing:
                return "Error: Email already in use"

            student.email = email
            student.first_name = first_name
            student.last_name = last_name

            if "password" in updated_data:
                password = updated_data.get("password", "").strip()
                if password:
                    student.password = password

            student.save()
            return "Successfully updated student data"

        except Exception as e:
            return f"Error: Failed to update student data - {str(e)}"

    # ==============================================================
    # NEW METHODS FOR DATABASE ACCESS (Called from Views)
    # ==============================================================

    def get_user_by_id(self, user_id):
        """
        Get a user by their ID.
        Returns UserModel object or None.
        """
        try:
            return UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            return None

    def get_instructor_courses_by_id(self, instructor_id):
        """
        Get all courses taught by instructor with given ID.
        Returns queryset of CourseModel objects.
        """
        try:
            return CourseModel.objects.filter(instructorId=instructor_id)
        except Exception:
            return CourseModel.objects.none()

    def get_course_by_code(self, course_code):
        """
        Get a course by its code.
        Returns CourseModel object or None.
        """
        try:
            return CourseModel.objects.get(code=course_code)
        except CourseModel.DoesNotExist:
            return None

    def check_course_ownership(self, course, instructor_id):
        """
        Check if the given instructor owns the course.
        Returns True if instructor owns course, False otherwise.
        """
        try:
            return int(course.instructorId) == int(instructor_id)
        except Exception:
            return False

    def get_students_in_course(self, course):
        """
        Get all students enrolled in a specific course.
        Returns queryset of UserModel objects (students) ordered by name.
        """
        try:
            return UserModel.objects.filter(
                student_course_assignments__course=course
            ).order_by('last_name', 'first_name')
        except Exception:
            return UserModel.objects.none()

    def get_student_by_id(self, student_id):
        """
        Get a specific student by ID.
        Returns UserModel object or None.
        """
        try:
            return UserModel.objects.filter(
                id=student_id,
                role=UserRole.STUDENT
            ).first()
        except Exception:
            return None

    def check_student_exists_by_email(self, email):
        """
        Check if a student with the given email already exists.
        Returns True if exists, False otherwise.
        """
        try:
            return UserModel.objects.filter(email=email).exists()
        except Exception:
            return False

    def create_student_user(self, email, first_name=" ", last_name=" ", password=" "):
        """
        Create a new student user.
        Returns the created UserModel object or None if failed.
        """
        try:
            new_student = UserModel(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.STUDENT,
                password=password
            )
            new_student.save()
            return new_student
        except Exception:
            return None