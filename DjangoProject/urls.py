from django.urls import path
from SchedulerApp import views





urlpatterns = [
    # Main / Root
    # ALWAYS go to login when opening the site
    path("", views.SchedulerHomeView.as_view(), name="root_redirect"),



    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),


    # ADMIN

    path("admin/", views.AdminHomeView.as_view(), name="admin_home"),


    # Staff
    path("admin/staff/", views.AdminStaffListView.as_view(), name="admin_staff_list"),
    path("admin/staff/create/", views.AdminStaffCreateView.as_view(), name="admin_staff_create"),
    path("admin/staff/<int:staff_id>/edit/",views.AdminStaffEditView.as_view(),name="admin_staff_edit",),

    path("admin/staff/<int:staff_id>/delete/", views.AdminStaffDeleteView.as_view(), name="admin_staff_delete"),

    path("admin/office_hours/", views.AdminOfficeHoursView.as_view(), name="admin_office_hours"),
    # Courses
    path("admin/courses/", views.AdminCourseListView.as_view(), name="admin_course_list"),
    path("admin/courses/create/", views.AdminCourseCreateView.as_view(), name="admin_course_create"),
    path("admin/courses/<int:course_id>/delete/", views.AdminCourseDeleteView.as_view(), name="admin_course_delete"),

    path("admin/courses/<int:course_id>/edit/", views.AdminCourseEditView.as_view(), name="edit_course"),


    # Sections & office hours placeholders (needed for URL existence)
    path(
        "admin/courses/<int:course_id>/sections/assign_staff/",
        views.AdminCourseSectionAssignTaView.as_view(),
        name="admin_course_section_assign_ta",
    ),
path(
        "admin/courses/<int:course_id>/delete/",
        views.AdminCourseDeleteView.as_view(),
        name="delete_course",
    ),

    # INSTRUCTOR

# Instructor Home
    path("instructor/", views.InstructorHomeView.as_view(), name="instructor_home"),

    # Office Hours
    path("instructor/office-hours/cancel/", views.InstructorCancelOfficeHoursView.as_view(), name="instructor_cancel_office_hours"),

    path(
        "instructor/courses/office_hours/",
        views.InstructorOfficeHoursView.as_view(),
        name="instructor_office_hours"
    ),

    path(
        "instructor/courses/<int:course_id>/office_hours/<int:hour_id>/approve/",
        views.InstructorOfficeHourApproveView.as_view(),
        name="instructor_office_hour_approve"
    ),

    # Students
    path(
        "instructor/courses/<int:course_id>/students/",
        views.InstructorStudentListView.as_view(),
        name="instructor_student_list"
    ),
    path(
        "instructor/courses/<int:course_id>/students/create/",
        views.InstructorStudentCreateView.as_view(),
        name="instructor_student_create"
    ),
    path(
        "instructor/courses/<int:course_id>/students/manage/",
        views.InstructorStudentManageView.as_view(),
        name="instructor_student_manage"
    ),
    path(
        "instructor/courses/<int:course_id>/students/upload/",
        views.InstructorStudentUploadView.as_view(),
        name="instructor_student_upload"
    ),
    path(
        "instructor/courses/<int:course_id>/students/<int:student_id>/edit/",
        views.InstructorStudentEditView.as_view(),
        name="instructor_student_edit"
    ),

    path(
        "instructor/reports/tardy/",
        views.InstructorReportsView.as_view(),
        name="instructor_reports"
    ),

path(
        "staff/reservations/passed",
        views.InstructorReportsView.as_view(),
        name="reservations_passed"
    ),
    # Upcoming Reservations
    path(
        "instructor/pending/",
        views.InstructorPendingOfficeHoursView.as_view(),
        name="instructor_pending_office_hours"
    ),
    path(
        "instructor/office_hours/approve/<int:pk>/",
        views.InstructorOfficeHourApproveView.as_view(),
        name="instructor_approve_office_hour"
    ),
    path(
        "instructor/office_hours/deny/<int:pk>/",
        views.InstructorOfficeHourDenyView.as_view(),
        name="instructor_deny_office_hour"
    ),

    path("staff/record_attendance/", views.StaffRecordAttendanceView.as_view(), name="record_attendance"),

# STAFF (shared TA + Instructor)

path(
    "staff/office_hours/propose/",
    views.StaffProposeOfficeHoursView.as_view(),
    name="staff_office_hours_propose",
),

path(
    "staff/upcoming_reservations/",
    views.StaffUpcomingReservationsView.as_view(),
    name="staff_upcoming_reservations",
),

    # ta

    path("ta/", views.TAHomeView.as_view(), name="ta_home"),

    path("ta/office_hours/", views.TAOfficeHoursView.as_view(), name="ta_office_hours"),
    path("ta/office-hours/denied/clear/", views.TAClearDeniedOfficeHoursView.as_view(), name="ta_clear_denied_office_hours"),


    path("ta/office_hours/<int:course_id>/", views.TAOfficeHoursForCourseView.as_view(), name="ta_office_hours_for_course"),


    # STUDENT
    path("student/", views.StudentHomeView.as_view(), name="student_home"),
    path("student/setup/", views.SetupView.as_view(), name="setup"),
    path("student/office_hours/", views.StudentOfficeHourView.as_view(), name="student_office_hours"),
    path(
        "student/reservations/",
        views.StudentUpcomingReservationView.as_view(),
        name="student_upcoming_reservation",
    ),
    path(
        "student/reservations/<int:reservation_id>/cancel/",
        views.CancelReservationView.as_view(),
        name="cancel_reservation",
    ),
    path("student/office_hours/reserve/<int:office_hour_id>/",
         views.CreateReservationView.as_view(),
         name="create_reservation"),
    # ReservationModel create + cancel
    path(
        "reservation/create/<int:office_hour_id>/",
        views.CreateReservationView.as_view(),
        name="reservation_create"
    ),
    path(
        "reservation/cancel/<int:reservation_id>/",
        views.CancelReservationView.as_view(),
        name="reservation_cancel"
    ),
]
