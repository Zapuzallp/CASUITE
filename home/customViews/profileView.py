import os
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re
from home.models import Employee, Attendance,OfficeDetails
from django.utils import timezone


def validate_phone(phone):
    """Simple phone validation"""
    if not phone:
        return True
    # Remove spaces and hyphens
    phone_clean = re.sub(r'[\s\-]', '', phone)
    # Check if valid Indian or international number
    return bool(re.match(r'^(\+91)?[789]\d{9}$|^\+\d{10,15}$', phone_clean))


def validate_email_strict(email):
    """Strict email validation with better pattern matching"""
    if not email:
        return True

    # Check for @ symbol
    if '@' not in email:
        return False

    # Split into local and domain
    local, domain = email.split('@')

    # Local part can't be empty
    if not local:
        return False

    # Domain can't be empty
    if not domain:
        return False

    # Domain must have at least one dot
    if '.' not in domain:
        return False

    # Domain can't start or end with dot
    if domain.startswith('.') or domain.endswith('.'):
        return False

    # Split domain into parts
    domain_parts = domain.split('.')

    # TLD (last part) must be 2-6 letters only
    tld = domain_parts[-1]
    if len(tld) < 2 or len(tld) > 6:
        return False

    if not tld.isalpha():
        return False

    # Each domain part must be at least 2 characters
    for part in domain_parts:
        if len(part) < 2:
            return False

        # Domain parts should only contain letters, numbers, hyphens
        if not re.match(r'^[a-zA-Z0-9-]+$', part):
            return False

        # Can't start or end with hyphen
        if part.startswith('-') or part.endswith('-'):
            return False

    # Check for consecutive dots
    if '..' in domain:
        return False

    return True
@login_required
def profile_view(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        employee = None

    today = timezone.now().date()
    attendance = Attendance.objects.filter(user=request.user, date=today).first()

    duration = None
    current_duration = None
    attendance_status = "absent"

    if attendance:
        attendance_status = attendance.status if attendance.status else "absent"

        if attendance.clock_in and attendance.clock_out:
            diff = attendance.clock_out - attendance.clock_in
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            duration = f"{hours}h {minutes}m"
        elif attendance.clock_in and not attendance.clock_out:
            diff = timezone.now() - attendance.clock_in
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            current_duration = f"{hours}h {minutes}m"

    return render(request, 'view.html', {
        'employee': employee,
        'attendance': attendance,
        'duration': duration,
        'current_duration': current_duration,
        'attendance_status': attendance_status,
        'today': today,
    })


@login_required
def profile_edit(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'})

    if request.method == 'POST':
        errors = {}

        # Validate phone numbers
        personal_phone = request.POST.get('personal_phone', '')
        if personal_phone and not validate_phone(personal_phone):
            errors['personal_phone'] = 'Invalid phone number (should be 10 digits or +91XXXXXXXXXX)'

        work_phone = request.POST.get('work_phone', '')
        if work_phone and not validate_phone(work_phone):
            errors['work_phone'] = 'Invalid phone number (should be 10 digits or +91XXXXXXXXXX)'

        # Validate email with strict validation
        personal_email = request.POST.get('personal_email', '')
        if personal_email:
            # Check if email is valid
            if not validate_email_strict(personal_email):
                # Provide specific error messages
                if '@' not in personal_email:
                    errors['personal_email'] = 'Email must contain @ symbol'
                elif personal_email.count('@') != 1:
                    errors['personal_email'] = 'Email must have exactly one @ symbol'
                elif '.' not in personal_email.split('@')[-1]:
                    errors['personal_email'] = 'Email domain must contain a dot (.)'
                else:
                    domain = personal_email.split('@')[-1]
                    tld = domain.split('.')[-1] if '.' in domain else ''

                    if len(tld) < 2 or len(tld) > 6:
                        errors['personal_email'] = f'Invalid email extension "{tld}". Extension should be 2-6 letters'
                    elif not tld.isalpha():
                        errors[
                            'personal_email'] = f'Invalid email extension "{tld}". Extension should only contain letters'
                    else:
                        errors['personal_email'] = 'Invalid email format. Example: name@domain.com'
            else:
                # Additional check for common mistakes
                if personal_email.endswith('.comm'):
                    errors['personal_email'] = 'Invalid email extension ".comm". Did you mean .com?'
                elif personal_email.endswith('.c0m'):
                    errors['personal_email'] = 'Invalid email extension ".c0m". Did you mean .com?'
                elif personal_email.endswith('.con'):
                    errors['personal_email'] = 'Invalid email extension ".con". Did you mean .com?'
                elif personal_email.endswith('.om'):
                    errors['personal_email'] = 'Invalid email extension ".om". Did you mean .com?'

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        # Save data
        employee.designation = request.POST.get('designation', employee.designation)
        employee.personal_phone = personal_phone
        employee.work_phone = work_phone
        employee.personal_email = personal_email
        employee.address = request.POST.get('address', employee.address)

        # Handle office
        if hasattr(employee, 'office_location') and employee.office_location:
            if request.POST.get('office_name'):
                employee.office_location.office_name = request.POST.get('office_name')
            if request.POST.get('office_address'):
                employee.office_location.office_address = request.POST.get('office_address')
            employee.office_location.save()

        employee.save()

        return JsonResponse({
            'success': True,
            'employee': {
                'designation': employee.designation,
                'personal_phone': employee.personal_phone,
                'work_phone': employee.work_phone,
                'personal_email': employee.personal_email,
                'address': employee.address,
                'profile_pic_url': employee.profile_pic.url if employee.profile_pic else None,
            }
        })

    return render(request, 'view.html', {'employee': employee})

@login_required
def upload_profile_pic(request):
    """View for uploading profile picture (AJAX support)"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(user=request.user)
            pic = request.FILES.get('profile_pic')
            # No file
            if not pic:
                return JsonResponse({'success': False, 'error': 'No file provided'})

            # SIZE VALIDATION (2MB)
            if pic.size > 2 * 1024 * 1024:
                return JsonResponse({'success': False, 'error': 'Image must be less than 2MB'})

            # TYPE VALIDATION
            if not pic.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'Only image files allowed'})

            if not pic:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'No file provided'})
                return redirect(request.META.get('HTTP_REFERER', '/'))

            # Delete old profile picture if it exists
            if employee.profile_pic and employee.profile_pic.name:
                try:
                    if os.path.isfile(employee.profile_pic.path):
                        os.remove(employee.profile_pic.path)
                except Exception:
                    pass  # Ignore file deletion errors

            # Save new profile picture
            employee.profile_pic = pic
            employee.save()


            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'profile_pic_url': employee.profile_pic.url,
                    'message': 'Profile picture updated successfully'
                })

            return redirect(request.META.get('HTTP_REFERER', '/'))

        except Employee.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Employee not found'})
            return redirect('/')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect('/')