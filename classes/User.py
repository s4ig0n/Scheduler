
from abc import ABC, abstractmethod
from SchedulerApp.models import UserModel, UserRole
from django.core.exceptions import ObjectDoesNotExist
class User:

    def __init__(self, email, password, first_name, last_name, role=None):
        # Attributes you can inspect after creating the object
        self.model = None   # will hold the UserModel instance if created
        self.error = None   # will hold error message if something goes wrong

        try:
            # ---------- BASIC TYPE & EMPTY CHECKS ----------
            if not isinstance(email, str) or not email.strip():
                raise ValueError("Email cannot be empty and must be a string.")

            email = email.strip().lower()

            if "@" not in email:
                raise ValueError("Email must contain '@'.")

            if not isinstance(password, str) or not password:
                raise ValueError("Password cannot be empty.")

            if not isinstance(first_name, str) or not first_name.strip():
                raise ValueError("First name cannot be empty.")

            if not isinstance(last_name, str) or not last_name.strip():
                raise ValueError("Last name cannot be empty.")

            first_name = first_name.strip()
            last_name = last_name.strip()

            # ---------- LENGTH CHECKS USING MODEL META ----------
            fn_max = UserModel._meta.get_field("first_name").max_length
            ln_max = UserModel._meta.get_field("last_name").max_length
            pw_max = UserModel._meta.get_field("password").max_length

            if len(first_name) > fn_max:
                raise ValueError(f"First name cannot be longer than {fn_max} characters.")

            if len(last_name) > ln_max:
                raise ValueError(f"Last name cannot be longer than {ln_max} characters.")

            if len(password) > pw_max:
                raise ValueError(f"Password cannot be longer than {pw_max} characters.")

            # ---------- ROLE HANDLING (DEFAULT = STUDENT) ----------
            # Allow strings like "admin", "Admin", etc.
            role_map = {
                "admin": UserRole.ADMIN,
                "instructor": UserRole.INSTRUCTOR,
                "ta": UserRole.TA,
                "student": UserRole.STUDENT,
            }

            if role is None or str(role).strip() == "":
                raise ValueError("Invalid role. Must be Admin, Instructor, ta, or Student.")
            else:
                role_str = str(role).strip().lower()
                if role_str not in role_map:
                    raise ValueError("Invalid role. Must be Admin, Instructor, ta, or Student.")
                role_value = role_map[role_str]

            # ---------- UNIQUENESS CHECK (EMAIL) ----------
            if UserModel.objects.filter(email=email).exists():
                raise ValueError(f"A user with email {email} already exists.")

            # ---------- CREATE ROW IN DATABASE ----------
            user = UserModel.objects.create(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role_value,
            )

            # Store created model & fields on this object
            #self.model = user - not sure do we need it
            self.email = user.email
            self.first_name = user.first_name
            self.last_name = user.last_name
            self.role = user.role

        except ValueError as e:
            # validation problem
            self.error = str(e)

    @staticmethod
    def get_id_by_email(email):
        try:
            return UserModel.objects.get(email=email).id
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_by_id(id):
        try:
            return UserModel.objects.get(id=id)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def login(email, password):
        try:
            user = UserModel.objects.get(email=email)
            if user.password == password:
                return user
            return None
        except ObjectDoesNotExist:
            return None


    def get_first_name(self):
        try:
            user = UserModel.objects.get(email=self.email)
            return f"{user.first_name}"
        except ObjectDoesNotExist:
            return False


    def get_last_name(self):
        try:
            user = UserModel.objects.get(email=self.email)
            return f"{user.last_name}"
        except ObjectDoesNotExist:
            return ""

    def get_role(self):
        try:
            user = UserModel.objects.get(email=self.email)
            return user.role
        except ObjectDoesNotExist:
            return None
