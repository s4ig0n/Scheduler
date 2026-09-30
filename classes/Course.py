from SchedulerApp.models import CourseModel
from django.core.exceptions import ObjectDoesNotExist

class Course:


    def __init__(self, course_code, course_name, course_section, instructor_id):
        # attributes to inspect after construction
        self.model = None  # will hold the CourseModel instance if created
        self.error = None  # will hold error message if something goes wrong

        try:
            # ---------- BASIC TYPE CHECKS ----------
            if not isinstance(course_code, int):
                raise ValueError("course_code must be an integer.")

            if not isinstance(instructor_id, int):
                raise ValueError("instructor_id must be an integer.")

            if not isinstance(course_name, str):
                raise ValueError("course_name must be a string.")

            if not isinstance(course_section, str):
                raise ValueError("course_section must be a string.")

            # ---------- LENGTH CHECKS (USING MODEL META) ----------
            name_max = CourseModel._meta.get_field("name").max_length
            section_max = CourseModel._meta.get_field("section").max_length

            course_name = course_name.strip()
            course_section = course_section.strip()

            if not course_name:
                raise ValueError("course_name cannot be empty.")
            if len(course_name) > name_max:
                raise ValueError(f"course_name cannot be longer than {name_max} characters.")

            if not course_section:
                raise ValueError("course_section cannot be empty.")
            if len(course_section) > section_max:
                raise ValueError(f"course_section cannot be longer than {section_max} characters.")

            # ---------- UNIQUENESS CHECK ----------
            # code is primary_key, so it must be unique
            if CourseModel.objects.filter(code=course_code).exists():
                raise ValueError(f"A course with code {course_code} already exists.")

            # ---------- CREATE THE ROW IN DB ----------
            course = CourseModel.objects.create(
                code=course_code,
                name=course_name,
                section=course_section,
                instructorId=instructor_id,
            )

            # store on self if success
            self.model = course

        except ValueError as e:
            # validation error – store message
            self.error = str(e)

        except Exception as e:
            # any unexpected error (DB, etc.)
            self.error = f"Unexpected error while creating course: {e}"


    @staticmethod
    def delete_course(course_code):
        try:
            course = CourseModel.objects.get(code=course_code)
            course.delete()
            return True

        except ObjectDoesNotExist:
            return False


    def get_course_section(self, course_code):
        try:
            course = CourseModel.objects.get(code=course_code)
            return course.section

        except ObjectDoesNotExist:
            raise KeyError("Course not found")


    def get_course_name(self, course_code):
        try:
            course = CourseModel.objects.get(code=course_code)
            return course.name

        except ObjectDoesNotExist:
            raise KeyError("Course not found")


    def get_course_instructor_id(self, course_code):
        try:
            course = CourseModel.objects.get(code=course_code)
            return course.instructorId

        except ObjectDoesNotExist:
            raise KeyError("Course not found")
