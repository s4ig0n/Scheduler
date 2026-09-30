from abc import ABC, abstractmethod
from classes.User import User


class Staff(User, ABC):
    #can be later change to non absttact methods if one implementation works for both classes (ta and Instructor)
    @abstractmethod
    def propose_office_hours(self, start, end, software):
        pass

    @abstractmethod
    def view_meeting_times(self, course_id):
        pass

    @abstractmethod
    def view_all_staff_office_hours(self, course_id):
        pass

    @abstractmethod
    def view_upcoming_reservations(self):
        pass

    @abstractmethod
    def record_attendance(self, reservation_id, attendance):
        pass