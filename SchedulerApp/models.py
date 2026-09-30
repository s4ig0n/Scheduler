from multiprocessing.util import MAXFD

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


#created this so in the future we can just replace this instead of touching
#the user model itself
class UserRole(models.TextChoices):
    ADMIN = "Admin"
    INSTRUCTOR = "Instructor"
    TA = "TA"
    STUDENT = "Student"

class UserModel(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices
    )

    created_at = models.DateTimeField(auto_now_add=True)
    #formatting
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

# Create your models here.

#model for the Course class
class CourseModel(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    section = models.CharField(max_length=10)
    instructorId = models.IntegerField()

    office_hours = models.ManyToManyField(
        "OfficeHourModel",
        through="CourseOfficeHourAssignmentModel",
        related_name="courses"
    )  #this will give us this functonality:  course.office_hours.all() and office_hour.courses.all()
    # - so the office_hour view can be easily done through this
    students = models.ManyToManyField(
        UserModel,
        through="StudentEnrollmentModel",
        related_name="courses_enrolled",
        limit_choices_to={'role': UserRole.STUDENT}, #the same as for office hours
    )

    def __str__(self):
        return f"{self.code} - {self.name} ({self.section})"




# model for the Office Hour class
DAY_OF_WEEK_CHOICES = [
    ("M", "Monday"),
    ("T", "Tuesday"),
    ("W", "Wednesday"),
    ("R", "Thursday"),
    ("F", "Friday"),
    ("Sa", "Saturday"),
    ("Su", "Sunday"),
]

STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("APPROVED", "Approved"),
    ("DENIED", "Denied"),
]


class OfficeHourModel(models.Model):
    # Since IDs are integers in the low level design, validators ensures 5 digits
    office_hour_id = models.AutoField(primary_key=True)

    staff_id = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        limit_choices_to={'role': [UserRole.TA, UserRole.INSTRUCTOR]},
        # Removed validators as they are unnecessary for ForeignKey
    )



    day_of_week = models.CharField(
        max_length=2,
        default="M",
        choices=DAY_OF_WEEK_CHOICES
    )

    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.TextField(default='TBD')

    status = models.CharField(
        max_length=10,
        default='PENDING',
        choices=STATUS_CHOICES
    )


class ReservationStatus(models.TextChoices):
    RESERVED = "Reserved"
    CANCELED = "Canceled"

class ReservationAttendanceStatus(models.TextChoices):
    ATTENDED = "Attended"
    TARDY = "Tardy"
    ABSENT = "Absent"

class ReservationModel(models.Model):
    office_hour = models.ForeignKey(
        OfficeHourModel,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    student = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        limit_choices_to={'role': UserRole.STUDENT},
        related_name="reservations"
    )

    course = models.ForeignKey(
        CourseModel,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices
    )

    attendance_status = models.CharField(
        max_length=20,
        choices=ReservationAttendanceStatus.choices,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.student.first_name} {self.student.last_name} - "
            f"{self.office_hour} - {self.course.code}"
        )

class StaffAssignmentModel(models.Model):
    id = models.AutoField(primary_key=True)

    staff = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        limit_choices_to={
            "role__in": [UserRole.TA, UserRole.INSTRUCTOR]
        },
        related_name="staff_assignments"
    )

    course = models.ForeignKey(
        CourseModel,
        on_delete=models.CASCADE,
        related_name="course_assignments"
    )
    def __str__(self):
        return f"{self.staff.email} → {self.course.name} ({self.course.section})"

class CourseOfficeHourAssignmentModel(models.Model):
    id = models.AutoField(primary_key=True)

    course = models.ForeignKey(
        CourseModel,
        on_delete=models.CASCADE,
        related_name="office_hour_assignments"
    )

    office_hour = models.ForeignKey(
        OfficeHourModel,
        on_delete=models.CASCADE,
        related_name="course_assignments"
    )

    def __str__(self):
        return f"{self.course.code} ({self.course.section}) ↔ OH #{self.office_hour.office_hour_id}"

class StudentEnrollmentModel(models.Model):
    id = models.AutoField(primary_key=True)

    student = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        limit_choices_to={'role': UserRole.STUDENT},
        related_name="student_course_assignments",
    )

    course = models.ForeignKey(
        CourseModel,
        on_delete=models.CASCADE,
        related_name="student_assignments",
    )

    def __str__(self):
        return f"{self.student.email} → {self.course.name} ({self.course.section})"
