from django.contrib import admin

# Register your models here.
# office/admin.py

from .models import Shift, EmployeeShift, OfficeDetails


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('shift_name', 'shift_start_time',
                    'shift_end_time', 'maximum_allowed_duration', 'days_off')


@admin.register(EmployeeShift)
class EmployeeShiftAdmin(admin.ModelAdmin):
    list_display = ('user', 'shift', 'valid_from', 'valid_to')
    list_filter = ('shift', 'valid_from', 'valid_to')


@admin.register(OfficeDetails)
class OfficeDetailsAdmin(admin.ModelAdmin):
    list_display = ('office_name', 'contact_person_name',
                    'office_contact_no', 'latitude', 'longitude')
    search_fields = ('office_name', 'contact_person_name')
