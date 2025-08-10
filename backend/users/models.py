# from django.db import models
# from django.utils import timezone

# class User(models.Model):
#     """
#     Represents a user in the system.
#     """
#     email = models.EmailField(unique=True)
#     password_hash = models.CharField(max_length=255) 
#     role = models.CharField(max_length=50, default='user')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.email

#     class Meta:
#         verbose_name = "User"
#         verbose_name_plural = "Users"

# backend/users/models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser):
    """
    Represents a user in the system.
    """
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Add this line

    objects = MyUserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"