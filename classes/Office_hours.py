from SchedulerApp.models import OfficeHourModel, CourseOfficeHourAssignmentModel
from django.core.exceptions import ObjectDoesNotExist


class Office_hours: # must match your import

    # Constructor
    def __init__(
            self,
            staff_id=None,
            day_of_week=None,
            course_ids=None,
            start_time=None,
            end_time=None,
            location=None,
            status=None
    ):
        self.staff_id = staff_id
        self.day_of_week = day_of_week
        self.course_ids = course_ids
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.status = status


    @staticmethod
    def propose(staff_id, day_of_week, course_ids, start_time, end_time, location, status="PENDING"):

        office_hour = OfficeHourModel.objects.create(
            staff_id_id=staff_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            location=location,
            status=status
        )
        for course_id in course_ids:
            course_to_office_hour = CourseOfficeHourAssignmentModel.objects.create(
                office_hour=office_hour,
                course_id=course_id,
            )

        return office_hour.office_hour_id

    def approve(self, office_hour_id):
        try:
            office_hour = OfficeHourModel.objects.get(office_hour_id=office_hour_id)
            office_hour.status = "APPROVED"
            office_hour.save()
            return True
        except OfficeHourModel.DoesNotExist:
            return False

    def deny(self, office_hour_id):
        try:
            office_hour = OfficeHourModel.objects.get(office_hour_id=office_hour_id)
            office_hour.status = "DENIED"
            office_hour.save()
            return True
        except OfficeHourModel.DoesNotExist:
            return False

    def delete(self, office_hour_id):
        try:
            office_hour = OfficeHourModel.objects.get(office_hour_id=office_hour_id)
            office_hour.delete()
            return True
        except OfficeHourModel.DoesNotExist:
            return False


    def _get(self, office_hour_id):
        try:
            return OfficeHourModel.objects.get(office_hour_id=office_hour_id)
        except ObjectDoesNotExist:
            raise KeyError("Office hour does not exist")

    def get_staff_id(self, office_hour_id):
        return self._get(office_hour_id).staff_id_id

    def get_courses(self, office_hour_id):
        return self._get(office_hour_id).courses.all()



    def get_start_time(self, office_hour_id):
        return self._get(office_hour_id).start_time

    def get_end_time(self, office_hour_id):
        return self._get(office_hour_id).end_time

    def get_day_of_week(self, office_hour_id):
        return self._get(office_hour_id).day_of_week
