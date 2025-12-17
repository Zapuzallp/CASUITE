from django.db import models

# Create your models here.
# office/models.py

from django.contrib.auth.models import User
from datetime import timedelta

# -----------------------------------------
# 1. Shift Table
# -----------------------------------------


class Shift(models.Model):
    DAY_CHOICES = (
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    )

    shift_name = models.CharField(max_length=100)
    shift_start_time = models.TimeField()
    shift_end_time = models.TimeField()
    # Maximum allowed duration in hours (e.g., 8.5 for 8 hours 30 mins)
    maximum_allowed_duration = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Maximum permitted duration in hours (example: 8.5)"
    )
    # Day off stored as a comma-separated string (e.g., 'Sat,Sun')
    days_off = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=DAY_CHOICES
    )

    def __str__(self):
        return self.shift_name

# -----------------------------------------
# 2. Employee Shift Table
# -----------------------------------------


class EmployeeShift(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='employee_shifts')
    shift = models.ForeignKey(
        Shift, on_delete=models.CASCADE, related_name='assigned_employees')
    # Optional: Track this assignment validity
    valid_from = models.DateField(auto_now_add=True)
    valid_to = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_username()} assigned to {self.shift.shift_name}"

# -----------------------------------------
# 3. Office Details Table
# -----------------------------------------


class OfficeDetails(models.Model):
    office_name = models.CharField(max_length=100)
    office_full_address = models.TextField()
    contact_person_name = models.CharField(max_length=100)
    office_contact_no = models.CharField(max_length=20)
    # Store Lat/Long as Decimal fields for accuracy
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True)

    def __str__(self):
        return self.office_name
