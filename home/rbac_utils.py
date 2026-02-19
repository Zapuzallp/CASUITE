"""
Role-Based Access Control (RBAC) Utilities for Attendance Module

This module provides helper functions to check user permissions and access levels
for the attendance management system.
"""

from django.contrib.auth.models import User


def get_user_attendance_access_level(user):
    """
    Determine user's access level for attendance records.
    
    Returns:
        dict: {
            'level': 'global' | 'branch' | 'self' | 'none',
            'can_view': bool,
            'can_add': bool,
            'can_edit': bool,
            'can_delete': bool,
            'branch': OfficeDetails or None
        }
    """
    access = {
        'level': 'none',
        'can_view': False,
        'can_add': False,
        'can_edit': False,
        'can_delete': False,
        'branch': None
    }
    
    # Superuser has full access
    if user.is_superuser:
        access.update({
            'level': 'global',
            'can_view': True,
            'can_add': True,
            'can_edit': True,
            'can_delete': True
        })
        return access
    
    # Admin (is_staff without employee profile) has full access
    if user.is_staff and not hasattr(user, 'employee'):
        access.update({
            'level': 'global',
            'can_view': True,
            'can_add': True,
            'can_edit': True,
            'can_delete': True
        })
        return access
    
    # Check Employee profile
    try:
        employee = user.employee
        
        # Branch Manager
        if employee.role == 'BRANCH_MANAGER':
            # Check for global attendance permission
            if user.has_perm('home.can_manage_all_attendance'):
                access.update({
                    'level': 'global',
                    'can_view': True,
                    'can_add': True,
                    'can_edit': True,
                    'can_delete': False  # Only superuser/admin can delete
                })
            else:
                # Branch-level access
                access.update({
                    'level': 'branch',
                    'can_view': True,
                    'can_add': True,
                    'can_edit': True,
                    'can_delete': False,
                    'branch': employee.office_location
                })
            return access
        
        # Staff (Normal Employee)
        if employee.role == 'STAFF':
            access.update({
                'level': 'self',
                'can_view': True,  # Can view own records
                'can_add': False,
                'can_edit': False,
                'can_delete': False
            })
            return access
            
    except Exception:
        pass
    
    return access


def can_user_view_attendance(user, attendance_record):
    """
    Check if user can view a specific attendance record.
    
    Args:
        user: User object
        attendance_record: Attendance object
        
    Returns:
        bool: True if user can view the record
    """
    access = get_user_attendance_access_level(user)
    
    if not access['can_view']:
        return False
    
    if access['level'] == 'global':
        return True
    
    if access['level'] == 'branch':
        try:
            return attendance_record.user.employee.office_location == access['branch']
        except Exception:
            return False
    
    if access['level'] == 'self':
        return attendance_record.user == user
    
    return False


def can_user_edit_attendance(user, attendance_record):
    """
    Check if user can edit a specific attendance record.
    
    Args:
        user: User object
        attendance_record: Attendance object
        
    Returns:
        bool: True if user can edit the record
    """
    access = get_user_attendance_access_level(user)
    
    if not access['can_edit']:
        return False
    
    if access['level'] == 'global':
        return True
    
    if access['level'] == 'branch':
        try:
            return attendance_record.user.employee.office_location == access['branch']
        except Exception:
            return False
    
    return False


def filter_attendance_queryset(user, queryset):
    """
    Filter attendance queryset based on user's access level.
    
    Args:
        user: User object
        queryset: Attendance queryset
        
    Returns:
        Filtered queryset
    """
    access = get_user_attendance_access_level(user)
    
    if access['level'] == 'global':
        return queryset
    
    if access['level'] == 'branch' and access['branch']:
        return queryset.filter(user__employee__office_location=access['branch'])
    
    if access['level'] == 'self':
        return queryset.filter(user=user)
    
    return queryset.none()


def get_accessible_employees(user):
    """
    Get list of employees whose attendance the user can access.
    
    Args:
        user: User object
        
    Returns:
        User queryset
    """
    access = get_user_attendance_access_level(user)
    
    if access['level'] == 'global':
        return User.objects.filter(is_active=True, is_staff=True)
    
    if access['level'] == 'branch' and access['branch']:
        return User.objects.filter(
            is_active=True,
            is_staff=True,
            employee__office_location=access['branch']
        )
    
    if access['level'] == 'self':
        return User.objects.filter(id=user.id)
    
    return User.objects.none()
