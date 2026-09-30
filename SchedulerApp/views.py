from django.views import View
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse

import datetime
from collections import defaultdict

from classes.Admin import Administrator
from classes.TA import TA
from classes.Instructor import Instructor
from classes.Course import Course
from classes.User import User
from classes.Office_hours import Office_hours
from classes.Reservation import Reservation

from SchedulerApp.models import (
    UserModel,
    UserRole,
    CourseModel,
    ReservationModel,
    ReservationStatus,
    OfficeHourModel,
    StaffAssignmentModel,
    CourseOfficeHourAssignmentModel, ReservationAttendanceStatus
)


# =============================================================================
# HELPERS
# =============================================================================


def get_admin():
    """Return a domain Administrator object. No login required for acceptance tests."""
    return Administrator(email="admin@uwm.edu", first_name="Admin", last_name="User")


def render_error(msg):
    """All acceptance tests expect: status 200 and body containing 'error'."""
    return HttpResponse(f"error {msg}", status=200)


class SchedulerHomeView(View):
    def get(self, request):
        # If no active session then go to login
        user = User.get_by_id(request.session.get("user_id"))
        if not user:
            return redirect("login")

        # Redirect based on role (same logic as LoginView.post)
        if user.role == UserRole.ADMIN:
            return redirect("admin_home")

        if user.role == UserRole.TA:
            return redirect("ta_home")

        if user.role == UserRole.INSTRUCTOR:
            return redirect("instructor_home")

        # default: treat as student
        return redirect("student_home")


# =============================================================================
# ADMIN — STAFF MANAGEMENT
# =============================================================================


class LoginView(View):

    def get(self, request):
        # Clear session every time login page loads
        request.session.flush()
        return render(request, "SchedulerApp/login.html")

    def post(self, request):
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        # Required fields
        if not email or not password:
            return render(
                request,
                "SchedulerApp/login.html",
                {"error": "Invalid email or password."},
            )

        # Authenticate
        user = User.login(email, password)

        if user is None:
            # Invalid credentials
            return render(
                request,
                "SchedulerApp/login.html",
                {"error": "Invalid email or password."},
            )

        # Save session
        request.session["user_id"] = user.id
        request.session["user_role"] = user.role
        request.session["user_email"] = user.email

        # Check if student needs to complete setup (no name)
        if user.role == UserRole.STUDENT:
            if not user.first_name  or not user.last_name:
                return redirect("setup")  # Redirect to setup page

        # Redirect based on role
        if user.role == UserRole.TA:
            return redirect("ta_home")

        elif user.role == UserRole.ADMIN:
            return redirect("admin_home")

        elif user.role == UserRole.INSTRUCTOR:
            return redirect("instructor_home")

        else: return redirect("student_home")



class LogoutView(View):
    def get(self, request):
        request.session.flush()   # clears all session data safely
        return redirect("/login") # send user to the login page



class AdminHomeView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can access this page.")

        return render(request, "SchedulerApp/admin/admin_home.html", {"user": user})


class AdminStaffListView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        staff_qs = (
            UserModel.objects
            .filter(role__in=[UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.TA])
            .order_by("last_name", "first_name")
        )

        staff_rows = []
        for s in staff_qs:
            staff_rows.append({
                "id": s.id,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "email": getattr(s, "email", s.id),
                "role": getattr(s, "role", ""),
            })

        return render(
            request,
            "SchedulerApp/admin/staff.html",
            {"staff": staff_rows, "user": user},
        )


class AdminStaffCreateView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")


        return render(
            request,
            "SchedulerApp/admin/staff_create.html",
            {"user": user},
        )

    def post(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        # Retrieve form data
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        role = request.POST.get("role", "").strip()

        # Validate empty fields
        if not (email and password and first_name and last_name and role):
            return render(
                request,
                "SchedulerApp/admin/staff_create.html",
                {
                    "user": user,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "password": password,
                    "email_error": None,
                    "error": "All fields are required."
                },
            )

        # Check if email already exists
        if UserModel.objects.filter(email=email).exists():
            return render(
                request,
                "SchedulerApp/admin/staff_create.html",
                {
                    "user": user,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "password": password,
                    "email_error": "Email already exists.",
                },
            )

        # Create user via domain class
        new_user = User(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

        # Domain class validation
        if new_user.error is not None:
            return render(
                request,
                "SchedulerApp/admin/staff_create.html",
                {
                    "user": user,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "password": password,
                    "error": new_user.error,
                    "email_error": None
                },
            )

        # ⬇⬇⬇⬇ SUCCESS: Stay on the SAME PAGE with a success banner
        return render(
            request,
            "SchedulerApp/admin/staff_create.html",
            {
                "user": user,
                "success": "Account created successfully!",
            },
        )


class AdminCourseEditView(View):
    def get(self, request, course_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        course = get_object_or_404(CourseModel, pk=course_id)

        # Resolve instructor email if possible
        instructor_email = ""
        instructor = User.get_by_id(course.instructorId)
        if instructor is not None:
            instructor_email = instructor.email

        context = {
            "user": user,
            "code": course.code,
            "name": course.name,
            "section": course.section,
            "instructor_email": instructor_email,
        }
        return render(request, "SchedulerApp/admin/edit_course.html", context)

    def post(self, request, course_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        # Grab posted values
        name = request.POST.get("name", "").strip()
        section = request.POST.get("section", "").strip()
        instructor_email = request.POST.get("instructor_email", "").strip().lower()

        # we keep the original code (primary key)
        code = course_id

        # Basic required-field check (like create_course)
        if not name or not section or not instructor_email:
            return render(
                request,
                "SchedulerApp/admin/edit_course.html",
                {
                    "user": user,
                    "code": code,
                    "name": name,
                    "section": section,
                    "instructor_email": instructor_email,
                    "error": "This field is required",
                },
            )

        # Validate instructor exists and is an INSTRUCTOR
        instructor = UserModel.objects.filter(
            email=instructor_email,
            role=UserRole.INSTRUCTOR,
        ).first()

        if not instructor:
            return render(
                request,
                "SchedulerApp/admin/edit_course.html",
                {
                    "user": user,
                    "code": code,
                    "name": name,
                    "section": section,
                    "instructor_email": instructor_email,
                    "error": "Instructor with this email was not found or is not an instructor.",
                },
            )

        # Use domain Admin object to perform the edit
        admin = get_admin()
        result = admin.edit_course(
            course_code=code,
            updated_data={
                "name": name,
                "section": section,
                "instructorId": instructor.id,
            },
        )

        if result.get("status") != "success":
            return render(
                request,
                "SchedulerApp/admin/edit_course.html",
                {
                    "user": user,
                    "code": code,
                    "name": name,
                    "section": section,
                    "instructor_email": instructor_email,
                    "error": result.get("message", "Unable to update course."),
                },
            )

        # On success, go back to course list
        return redirect("/admin/courses/")

class AdminStaffEditView(View):
    def get(self, request, staff_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        staff = get_object_or_404(UserModel, pk=staff_id)

        context = {
            "user": user,
            "staff_id": staff.id,
            "first_name": staff.first_name,
            "last_name": staff.last_name,
            "email": staff.email,
            "role": staff.role,   # shown read-only in the form
        }
        return render(request, "SchedulerApp/admin/staff_edit.html", context)

    def post(self, request, staff_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        staff = get_object_or_404(UserModel, pk=staff_id)

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        # Validate required fields
        if not first_name or not last_name or not email:
            return render(
                request,
                "SchedulerApp/admin/staff_edit.html",
                {
                    "user": user,
                    "staff_id": staff.id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "role": staff.role,
                    "error": "First name, last name, and email are required.",
                },
            )

        updated_fields = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        }

        # Only update password if user typed something
        if password:
            updated_fields["password"] = password

        admin = get_admin()
        result = admin.edit_staff(staff_id=staff.id, updated_data=updated_fields)

        if result.get("status") != "success":
            return render(
                request,
                "SchedulerApp/admin/staff_edit.html",
                {
                    "user": user,
                    "staff_id": staff.id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "role": staff.role,
                    "error": "This field is required.",
                },
            )

        # SUCCESS — Stay on same page and show success message
        return render(
            request,
            "SchedulerApp/admin/staff_edit.html",
            {
                "user": user,
                "staff_id": staff.id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": staff.role,
                "message": "Information updated successfully!",
            },
        )


class AdminStaffDeleteView(View):
    def get(self, request, staff_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")


        return HttpResponse("Confirm deletion")

    def post(self, request, staff_id):
        staff = get_object_or_404(UserModel, pk=staff_id)

        if staff.email == "admin@uwm.edu":
            return HttpResponse("cannot delete your own account")

        staff.delete()
        return redirect("/admin/staff/")


# =============================================================================
# ADMIN — COURSE MANAGEMENT
# =============================================================================


class AdminCourseListView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        courses_qs = CourseModel.objects.filter().order_by("name", "section")

        #Convert to simple rows for template
        course_rows = []
        for c in courses_qs:
            instructor = User.get_by_id(c.instructorId)
            course_rows.append({
                "id": c.code,
                "name": c.name,
                "section": c.section,
                "instructor_first_name": instructor.first_name,
                "instructor_last_name": instructor.last_name,
            })

        return render(
            request,
            "SchedulerApp/admin/courses.html",
            {"courses": course_rows, "user": user},
        )


class AdminCourseCreateView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        return render(
            request,
            "SchedulerApp/admin/create_course.html",
            {"user": user},
        )

    def post(self, request):
        code_str = request.POST.get("code", "").strip()
        section = request.POST.get("section", "").strip()
        name = request.POST.get("name", "").strip()
        instructor_email = request.POST.get("instructor_email", "").strip().lower()

        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        # basic validation
        if not code_str or not name or not section or not instructor_email:
            return render(
                request,
                "SchedulerApp/admin/create_course.html",
                {
                    "user": user,
                    "error": "This field is required",
                    "old": request.POST,
                },
            )


        try:
            course_code = int(code_str)
        except ValueError:
            return render(
                request,
                "SchedulerApp/admin/create_course.html",
                {
                    "user": user,
                    "error": "Course code must be an integer.",
                    "code": code_str,
                    "section": section,
                    "name": name,
                    "instructor_email": instructor_email,
                },
            )

        # find instructor by email & role
        instructor = UserModel.objects.filter(
            email=instructor_email,
            role=UserRole.INSTRUCTOR,
        ).first()

        if not instructor:
            return render(
                request,
                "SchedulerApp/admin/create_course.html",
                {
                    "user": user,
                    "error": "Instructor with this email was not found or is not an instructor.",
                    "code": code_str,
                    "section": section,
                    "name": name,
                    "instructor_email": instructor_email,
                },
            )

        # use domain Course constructor
        new_course = Course(
            course_code=course_code,
            course_section=section,
            course_name=name,
            instructor_id=instructor.id,
        )

        # if domain validation fails, show its error
        if new_course.error is not None:
            return render(
                request,
                "SchedulerApp/admin/create_course.html",
                {
                    "user": user,
                    "error": new_course.error,
                    "code": code_str,
                    "section": section,
                    "name": name,
                    "instructor_email": instructor_email,
                },
            )

        return redirect("/admin/courses/")


class AdminCourseDeleteView(View):
    def post(self, request, course_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        try:

            Course.delete_course(course_id)
        except CourseModel.DoesNotExist:
            return HttpResponse("Course not found", status=404)

        return redirect("/admin/courses/")



# Placeholder required by acceptance tests
class AdminCourseSectionAssignTaView(View):
    def _build_ta_lists(self, course):
        # TAs already assigned to this course
        assigned_qs = (
            StaffAssignmentModel.objects
            .filter(course=course)
            .select_related("staff")
            .order_by("staff__last_name", "staff__first_name")
        )
        assigned_tas = [a.staff for a in assigned_qs]

        assigned_ids = [ta.id for ta in assigned_tas]

        # TAs not yet assigned to this course
        unassigned_tas = (
            UserModel.objects
            .filter(role=UserRole.TA)
            .exclude(id__in=assigned_ids)
            .order_by("last_name", "first_name")
        )

        return assigned_tas, unassigned_tas

    def get(self, request, course_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        course = get_object_or_404(CourseModel, pk=course_id)

        assigned_tas, unassigned_tas = self._build_ta_lists(course)

        return render(
            request,
            "SchedulerApp/admin/course_section_assign_ta.html",
            {
                "course": course,
                "course_id": course_id,
                "assigned_tas": assigned_tas,
                "unassigned_tas": unassigned_tas,
                "user": user,
            },
        )

    def post(self, request, course_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can perform this action.")

        course = get_object_or_404(CourseModel, pk=course_id)

        ta_email = request.POST.get("ta_email", "").strip().lower()
        action = request.POST.get("action", "assign")

        ta = UserModel.objects.filter(email=ta_email, role=UserRole.TA).first()
        if not ta:
            assigned_tas, unassigned_tas = self._build_ta_lists(course)
            return render(
                request,
                "SchedulerApp/admin/course_section_assign_ta.html",
                {
                    "course": course,
                    "course_id": course_id,
                    "assigned_tas": assigned_tas,
                    "unassigned_tas": unassigned_tas,
                    "user": user,
                    "error": "ta with this email was not found or is not a ta.",
                },
            )

        if action == "assign":
            StaffAssignmentModel.objects.get_or_create(course=course, staff=ta)
        elif action == "unassign":
            StaffAssignmentModel.objects.filter(course=course, staff=ta).delete()

        # Reload page so lists refresh
        return redirect("admin_course_section_assign_ta", course_id=course_id)

class AdminOfficeHoursView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.ADMIN:
            return HttpResponseForbidden("Only admins can view this page.")

        base_qs = OfficeHourModel.objects.all()
        context = build_office_hours_week_context(user, request, base_queryset=base_qs)
        return render(request, "SchedulerApp/staff/view_office_hours.html", context)


# =============================================================================
# ta — FULL REAL IMPLEMENTATION USING classes.ta
# =============================================================================

class TAHomeView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))

        if not user or user.role != UserRole.TA:
            return HttpResponseForbidden("Only TAs can access this page.")

        denied_qs = OfficeHourModel.objects.filter(staff_id=user.id, status="DENIED").order_by("office_hour_id")

        return render(
            request,
            "SchedulerApp/ta/home.html",
            {
                "user": user,
                "denied_office_hours": denied_qs,
            },
        )

class TAClearDeniedOfficeHoursView(View):
    def post(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.TA:
            return HttpResponseForbidden("Only TAs can perform this action.")

        denied_ids = list(
            OfficeHourModel.objects.filter(staff_id=user.id, status="DENIED")
            .values_list("office_hour_id", flat=True)
        )

        oh_service = Office_hours()
        for oh_id in denied_ids:
            oh_service.delete(oh_id)   # uses Office_hours.py delete()

        return redirect("ta_home")


class TAOfficeHoursView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.TA:
            return HttpResponseForbidden("Only TAs can view this page.")

        base_qs = OfficeHourModel.objects.filter(staff_id=user.id)
        context = build_office_hours_week_context(user, request, base_queryset=base_qs)
        return render(request, "SchedulerApp/staff/view_office_hours.html", context)


class TAOfficeHoursForCourseView(View):
    def get(self, request, course_id):
        email = request.GET.get("email", "")
        ta = TA(email=email)
        oh_list = ta.view_all_staff_office_hours(course_id)
        return HttpResponse(f"Office hours for {course_id}: {len(oh_list)} found")


# ta — PROPOSE OFFICE HOURS

DAY_CHOICES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "R": "Thursday",
    "F": "Friday",
}

class StaffProposeOfficeHoursView(View):
    def _get_courses_for_staff(self, user):
        """
        TA: courses from StaffAssignmentModel
        Instructor: courses where CourseModel.instructorId == user.id
        Returns: list of dicts {id, name} and a set of allowed ids (as strings)
        """
        if user.role == UserRole.INSTRUCTOR:
            qs = CourseModel.objects.filter(instructorId=user.id).order_by("code", "section")
            courses = [{
                "id": str(c.code),
                "name": f"{c.code} - {c.name} ({c.section})"
            } for c in qs]
            allowed = {str(c.code) for c in qs}
            return courses, allowed

        # default: TA
        assignments = (
            StaffAssignmentModel.objects
            .filter(staff_id=user.id)
            .select_related("course")
            .order_by("course__code", "course__section")
        )
        courses = [{
            "id": str(a.course.code),
            "name": f"{a.course.code} - {a.course.name} ({a.course.section})"
        } for a in assignments]
        allowed = {str(a.course.code) for a in assignments}
        return courses, allowed

    def _home_url_name(self, user):
        return "instructor_home" if user.role == UserRole.INSTRUCTOR else "ta_home"

    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role not in [UserRole.TA, UserRole.INSTRUCTOR]:
            return HttpResponseForbidden("Only staff can propose office hours.")

        courses, _allowed = self._get_courses_for_staff(user)

        return render(
            request,
            "SchedulerApp/staff/propose_office_hour.html",
            {
                "user": user,
                "courses": courses,
                "errors": {},
                "old": {},
                "home_url": self._home_url_name(user),
            }
        )

    def post(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role not in [UserRole.TA, UserRole.INSTRUCTOR]:
            return HttpResponseForbidden("Only staff can propose office hours.")

        course_ids = request.POST.getlist("course_id")  # multiple select
        day = request.POST.get("day_of_week", "").strip()
        start_time = request.POST.get("start_time", "").strip()
        end_time = request.POST.get("end_time", "").strip()
        software = request.POST.get("software", "").strip()

        courses, allowed_course_ids = self._get_courses_for_staff(user)

        errors = {}
        if not course_ids:
            errors["course_id"] = "Please select a course."
        if not day:
            errors["day_of_week"] = "Please select a day."
        if not start_time:
            errors["start_time"] = "Please enter start time."
        if not end_time:
            errors["end_time"] = "Please enter end time."
        if not software:
            errors["software"] = "Please choose a software."

        # Validate selected courses belong to this staff user
        for cid in course_ids:
            if str(cid) not in allowed_course_ids:
                errors["course_id"] = "Invalid course selection."
                break

        import datetime
        start = end = None
        if start_time and end_time:
            try:
                start = datetime.datetime.strptime(start_time, "%H:%M").time()
                end = datetime.datetime.strptime(end_time, "%H:%M").time()

                if (start.minute % 15 != 0) or (end.minute % 15 != 0):
                    errors["start_time"] = "Times must be in 15-minute increments (00, 15, 30, 45)."
                    errors["end_time"] = "Times must be in 15-minute increments (00, 15, 30, 45)."
                elif end <= start:
                    errors["end_time"] = "End time must be later than start time."

            except ValueError:
                errors["start_time"] = "Invalid time format."
                errors["end_time"] = "Invalid time format."

        if errors:
            return render(
                request,
                "SchedulerApp/staff/propose_office_hour.html",
                {
                    "user": user,
                    "courses": courses,
                    "errors": errors,
                    "old": request.POST,
                    "home_url": self._home_url_name(user),
                },
            )

        office_hour_id = Office_hours.propose(
            staff_id=user.id,
            course_ids=course_ids,
            start_time=start,
            end_time=end,
            day_of_week=DAY_CHOICES[day],
            location=software,
            status="PENDING",
        )

        return render(
            request,
            "SchedulerApp/staff/propose_office_hour.html",
            {
                "user": user,
                "courses": courses,
                "success": f"Office Hour submitted successfully! (ID: {office_hour_id})",
                "errors": {},
                "old": {},
                "home_url": self._home_url_name(user),
            },
        )



class StaffUpcomingReservationsView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role not in [UserRole.TA, UserRole.INSTRUCTOR]:
            return HttpResponseForbidden("Only staff can view this page.")

        now = timezone.now()

        qs = (
            ReservationModel.objects
            .filter(
                office_hour__staff_id=user.id,
                status=ReservationStatus.RESERVED,
                start_time__gte=now,
            )
            .select_related("office_hour", "student")
            .prefetch_related("office_hour__courses")
            .order_by("start_time")
        )

        rows = []
        for r in qs:
            courses = list(r.office_hour.courses.all())
            c = courses[0] if courses else None

            rows.append({
                "student_name": f"{r.student.first_name} {r.student.last_name}",
                "student_email": r.student.email,
                "course_code": c.code if c else "",
                "course_name": c.name if c else "",
                "start": r.start_time,
                "end": r.end_time,
            })

        return render(
            request,
            "SchedulerApp/staff/upcoming_reservations.html",
            {"reservations": rows, "user": user},
        )





class StaffRecordAttendanceView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user:
            return redirect("login")

        # staff = TA or Instructor
        if user.role not in [UserRole.TA, UserRole.INSTRUCTOR]:
            return HttpResponseForbidden("Only staff can access this page.")

        now = timezone.now()

        # Passed reservations, empty attendance_status, and OH belongs to this staff user
        qs = (
            ReservationModel.objects
            .filter(
                office_hour__staff_id=user.id,
                status=ReservationStatus.RESERVED,
                start_time__lt=now,
                attendance_status__isnull=True,
            )
            .select_related("student", "course", "office_hour")
            .order_by("-start_time")
        )

        rows = []
        for r in qs:
            rows.append({
                "id": r.id,
                "when": r.start_time,
                "course_code": r.course.code,
                "course_name": r.course.name,
                "course_section": r.course.section,
                "student_name": f"{r.student.first_name} {r.student.last_name}",
                "student_email": r.student.email,
            })

        context = {
            "user": user,
            "reservations": rows,
            "success": request.GET.get("success", ""),
            "error": request.GET.get("error", ""),
        }
        return render(request, "SchedulerApp/staff/record_attendance.html", context)


    def post(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user:
            return redirect("login")

        if user.role not in [UserRole.TA, UserRole.INSTRUCTOR]:
            return HttpResponseForbidden("Only staff can access this page.")

        reservation_id = int(request.POST.get("reservation_id", "0") or 0)
        attendance = request.POST.get("attendance", "")

        ok = Reservation.update_attendance_status_for_staff(user, reservation_id, attendance)
        if not ok:
            return redirect(request.path + "?error=Could+not+update+attendance.")

        return redirect(request.path + "?success=Attendance+recorded+successfully.")

# =============================================================================
# INSTRUCTOR — PLACEHOLDERS ONLY
# =============================================================================
class InstructorOfficeHoursView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can view this page.")

        # Base: only OH for this instructor (they can still filter further)
        base_qs = OfficeHourModel.objects.filter(staff_id=user.id)
        context = build_office_hours_week_context(user, request, base_queryset=base_qs)
        return render(request, "SchedulerApp/staff/view_office_hours.html", context)



class InstructorOfficeHourApproveView(View):
    def post(self, request, pk):
        user = User.get_by_id(request.session.get("user_id"))

        if not user or user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can approve office hours.")

        office_hour = get_object_or_404(OfficeHourModel, office_hour_id=pk)

        if office_hour.status != "PENDING":
            return redirect('instructor_pending_office_hours')

        office_hour.status = "APPROVED"
        office_hour.save()

        return redirect('instructor_pending_office_hours')


class InstructorOfficeHourDenyView(View):
    def post(self, request, pk):
        user = User.get_by_id(request.session.get("user_id"))

        if not user or user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can deny office hours.")

        office_hour = get_object_or_404(OfficeHourModel, office_hour_id=pk)

        if office_hour.status != "PENDING":
            return redirect('instructor_pending_office_hours')

        office_hour.status = "DENIED"
        office_hour.save()

        return redirect('instructor_pending_office_hours')


class InstructorStudentCreateView(View):
    def get(self, request, course_id):
        return HttpResponse("Create student form")

    def post(self, request, course_id):
        return HttpResponse("Student created")

"""
Instructor Student Management Views
Handles course selection, student upload, and student editing
"""


class InstructorHomeView(View):
    required_role = UserRole.INSTRUCTOR

    def get(self, request):
        # Ensure user is logged in
        user_id = request.session.get("user_id")
        if not user_id:
            return redirect("login")

        # Create instructor instance for database access
        instructor = Instructor()

        # Get user from database
        user = instructor.get_user_by_id(user_id)
        if not user:
            return redirect("login")

        # Override request.user so all views can use it
        request.user = user

        # Debug printing
        print("SESSION DATA:")
        for key, value in request.session.items():
            print(f"{key}: {value}")

        print("USER INFO:")
        print(f"id: {request.user.id}")
        print(f"email: {request.user.email}")
        print(f"role: {request.user.role}")
        print(f"first_name: {request.user.first_name}")
        print(f"last_name: {request.user.last_name}")

        # Get courses taught by instructor
        instructor_courses = instructor.get_instructor_courses_by_id(request.user.id)
        print(f"Found {instructor_courses.count()} courses for instructor {request.user.id}")

        return render(
            request,
            "SchedulerApp/instructor/instructor_home.html",
            {
                "user": request.user,
                "courses": instructor_courses
            }
        )


class InstructorCancelOfficeHoursView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can access this page.")


        my_courses = CourseModel.objects.filter(instructorId=user.id)


        approved_oh_qs = (
            OfficeHourModel.objects
            .filter(
                status="APPROVED",
                course_assignments__course__in=my_courses,
            )
            .select_related("staff_id")
            .prefetch_related("course_assignments__course")
            .distinct()
            .order_by("day_of_week", "start_time", "office_hour_id")
        )

        office_hours = []
        for oh in approved_oh_qs:
            staff = oh.staff_id
            courses = [a.course for a in oh.course_assignments.all()]
            course_labels = ", ".join(f"{c.code} ({c.section})" for c in courses) if courses else "—"

            office_hours.append({
                "id": oh.office_hour_id,
                "staff_name": f"{staff.first_name} {staff.last_name}",
                "courses": course_labels,
                "day": oh.day_of_week,
                "start": oh.start_time.strftime("%I:%M %p"),
                "end": oh.end_time.strftime("%I:%M %p"),
            })

        return render(
            request,
            "SchedulerApp/instructor/cancel_office_hours.html",
            {
                "user": user,
                "office_hours": office_hours,
                "success": request.GET.get("success", ""),
                "error": request.GET.get("error", ""),
            },
        )

    def post(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can perform this action.")

        oh_id = request.POST.get("office_hour_id")
        if not oh_id:
            return redirect(reverse("instructor_cancel_office_hours") + "?error=Missing office hour id.")

        oh_service = Office_hours()
        ok = oh_service.delete(int(oh_id))

        if not ok:
            return redirect(reverse("instructor_cancel_office_hours") + "?error=Office hour not found.")

        return redirect(reverse("instructor_cancel_office_hours") + "?success=Office hour deleted.")

class InstructorStudentManageView(View):
    """
    Main student management page - choose between upload or edit
    """
    required_role = UserRole.INSTRUCTOR

    def get(self, request, course_id):
        # Create instructor instance for database access
        instructor = Instructor()

        # Ensure user is loaded from session if not authenticated
        if not hasattr(request, "user") or request.user.is_anonymous:
            user_id = request.session.get("user_id")
            user_role = request.session.get("user_role")
            user_email = request.session.get("user_email")

            if not user_id:
                return redirect("login")

            request.user = instructor.get_user_by_id(user_id)
            if not request.user:
                return redirect("login")

            print("Loaded user from session:")
            print(f"ID: {request.user.id}")
            print(f"Email: {request.user.email}")
            print(f"Role: {request.user.role}")
            print(f"First name: {request.user.first_name}")
            print(f"Last name: {request.user.last_name}")

        # Print session data
        print("SESSION DATA:")
        for key, value in request.session.items():
            print(f"{key}: {value}")

        # Try to get the course
        course = instructor.get_course_by_code(course_id)
        if not course:
            return HttpResponse("Course not found", status=404)

        print(f"Course found: code={course.code}, instructorId={course.instructorId}")

        # Compare IDs safely
        if not instructor.check_course_ownership(course, request.user.id):
            print(f"Forbidden: instructorId={course.instructorId} != user.id={request.user.id}")
            return HttpResponseForbidden("You can only manage students for your own courses")

        # If everything is fine, render the page
        return render(
            request,
            "SchedulerApp/instructor/manage_students.html",
            {
                "user": request.user,
                "course": course,
                "course_id": course_id
            }
        )


class InstructorStudentUploadView(View):
    """
    Upload student data from .txt file.
    Creates new Student users with default password " " if they don't already exist.
    """
    required_role = UserRole.INSTRUCTOR

    def get(self, request, course_id):
        # Create instructor instance for database access
        instructor = Instructor()

        if not hasattr(request, "user") or request.user.is_anonymous:
            user_id = request.session.get("user_id")
            if not user_id:
                return redirect("login")
            request.user = instructor.get_user_by_id(user_id)
            if not request.user:
                return redirect("login")

        # Verify instructor owns course
        course = instructor.get_course_by_code(course_id)
        if not course:
            return HttpResponse("Course not found", status=404)

        if not instructor.check_course_ownership(course, request.user.id):
            return HttpResponseForbidden("You can only upload students for your own courses")

        return render(
            request,
            "SchedulerApp/instructor/upload_students.html",
            {"user": request.user, "course": course, "course_id": course_id}
        )

    def post(self, request, course_id):
        # Create instructor instance for database access
        instructor = Instructor()

        if not hasattr(request, "user") or request.user.is_anonymous:
            user_id = request.session.get("user_id")
            if not user_id:
                return redirect("login")
            request.user = instructor.get_user_by_id(user_id)
            if not request.user:
                return redirect("login")

        # Verify instructor owns course
        course = instructor.get_course_by_code(course_id)
        if not course:
            return HttpResponse("Course not found", status=404)

        if not instructor.check_course_ownership(course, request.user.id):
            return HttpResponseForbidden("You can only upload students for your own courses")

        uploaded_file = request.FILES.get("student_file")
        if not uploaded_file:
            return render(
                request,
                "SchedulerApp/instructor/upload_students.html",
                {"user": request.user, "course": course, "course_id": course_id, "error": "No file uploaded"}
            )

        if not uploaded_file.name.endswith(".txt"):
            return render(
                request,
                "SchedulerApp/instructor/upload_students.html",
                {"user": request.user, "course": course, "course_id": course_id, "error": "Please upload a .txt file"}
            )

        try:
            content = uploaded_file.read().decode("utf-8")
            emails = [line.strip() for line in content.split("\n") if line.strip()]

            # Create instructor instance with user info and upload students to the specific course
            instructor_obj = Instructor(
                email=request.user.email,
                first_name=request.user.first_name,
                last_name=request.user.last_name
            )
            results = instructor_obj.upload_student_data(emails, course)

            # Add existing emails count
            results['existing'] = results.get('existing', 0)

            return render(
                request,
                "SchedulerApp/instructor/upload_students.html",
                {
                    "user": request.user,
                    "course": course,
                    "course_id": course_id,
                    "results": results
                }
            )


        except Exception as e:
            return render(
                request,
                "SchedulerApp/instructor/upload_students.html",
                {"user": request.user, "course": course, "course_id": course_id,
                 "error": f"Error processing file: {str(e)}"}
            )


class InstructorStudentListView(View):
    """
    List all students in a course for editing
    """
    required_role = UserRole.INSTRUCTOR

    def get(self, request, course_id):
        # Create instructor instance for database access
        instructor = Instructor()

        # Load user from session if not authenticated
        if not hasattr(request, "user") or request.user.is_anonymous:
            user_id = request.session.get("user_id")
            if not user_id:
                return redirect("login")
            request.user = instructor.get_user_by_id(user_id)
            if not request.user:
                return redirect("login")
            print("Loaded user from session (GET - Student List):")
            print(f"ID: {request.user.id}, Email: {request.user.email}, Role: {request.user.role}")

        print("SESSION DATA (GET - Student List):")
        for key, value in request.session.items():
            print(f"{key}: {value}")

        # Verify instructor owns course
        course = instructor.get_course_by_code(course_id)
        if not course:
            return HttpResponse("Course not found", status=404)

        print(f"Course found: code={course.code}, instructorId={course.instructorId}")

        if not instructor.check_course_ownership(course, request.user.id):
            print(f"Forbidden: instructorId={course.instructorId} != user.id={request.user.id}")
            return HttpResponseForbidden("You can only view students in your own courses")

        # Get all students for this course
        students = instructor.get_students_in_course(course)

        return render(
            request,
            "SchedulerApp/instructor/student_list.html",
            {
                "user": request.user,
                "course": course,
                "students": students,
                "course_id": course_id
            }
        )


class InstructorStudentEditView(View):
    """
    Edit student's name, email, and password
    """
    required_role = UserRole.INSTRUCTOR

    def get_user_from_session(self, request):
        user_id = request.session.get("user_id")
        if not user_id:
            return None

        # Use instructor instance to get user
        instructor = Instructor()
        return instructor.get_user_by_id(user_id)

    def get(self, request, course_id, student_id):
        user = self.get_user_from_session(request)
        if not user:
            return redirect("login")

        if user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can perform this action.")

        # Create instructor instance for database access
        instructor = Instructor()

        # Verify instructor owns course
        course = instructor.get_course_by_code(course_id)
        if not course:
            return HttpResponse("Course not found", status=404)

        if not instructor.check_course_ownership(course, user.id):
            return HttpResponseForbidden("You can only edit students in your own courses")

        # Get student
        student = instructor.get_student_by_id(student_id)
        if not student:
            return HttpResponse("Student not found", status=404)

        return render(
            request,
            "SchedulerApp/instructor/edit_student.html",
            {
                "user": user,
                "student": student,
                "course": course,
                "course_id": course_id
            }
        )

    def post(self, request, course_id, student_id):
        user = self.get_user_from_session(request)
        if not user:
            return redirect("login")

        if user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can perform this action.")

        # Create instructor instance for database access
        instructor_obj = Instructor(email=user.email, first_name=user.first_name, last_name=user.last_name)

        # Verify instructor owns course
        course = instructor_obj.get_course_by_code(course_id)
        if not course:
            return HttpResponse("Course not found", status=404)

        if not instructor_obj.check_course_ownership(course, user.id):
            return HttpResponseForbidden("You can only edit students in your own courses")

        # Get the student
        student = instructor_obj.get_student_by_id(student_id)
        if not student:
            return HttpResponse("Student not found", status=404)

        # Get form data
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "").strip()

        # Check if any required fields are empty
        if not email or not first_name or not last_name:
            error_msg = "This field is required"
            return render(
                request,
                "SchedulerApp/instructor/edit_student.html",
                {
                    "user": user,
                    "course": course,
                    "course_id": course_id,
                    "student": student,
                    "error": error_msg
                }
            )

        # Build updated data dictionary
        updated_data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        }

        # Only include password if provided
        if password:
            updated_data["password"] = password

        # Update student using instructor class method
        result = instructor_obj.edit_student_data(student_id, updated_data)

        if "Error" in result:
            return render(
                request,
                "SchedulerApp/instructor/edit_student.html",
                {
                    "user": user,
                    "course": course,
                    "course_id": course_id,
                    "student": student,
                    "error": result.replace("Error: ", "")
                }
            )

        # Refresh student data to show updated values
        student = instructor_obj.get_student_by_id(student_id)

        # Success
        return render(
            request,
            "SchedulerApp/instructor/edit_student.html",
            {
                "user": user,
                "course": course,
                "course_id": course_id,
                "student": student,
                "success": "Student information updated successfully!"
            }
        )




class InstructorReportsView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can access this page.")

        # ---- query params ----
        selected_course = request.GET.get("course", "").strip()
        selected_student = request.GET.get("student", "").strip()
        sort = request.GET.get("sort", "recent").strip()  # 'recent' or 'oldest'

        # ---- dropdown options: courses this instructor teaches ----
        courses_qs = CourseModel.objects.filter(instructorId=user.id).order_by("code")
        course_options = [
            {"code": c.code, "label": f"{c.code} - {c.name} ({c.section})"}
            for c in courses_qs
        ]

        # ---- main query via helper ----
        reports_qs = Reservation.get_report_reservations_for_instructor(
            instructor_user=user,
            course_code=selected_course,
            student_email=selected_student,
            order=sort,
        )

        # ---- convert to template-friendly rows ----
        report_rows = []
        for r in reports_qs:
            report_rows.append({
                "student_display": f"{r.student.first_name} {r.student.last_name}",
                "student_email": r.student.email,
                "attendance": r.attendance_status,  # "Tardy" or "Absent"
                "course_display": f"{r.course.code}, {r.course.name}, {r.course.section}",
                "ta_email": r.office_hour.staff_id.email if r.office_hour and r.office_hour.staff_id else "",
                "start": r.start_time,
                "end": r.end_time,
            })

        context = {
            "reports": report_rows,
            "course_options": course_options,
            "selected_course": selected_course,
            "selected_student": selected_student,
            "sort": sort,
        }
        return render(request, "SchedulerApp/instructor/report_list.html", context)

class InstructorPendingOfficeHoursView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))

        if not user or user.role != UserRole.INSTRUCTOR:
            return HttpResponseForbidden("Only instructors can view this page.")

        # Get filters from query params
        selected_course = request.GET.get('course', '')
        selected_staff = request.GET.get('staff', '')

        # Get all courses taught by this instructor
        courses = CourseModel.objects.filter(instructorId=user.id)
        course_ids = [c.code for c in courses]

        # Build course dropdown options
        course_options = [
            {'code': c.code, 'label': f"{c.code} - {c.name}"}
            for c in courses
        ]

        # Get all office hours linked to these courses via the assignment table
        office_hour_assignments = CourseOfficeHourAssignmentModel.objects.filter(
            course__code__in=course_ids
        ).select_related('office_hour', 'course', 'office_hour__staff_id')

        # Apply filters
        if selected_course:
            office_hour_assignments = office_hour_assignments.filter(course__code=selected_course)
        if selected_staff:
            staff_user = UserModel.objects.filter(email=selected_staff).first()
            if staff_user:
                office_hour_assignments = office_hour_assignments.filter(office_hour__staff_id=staff_user)

        # Build staff dropdown
        staff_ids = set()
        for assignment in office_hour_assignments:
            staff_ids.add(assignment.office_hour.staff_id.id)

        staff_list = []
        for staff_id in staff_ids:
            staff = User.get_by_id(staff_id)
            if staff:
                staff_list.append({
                    'email': staff.email,
                    'label': f"{staff.first_name} {staff.last_name}"
                })

        # Build calendar grid
        days = [
            {'label': 'Monday', 'value': 'M', 'full_name': 'Monday'},
            {'label': 'Tuesday', 'value': 'T', 'full_name': 'Tuesday'},
            {'label': 'Wednesday', 'value': 'W', 'full_name': 'Wednesday'},
            {'label': 'Thursday', 'value': 'R', 'full_name': 'Thursday'},
            {'label': 'Friday', 'value': 'F', 'full_name': 'Friday'},
        ]

        # Generate 15-minute time slots from 8 AM to 8 PM
        import datetime
        time_slots = []
        for hour in range(8, 21):  # 8 AM to 8 PM
            for minute in [0, 15, 30, 45]:
                time_slots.append(datetime.time(hour, minute))

        # Build a map of office hours by day and their time ranges
        office_hours_map = defaultdict(list)

        for assignment in office_hour_assignments:
            oh = assignment.office_hour

            # Match with full day name
            day_match = None
            for day in days:
                if oh.day_of_week == day['full_name'] or oh.day_of_week == day['value']:
                    day_match = day['full_name']
                    break

            if not day_match:
                continue

            staff = oh.staff_id

            # Get all course codes for this office hour
            course_codes = [
                a.course.code
                for a in CourseOfficeHourAssignmentModel.objects.filter(
                    office_hour=oh
                ).select_related('course')
            ]

            office_hours_map[day_match].append({
                'id': oh.office_hour_id,
                'staff_name': f"{staff.first_name} {staff.last_name}",
                'courses': course_codes,
                'status': oh.status,
                'start_time': oh.start_time,
                'end_time': oh.end_time,
            })

        # Build rows with 15-minute increments
        # Track which cells should be skipped due to rowspan
        skip_cells = set()  # (row_index, day_index)

        rows = []
        for row_idx, time_slot in enumerate(time_slots):
            row = {
                'time': time_slot.strftime('%I:%M %p'),
                'cells': []
            }

            for day_idx, day in enumerate(days):
                # Check if this cell should be skipped (part of a previous rowspan)
                if (row_idx, day_idx) in skip_cells:
                    row['cells'].append({'skip': True})
                    continue

                entries = []
                day_office_hours = office_hours_map.get(day['full_name'], [])

                for oh_data in day_office_hours:
                    # Check if this time slot is the START of the office hour
                    if oh_data['start_time'] == time_slot:
                        # Calculate rowspan (number of 15-minute blocks this OH covers)
                        start_minutes = oh_data['start_time'].hour * 60 + oh_data['start_time'].minute
                        end_minutes = oh_data['end_time'].hour * 60 + oh_data['end_time'].minute
                        duration_minutes = end_minutes - start_minutes
                        rowspan = duration_minutes // 15

                        # Mark cells that should be skipped
                        for i in range(1, rowspan):
                            skip_cells.add((row_idx + i, day_idx))

                        entries.append({
                            'id': oh_data['id'],
                            'staff_name': oh_data['staff_name'],
                            'courses': oh_data['courses'],
                            'status': oh_data['status'],
                            'rowspan': rowspan,
                            'start_time': oh_data['start_time'].strftime('%I:%M %p'),
                            'end_time': oh_data['end_time'].strftime('%I:%M %p'),
                        })
                        break  # Only one office hour per cell start

                row['cells'].append({'entries': entries})

            rows.append(row)

        # Count pending office hours
        pending_count = sum(
            1 for assignment in office_hour_assignments
            if assignment.office_hour.status == 'PENDING'
        )

        return render(
            request,
            "SchedulerApp/instructor/pending_office_hours.html",
            {
                "user": user,
                "courses": course_options,
                "staff_list": staff_list,
                "selected_course": selected_course,
                "selected_staff": selected_staff,
                "days": days,
                "rows": rows,
                "pending_count": pending_count,
            }
        )



# =============================================================================
# STUDENT — PLACEHOLDERS
# =============================================================================

class StudentHomeView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user:
            return redirect("login")

        # If you have a dedicated student role, enforce it:
        if user.role != UserRole.STUDENT:
            return HttpResponseForbidden("Only students can access this page.")

        return render(request, "SchedulerApp/student/home.html", {"user": user})


class StudentOfficeHourView(View):
    def get(self, request):
        user = User.get_by_id(request.session.get("user_id"))
        if not user:
            return redirect("login")

        if user.role != UserRole.STUDENT:
            return HttpResponseForbidden("Only students can access this page.")

        context = build_student_office_hours_week_context(user, request)
        # Optional success / error messages via query params
        context["success"] = request.GET.get("success", "")
        context["error"] = request.GET.get("error", "")
        return render(request, "SchedulerApp/student/office_hours.html", context)


class StudentUpcomingReservationView(View):
    """
    Shows the student's upcoming reservations ("My Reservations" page).
    Only reservations with start_time >= now and status = Reserved are shown.
    """

    def get(self, request):
        # Get logged-in domain user
        user = User.get_by_id(request.session.get("user_id"))
        if not user:
            return redirect("login")

        if user.role != UserRole.STUDENT:
            return HttpResponseForbidden("Only students can view reservations.")

        now = timezone.now()

        # Only FUTURE reservations that are still reserved
        reservations_qs = (
            ReservationModel.objects
            .filter(
                student_id=user.id,
                status=ReservationStatus.RESERVED,
                start_time__gte=now,
            )
            .select_related("office_hour", "office_hour__staff_id")
            .prefetch_related("office_hour__course_assignments__course")
            .order_by("start_time")
        )

        reservations = []
        for res in reservations_qs:
            oh = res.office_hour
            staff = oh.staff_id

            # All courses linked to this office hour (often just one)
            courses = [ca.course for ca in oh.course_assignments.all()]
            if courses:
                course_label = ", ".join(
                    f"{c.code} - {c.name} ({c.section})"
                    for c in courses
                )
            else:
                course_label = "No course assigned"

            # can cancel only if more than 24 hours before start
            can_cancel = (res.start_time - now).total_seconds() > 24 * 3600

            reservations.append({
                "id": res.id,
                "course_label": course_label,
                "staff_name": f"{staff.first_name} {staff.last_name}",
                "staff_email": staff.email,
                "start": res.start_time,
                "end": res.end_time,
                "location": oh.location,
                "can_cancel": can_cancel,
            })

        context = {
            "user": user,
            "reservations": reservations,
            "success": request.GET.get("success", ""),
            "error": request.GET.get("error", ""),
        }
        return render(request, "SchedulerApp/student/my_reservations.html", context)

class SetupView(View):
    def _get_logged_in_user(self, request):
        user_id = request.session.get("user_id")
        if not user_id:
            return None
        return UserModel.objects.filter(pk=user_id).first()

    def get(self, request):
        user = self._get_logged_in_user(request)
        if not user:
            return redirect("login")

        # If user already has a name, redirect to home
        if user.first_name and user.last_name:
            return redirect("/")

        return render(
            request,
            "SchedulerApp/student/setup.html",
            {"user": user},
        )

    def post(self, request):
        user = self._get_logged_in_user(request)
        if not user:
            return redirect("login")

        first = request.POST.get("first_name", "").strip()
        last = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        errors = {}
        if not first:
            errors["first_name"] = "First name is required."
        if not last:
            errors["last_name"] = "Last name is required."
        if not password:
            errors["password"] = "Password is required."
        if not confirm_password:
            errors["confirm_password"] = "Please confirm your password."
        if password and confirm_password and password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return render(
                request,
                "SchedulerApp/student/setup.html",
                {
                    "user": user,
                    "errors": errors,
                    "old": request.POST,
                },
            )

        # Save the name
        user.first_name = first
        user.last_name = last
        user.password = password
        user.save()

        # Redirect to home
        return redirect("/")
# =============================================================================
# RESERVATIONS
# =============================================================================

class CreateReservationView(View):
    """
    Student creates a reservation (15–60 minutes) for a specific office hour
    and start slot.

    GET  -> show confirmation + course selection (if multiple courses)
    POST -> validate and create reservation, then redirect back to student OH grid
    """

    def _compute_appointment_date(self, oh, week_start_str, day_code):
        """
        Use the week_start + day_code from the request to get the actual
        calendar date of the reservation.
        """
        # base week_start (Monday)
        if week_start_str:
            try:
                week_start = datetime.datetime.strptime(
                    week_start_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                today = timezone.localdate()
                week_start = today - datetime.timedelta(days=today.weekday())
        else:
            today = timezone.localdate()
            week_start = today - datetime.timedelta(days=today.weekday())

        # if day_code missing, derive from office hour day_of_week
        day_code_map = {
            "Monday": "M",
            "Tuesday": "T",
            "Wednesday": "W",
            "Thursday": "R",
            "Friday": "F",
        }
        offset_map = {"M": 0, "T": 1, "W": 2, "R": 3, "F": 4}

        if day_code not in offset_map:
            oh_code = day_code_map.get(oh.day_of_week)
            if oh_code in offset_map:
                day_code = oh_code
            else:
                day_code = "M"

        appointment_date = week_start + datetime.timedelta(days=offset_map[day_code])
        return appointment_date, week_start.isoformat(), day_code

    # ------------------------------------------------------------------ GET
    def get(self, request, office_hour_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.STUDENT:
            return HttpResponseForbidden("Only students can make reservations.")

        oh = get_object_or_404(OfficeHourModel, pk=office_hour_id)

        start_str = (request.GET.get("start") or "").strip()
        week_start_str = (request.GET.get("week_start") or "").strip()
        day_code = (request.GET.get("day") or "").strip()

        # compute actual appointment date for this reservation
        appointment_date, week_start_iso, day_code = self._compute_appointment_date(
            oh, week_start_str, day_code
        )

        # parse start time
        try:
            start_clock = datetime.datetime.strptime(start_str, "%H:%M").time()
        except ValueError:
            return HttpResponse("Invalid start time.", status=400)

        # Courses this student is enrolled in
        student_course_codes = set(
            CourseModel.objects
            .filter(students__id=user.id)
            .values_list("code", flat=True)
        )

        assigned_courses = []
        for ca in oh.course_assignments.all():
            if ca.course.code in student_course_codes:
                assigned_courses.append(ca.course)

        if not assigned_courses:
            return HttpResponseForbidden(
                "You are not enrolled in any course for this office hour."
            )

        # --- Per-course limit: 1 active reservation per course ---
        now = timezone.now()

        my_res_qs = (
            ReservationModel.objects
            .filter(
                student_id=user.id,
                status=ReservationStatus.RESERVED,
                start_time__gte=now,  # Only upcoming matter
            )
        )

        my_reserved_course_codes = set()
        for r in my_res_qs:
            for x in r.office_hour.course_assignments.all():
                my_reserved_course_codes.add(x.course.code)

        # Build list of choices for template
        course_choices = []
        for c in assigned_courses:
            course_choices.append(
                {
                    "id": c.code,
                    "label": f"{c.code} - {c.name} ({c.section})",
                    "disabled": c.code in my_reserved_course_codes,
                }
            )

        duration_options = [
            {"value": 15, "label": "15 minutes"},
            {"value": 30, "label": "30 minutes"},
            {"value": 45, "label": "45 minutes"},
            {"value": 60, "label": "60 minutes"},
        ]

        context = {
            "office_hour": oh,
            "start_time_str": start_str,
            "courses": course_choices,
            "duration_options": duration_options,
            "selected_course_id": "",
            "selected_duration": "",
            "already_reserved_course_codes": my_reserved_course_codes,
            "error": "",
            "appointment_date": appointment_date,
            "week_start": week_start_iso,
            "day_code": day_code,
        }
        return render(request, "SchedulerApp/student/reservation_confirm.html", context)

    # ------------------------------------------------------------------ POST
    def post(self, request, office_hour_id):
        user = User.get_by_id(request.session.get("user_id"))
        if not user or user.role != UserRole.STUDENT:
            return HttpResponseForbidden("Only students can make reservations.")

        oh = get_object_or_404(OfficeHourModel, pk=office_hour_id)

        start_str = (request.POST.get("start_time") or "").strip()
        course_id_str = (request.POST.get("course_id") or "").strip()
        duration_str = (request.POST.get("duration") or "").strip()
        week_start_str = (request.POST.get("week_start") or "").strip()
        day_code = (request.POST.get("day") or "").strip()

        # actual appointment date
        appointment_date, week_start_iso, day_code = self._compute_appointment_date(
            oh, week_start_str, day_code
        )

        duration_options = [
            {"value": 15, "label": "15 minutes"},
            {"value": 30, "label": "30 minutes"},
            {"value": 45, "label": "45 minutes"},
            {"value": 60, "label": "60 minutes"},
        ]

        def render_with_error(msg):
            # rebuild course list the same way as GET, but with error
            student_course_codes = set(
                CourseModel.objects
                .filter(students__id=user.id)
                .values_list("code", flat=True)
            )

            assigned_courses_inner = []
            for ca in oh.course_assignments.all():
                if ca.course.code in student_course_codes:
                    assigned_courses_inner.append(ca.course)

            now = timezone.now()

            my_res_qs_inner = (
                ReservationModel.objects
                .filter(
                    student_id=user.id,
                    status=ReservationStatus.RESERVED,
                    start_time__gte=now,
                )
            )

            my_reserved_course_codes_inner = set()
            for r in my_res_qs_inner:
                for x in r.office_hour.course_assignments.all():
                    my_reserved_course_codes_inner.add(x.course.code)

            course_choices_inner = []
            for c in assigned_courses_inner:
                course_choices_inner.append(
                    {
                        "id": c.code,
                        "label": f"{c.code} - {c.name} ({c.section})",
                        "disabled": c.code in my_reserved_course_codes_inner,
                    }
                )

            ctx = {
                "office_hour": oh,
                "start_time_str": start_str,
                "courses": course_choices_inner,
                "duration_options": duration_options,
                "selected_course_id": course_id_str,
                "selected_duration": duration_str,
                "already_reserved_course_codes": my_reserved_course_codes_inner,
                "error": msg,
                "appointment_date": appointment_date,
                "week_start": week_start_iso,
                "day_code": day_code,
            }
            return render(
                request, "SchedulerApp/student/reservation_confirm.html", ctx
            )

        # validate time
        try:
            start_clock = datetime.datetime.strptime(start_str, "%H:%M").time()
        except ValueError:
            return render_with_error("Invalid start time.")

        # validate duration
        try:
            duration_minutes = int(duration_str)
        except ValueError:
            return render_with_error("Please choose a duration.")
        if duration_minutes not in (15, 30, 45, 60):
            return render_with_error("Invalid duration selected.")

        # validate course
        if not course_id_str:
            return render_with_error("Please select a course.")
        course_code = course_id_str

        # course must be a course for this OH AND the student must be enrolled
        student_is_enrolled = CourseModel.objects.filter(
            code=course_code,
            students__id=user.id,
        ).exists()
        is_linked_to_oh = oh.course_assignments.filter(
            course__code=course_code
        ).exists()
        if not (student_is_enrolled and is_linked_to_oh):
            return render_with_error(
                "You are not enrolled in the selected course for this office hour."
            )

        # per-course limit (any week)
        now = timezone.now()

        existing_for_course = ReservationModel.objects.filter(
            student_id=user.id,
            status=ReservationStatus.RESERVED,
            office_hour__course_assignments__course__code=course_code,
            start_time__gte=now,  # ONLY future reservations block
        ).exists()

        if existing_for_course:
            return render_with_error(
                "You already have an upcoming reservation for this course."
            )

        # --- build full datetimes for this reservation (correct week/day) ---
        start_dt = datetime.datetime.combine(appointment_date, start_clock)
        start_dt = timezone.make_aware(
            start_dt, timezone.get_current_timezone()
        )
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

        # office hour window bounds for that same date
        oh_start_dt = datetime.datetime.combine(appointment_date, oh.start_time)
        oh_end_dt = datetime.datetime.combine(appointment_date, oh.end_time)
        oh_start_dt = timezone.make_aware(
            oh_start_dt, timezone.get_current_timezone()
        )
        oh_end_dt = timezone.make_aware(
            oh_end_dt, timezone.get_current_timezone()
        )

        if start_dt < oh_start_dt or end_dt > oh_end_dt:
            return render_with_error(
                "Selected time block is outside of office hours."
            )

        # --- check overlapping reservations for this OH on that date ---
        overlap = (
            ReservationModel.objects
            .filter(
                office_hour=oh,
                status=ReservationStatus.RESERVED,
                start_time__lt=end_dt,
                end_time__gt=start_dt,
            )
            .exists()
        )
        if overlap:
            return render_with_error(
                "This time block is already reserved."
            )

        # create reservation
        selected_course = CourseModel.objects.get(code=course_code)

        Reservation.create_reservation(
            student_id=user.id,
            office_hour_id=oh.office_hour_id,
            course_id=selected_course.code,
            start_time=start_dt,
            end_time=end_dt,
            status=ReservationStatus.RESERVED,
        )

        # redirect back to OH grid for the same week
        return redirect(
            f"/student/office_hours/?week_start={week_start_iso}&success=Reservation+created+successfully"
        )



class CancelReservationView(View):
    """
    Allows a student to cancel their own reservation if more than 24 hours
    remain before the start time.
    """
    def post(self, request, reservation_id):
        # Ensure logged in
        user = User.get_by_id(request.session.get("user_id"))
        if not user:
            return redirect("login")

        if user.role != UserRole.STUDENT:
            return HttpResponseForbidden("Only students can cancel reservations.")

        # Reservation must belong to this student
        reservation = get_object_or_404(
            ReservationModel,
            pk=reservation_id,
            student_id=user.id,
        )

        # 24-hour rule
        now = timezone.now()
        delta = reservation.start_time - now
        if delta.total_seconds() <= 24 * 3600:
            base_url = reverse("student_upcoming_reservation")
            return redirect(
                f"{base_url}?error=Reservations+can+only+be+cancelled+at+least+24+hours+before+they+start."
            )

        # Use your Reservation helper to cancel
        Reservation().cancel_reservation(reservation_id)

        base_url = reverse("student_upcoming_reservation")
        return redirect(
            f"{base_url}?success=Reservation+cancelled+successfully."
        )

    # If someone hits this via GET, just send them back
    def get(self, request, reservation_id):
        return redirect("student_upcoming_reservation")





# =============================================================================
# Herlper methods
# =============================================================================

def build_office_hours_week_context(user, request, base_queryset=None):

    # ---- Filters from query string ----
    course_code = request.GET.get("course", "").strip()
    staff_email = request.GET.get("staff", "").strip()

    # ---- Base queryset ----
    oh_qs = (
        base_queryset
        or OfficeHourModel.objects.all()
    )
    oh_qs = oh_qs.filter(status="APPROVED")
    oh_qs = oh_qs.select_related("staff_id").prefetch_related("course_assignments__course")

    # Apply filters
    if course_code:
        oh_qs = oh_qs.filter(course_assignments__course__code=course_code)
    if staff_email:
        oh_qs = oh_qs.filter(staff_id__email=staff_email)

    oh_qs = oh_qs.order_by("day_of_week", "start_time")

    # ---- Course dropdown options ----
    course_qs = (
        CourseModel.objects
        .filter(office_hours__isnull=False)
        .distinct()
        .order_by("code")
    )
    courses = [
        {
            "code": c.code,
            "label": f"{c.code} - {c.name} ({c.section})",
        }
        for c in course_qs
    ]

    # ---- Staff dropdown options ----
    staff_qs = (
        UserModel.objects
        .filter(officehourmodel__isnull=False)
        .filter(role__in=[UserRole.TA, UserRole.INSTRUCTOR])
        .distinct()
        .order_by("last_name", "first_name")
    )
    staff_list = [
        {
            "email": s.email,
            "label": f"{s.first_name} {s.last_name} ({s.email})",
        }
        for s in staff_qs
    ]

    # ---- Time range (min/max across filtered OHs) ----
    if oh_qs.exists():
        min_start = min(oh.start_time for oh in oh_qs)
        max_end = max(oh.end_time for oh in oh_qs)
    else:
        # Default grid 08:00–18:00 if no office hours
        min_start = datetime.time(8, 0)
        max_end = datetime.time(18, 0)

    def round_down_to_15(t: datetime.time) -> datetime.time:
        return t.replace(
            minute=(t.minute // 15) * 15,
            second=0,
            microsecond=0,
        )

    def round_up_to_15(t: datetime.time) -> datetime.time:
        total_minutes = t.hour * 60 + t.minute
        total_minutes = ((total_minutes + 14) // 15) * 15
        hour = total_minutes // 60
        minute = total_minutes % 60
        if hour >= 24:
            hour = 23
            minute = 45
        return t.replace(hour=hour, minute=minute, second=0, microsecond=0)

    start_t = round_down_to_15(min_start)
    end_t = round_up_to_15(max_end)

    # ---- Build 15-minute time slots ----
    slots = []
    cur_dt = datetime.datetime.combine(datetime.date.today(), start_t)
    end_dt = datetime.datetime.combine(datetime.date.today(), end_t)

    while cur_dt <= end_dt:
        slots.append(cur_dt.time())
        cur_dt += datetime.timedelta(minutes=15)

    time_slots = [t.strftime("%H:%M") for t in slots]

    # ---- Days for columns (Mon–Fri) ----
    days = [
        {"code": "M", "label": "Mon"},
        {"code": "T", "label": "Tue"},
        {"code": "W", "label": "Wed"},
        {"code": "R", "label": "Thu"},
        {"code": "F", "label": "Fri"},
    ]

    # Normalize possible full names to your M/T/W/R/F codes
    day_code_map = {
        "Monday": "M",
        "Tuesday": "T",
        "Wednesday": "W",
        "Thursday": "R",
        "Friday": "F",
        "Saturday": "Sa",
        "Sunday": "Su",
    }

    # ---- Map (day_code, time_str) -> list of OH entries ----
    cell_map = defaultdict(list)

    for oh in oh_qs:
        staff_name = f"{oh.staff_id.first_name} {oh.staff_id.last_name}"

        # Courses via CourseOfficeHourAssignmentModel
        assigned_courses = [
            f"{a.course.code} ({a.course.section})"
            for a in oh.course_assignments.all()
        ]

        day_code = oh.day_of_week
        if day_code in day_code_map:
            day_code = day_code_map[day_code]

        # Covered slots for this office hour
        oh_start_dt = datetime.datetime.combine(
            datetime.date.today(),
            round_down_to_15(oh.start_time),
        )
        oh_end_dt = datetime.datetime.combine(
            datetime.date.today(),
            round_up_to_15(oh.end_time),
        )

        cur = oh_start_dt
        while cur < oh_end_dt:
            key = (day_code, cur.time().strftime("%H:%M"))
            cell_map[key].append(
                {
                    "staff_name": staff_name,
                    "courses": assigned_courses,
                    "location": oh.location,
                    "status": oh.status,
                }
            )
            cur += datetime.timedelta(minutes=15)

    # ---- Build rows for template ----
    rows = []
    for ts in time_slots:
        row_cells = []
        for d in days:
            entries = cell_map.get((d["code"], ts), [])
            tooltip_parts = []
            for e in entries:
                courses_str = ", ".join(e["courses"]) if e["courses"] else "No courses"
                tooltip_parts.append(f"{e['staff_name']} — {courses_str}")
            tooltip = " | ".join(tooltip_parts)
            row_cells.append(
                {
                    "day_code": d["code"],
                    "entries": entries,
                    "tooltip": tooltip,
                }
            )
        rows.append(
            {
                "time": ts,
                "cells": row_cells,
            }
        )

    context = {
        "user": user,
        "days": days,
        "rows": rows,
        "courses": courses,
        "staff_list": staff_list,
        "selected_course": course_code,
        "selected_staff": staff_email,
    }
    return context

from collections import defaultdict
import datetime

def build_student_office_hours_week_context(user, request):
    """
    Build weekly grid of office hours for a STUDENT.

    - Only office hours for courses the student is enrolled in.
    - Only APPROVED office hours.
    - Time is broken into 15-minute blocks.
    - Blocks that have any reservation in that week are marked as reserved.
    - Supports week navigation with ?week_start=YYYY-MM-DD
    """

    student_id = user.id

    # ---------- week navigation ----------
    week_start_str = (request.GET.get("week_start") or "").strip()
    if week_start_str:
        try:
            week_start = datetime.datetime.strptime(
                week_start_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            today = timezone.localdate()
            week_start = today - datetime.timedelta(days=today.weekday())
    else:
        today = timezone.localdate()
        week_start = today - datetime.timedelta(days=today.weekday())

    week_end = week_start + datetime.timedelta(days=4)  # Mon-Fri
    prev_week_start = week_start - datetime.timedelta(days=7)
    next_week_start = week_start + datetime.timedelta(days=7)

    week_label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d')}"
    week_start_iso = week_start.isoformat()
    prev_week_start_iso = prev_week_start.isoformat()
    next_week_start_iso = next_week_start.isoformat()

    # ---------- course filter ----------
    course_code = (request.GET.get("course") or "").strip()

    # All courses this student is enrolled in (for dropdown)
    student_courses_qs = (
        CourseModel.objects
        .filter(students__id=student_id)
        .distinct()
        .order_by("code")
    )

    courses = [
        {
            "code": c.code,
            "label": f"{c.code} - {c.name} ({c.section})",
        }
        for c in student_courses_qs
    ]

    # Courses actually used to filter OHs
    if course_code:
        filtered_courses_qs = student_courses_qs.filter(code=course_code)
    else:
        filtered_courses_qs = student_courses_qs

    # Weekday columns with actual dates
    weekday_info = [
        ("M", "Mon", 0),
        ("T", "Tue", 1),
        ("W", "Wed", 2),
        ("R", "Thu", 3),
        ("F", "Fri", 4),
    ]
    days = []
    for code, label, offset in weekday_info:
        d = week_start + datetime.timedelta(days=offset)
        days.append(
            {
                "code": code,
                "label": f"{label} {d.strftime('%m/%d')}",
                "date": d,
                "date_str": d.isoformat(),
            }
        )

    # If student has no courses at all, we can stop here
    if not filtered_courses_qs.exists():
        return {
            "user": user,
            "days": days,
            "rows": [],
            "courses": courses,
            "selected_course": course_code,
            "week_start": week_start_iso,
            "prev_week_start": prev_week_start_iso,
            "next_week_start": next_week_start_iso,
            "week_label": week_label,
        }

    # ---------- office hours for student's courses ----------
    oh_qs = (
        OfficeHourModel.objects
        .filter(
            status="APPROVED",
            course_assignments__course__in=filtered_courses_qs,
        )
        .select_related("staff_id")
        .prefetch_related("course_assignments__course", "reservations")
        .distinct()
    )

    if not oh_qs.exists():
        return {
            "user": user,
            "days": days,
            "rows": [],
            "courses": courses,
            "selected_course": course_code,
            "week_start": week_start_iso,
            "prev_week_start": prev_week_start_iso,
            "next_week_start": next_week_start_iso,
            "week_label": week_label,
        }

    # ---------- time grid bounds ----------
    min_start = min(oh.start_time for oh in oh_qs)
    max_end = max(oh.end_time for oh in oh_qs)

    def round_down_to_15(t: datetime.time) -> datetime.time:
        return t.replace(
            minute=(t.minute // 15) * 15,
            second=0,
            microsecond=0,
        )

    def round_up_to_15(t: datetime.time) -> datetime.time:
        total_minutes = t.hour * 60 + t.minute
        total_minutes = ((total_minutes + 14) // 15) * 15
        hour = total_minutes // 60
        minute = total_minutes % 60
        if hour >= 24:
            hour = 23
            minute = 45
        return t.replace(hour=hour, minute=minute, second=0, microsecond=0)

    start_t = round_down_to_15(min_start)
    end_t = round_up_to_15(max_end)

    time_slots = []
    cur_dt = datetime.datetime.combine(datetime.date.today(), start_t)
    end_dt_all = datetime.datetime.combine(datetime.date.today(), end_t)
    while cur_dt <= end_dt_all:
        time_slots.append(cur_dt.time().strftime("%H:%M"))
        cur_dt += datetime.timedelta(minutes=15)

    # ---------- map office hours to cells ----------
    day_code_map = {
        "Monday": "M",
        "Tuesday": "T",
        "Wednesday": "W",
        "Thursday": "R",
        "Friday": "F",
    }

    # reservations only in the currently-viewed week
    week_res_start = week_start
    week_res_end = week_start + datetime.timedelta(days=6)

    cell_map = defaultdict(list)

    # set of courses this student has overall (for labelling)
    student_courses_set = set(student_courses_qs)

    for oh in oh_qs:
        staff_name = ""
        if oh.staff_id:
            staff_name = f"{oh.staff_id.first_name} {oh.staff_id.last_name}".strip() or "Staff"
        else:
            staff_name = "Staff"

        day_code = day_code_map.get(oh.day_of_week)
        if not day_code:
            continue

        # reservations for this OH in this week
        reserved_slots = set()
        res_qs = (
            oh.reservations
            .filter(
                status=ReservationStatus.RESERVED,
                start_time__date__gte=week_res_start,
                start_time__date__lte=week_res_end,
            )
        )

        for res in res_qs:
            res_start_dt = timezone.localtime(res.start_time)
            res_end_dt = timezone.localtime(res.end_time)

            res_start = round_down_to_15(res_start_dt.time())
            res_end = round_up_to_15(res_end_dt.time())

            cur = datetime.datetime.combine(datetime.date.today(), res_start)
            end_res = datetime.datetime.combine(datetime.date.today(), res_end)
            while cur < end_res:
                reserved_slots.add(cur.time().strftime("%H:%M"))
                cur += datetime.timedelta(minutes=15)

        # all courses for this OH that the student is actually in
        oh_courses_for_student = [
            ca.course
            for ca in oh.course_assignments.all()
            if ca.course in student_courses_set
        ]
        if not oh_courses_for_student:
            continue

        course_labels = [
            f"{c.code} - {c.name} ({c.section})"
            for c in oh_courses_for_student
        ]

        cur = datetime.datetime.combine(datetime.date.today(), oh.start_time)
        oh_end_dt = datetime.datetime.combine(datetime.date.today(), oh.end_time)
        while cur < oh_end_dt:
            ts = cur.time().strftime("%H:%M")

            entry = {
                "office_hour_id": oh.office_hour_id,
                "staff_name": staff_name,
                "location": oh.location,
                "courses": course_labels,
                "start_time_str": ts,
                "is_reserved": ts in reserved_slots,
            }
            cell_map[(day_code, ts)].append(entry)

            cur += datetime.timedelta(minutes=15)

    # ---------- build rows for template ----------
    rows = []
    for ts in time_slots:
        row_cells = []
        for d in days:
            entries = cell_map.get((d["code"], ts), [])
            row_cells.append({"day_code": d["code"], "entries": entries})
        rows.append({"time": ts, "cells": row_cells})

    return {
        "user": user,
        "days": days,
        "rows": rows,
        "courses": courses,
        "selected_course": course_code,
        "week_start": week_start_iso,
        "prev_week_start": prev_week_start_iso,
        "next_week_start": next_week_start_iso,
        "week_label": week_label,
    }

