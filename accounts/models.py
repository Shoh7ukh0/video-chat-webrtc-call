from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser): ...


class ActiveUser(models.Model):
    username = models.CharField(max_length=125)
    is_admin = models.BooleanField(default=False)