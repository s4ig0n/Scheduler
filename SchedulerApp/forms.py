from django import forms
# SchedulerApp/forms.py

from typing import Dict, Any
from SchedulerApp.models import UserModel, CourseModel

class UserForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ['email', 'first_name', 'last_name', 'role', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

class BaseForm:
    def __init__(self, data: Dict[str, Any] | None = None, instance=None):
        self.data = data or {}
        self.instance = instance
        self.errors: Dict[str, list[str]] = {}

    def add_error(self, field: str, message: str):
        self.errors.setdefault(field, []).append(message)

    def is_valid(self) -> bool:
        """
        Subclasses override _clean; this runs it and returns True/False.
        """
        self.errors = {}
        self._clean()
        return not self.errors

    def _clean(self):
        """Override in subclass."""
        pass


class UserForm(BaseForm):
    """
    Simple creator for staff / users (only used lightly).
    """

    def _clean(self):
        email = (self.data.get("email") or "").strip()
        password = (self.data.get("password") or "").strip()
        first_name = (self.data.get("first_name") or "").strip()
        last_name = (self.data.get("last_name") or "").strip()
        role = (self.data.get("role") or "").strip()

        if not email:
            self.add_error("email", "This field is required")
        elif "@" not in email:
            self.add_error("email", "Invalid email address")

        if not password:
            self.add_error("password", "This field is required")

        if not first_name:
            self.add_error("first_name", "This field is required")

        if not last_name:
            self.add_error("last_name", "This field is required")

        if not role:
            self.add_error("role", "This field is required")

        # unique email
        if email and UserModel.objects.filter(email=email).exists():
            self.add_error("email", "Account with this email already exists")

    def save(self) -> UserModel:
        if not self.is_valid():
            raise ValueError("Cannot save invalid form")

        return UserModel.objects.create(
            email=self.data["email"].strip(),
            password=self.data["password"],
            first_name=self.data["first_name"].strip(),
            last_name=self.data["last_name"].strip(),
            role=self.data["role"].strip(),
        )


class StaffEditForm(BaseForm):
    """
    Editing an existing staff UserModel (admin side).
    """

    def _clean(self):
        email = (self.data.get("email") or "").strip()
        first_name = (self.data.get("first_name") or "").strip()
        last_name = (self.data.get("last_name") or "").strip()

        # Only email is strictly required in acceptance tests, but
        # we give all three some validation.
        if not email:
            self.add_error("email", "This field is required")
        elif "@" not in email:
            self.add_error("email", "Invalid email address")

        if not first_name:
            self.add_error("first_name", "This field is required")

        if not last_name:
            self.add_error("last_name", "This field is required")

    def save(self) -> UserModel:
        if not self.instance:
            raise ValueError("StaffEditForm requires an instance")
        if not self.is_valid():
            raise ValueError("Cannot save invalid form")

        self.instance.email = self.data["email"].strip()
        self.instance.first_name = self.data["first_name"].strip()
        self.instance.last_name = self.data["last_name"].strip()
        self.instance.save()
        return self.instance


class StudentEditForm(BaseForm):
    """
    Editing a student (used by instructor edit student tests).
    """

    def _clean(self):
        email = (self.data.get("email") or "").strip()
        first_name = (self.data.get("first_name") or "").strip()
        last_name = (self.data.get("last_name") or "").strip()

        if not email:
            self.add_error("email", "This field is required")
        elif "@" not in email:
            # invalid email format – tests only check that response contains "error"
            self.add_error("email", "Invalid email format")

        if not first_name:
            self.add_error("first_name", "This field is required")

        if not last_name:
            self.add_error("last_name", "This field is required")

    def save(self) -> UserModel:
        if not self.instance:
            raise ValueError("StudentEditForm requires an instance")
        if not self.is_valid():
            raise ValueError("Cannot save invalid form")

        self.instance.email = self.data["email"].strip()
        self.instance.first_name = self.data["first_name"].strip()
        self.instance.last_name = self.data["last_name"].strip()
        self.instance.save()
        return self.instance


class CourseForm(BaseForm):
    """
    Used for /admin/courses/create/ acceptance tests.
    """

    def _clean(self):
        name = (self.data.get("name") or "").strip()
        code_raw = (self.data.get("code") or "").strip()
        section = (self.data.get("section") or "").strip()
        instructor_id_raw = (self.data.get("instructorId") or "").strip()

        if not name:
            self.add_error("name", "This field is required")

        if not code_raw:
            self.add_error("code", "This field is required")
        else:
            try:
                int(code_raw)
            except ValueError:
                self.add_error("code", "Code must be an integer")

        if not section:
            self.add_error("section", "This field is required")

        if not instructor_id_raw:
            self.add_error("instructorId", "This field is required")
        else:
            try:
                int(instructor_id_raw)
            except ValueError:
                self.add_error("instructorId", "InstructorId must be an integer")

        # Duplicate code check – tests look for substring "already exists"
        if code_raw and code_raw.isdigit():
            code_int = int(code_raw)
            if CourseModel.objects.filter(code=code_int).exists():
                self.add_error("code", "Course with this code already exists")

    def save(self) -> CourseModel:
        if not self.is_valid():
            raise ValueError("Cannot save invalid course form")

        return CourseModel.objects.create(
            code=int(self.data["code"]),
            name=self.data["name"].strip(),
            section=self.data["section"].strip(),
            instructorId=int(self.data["instructorId"]),
        )

