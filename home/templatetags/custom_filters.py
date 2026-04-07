from django import template
from datetime import datetime

register = template.Library()

@register.filter
def timestamp_to_date(value):
    try:
        timestamp = int(value)
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except ValueError:
        return value

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def can_edit_client(client, user):
    """Check if user can edit a client (Partner role restrictions)"""
    if not hasattr(user, 'employee'):
        return True
    
    if user.employee.role != 'PARTNER':
        return True
    
    # Partner can edit ONLY IF they onboarded the client OR are assigned to the client
    return client.created_by == user or client.assigned_ca == user


@register.filter
def can_edit_lead(lead, user):
    """Check if user can edit a lead (Partner role restrictions)"""
    if not hasattr(user, 'employee'):
        return True
    
    if user.employee.role != 'PARTNER':
        return True
    
    # Partner can edit ONLY IF they onboarded the lead OR are assigned to the lead
    return lead.created_by == user or user in lead.assigned_to.all()


@register.filter
def can_edit_task(task, user):
    """Check if user can edit a task (Partner role restrictions)"""
    if not hasattr(user, 'employee'):
        return True
    
    if user.employee.role != 'PARTNER':
        return True
    
    # Partner can edit ONLY IF any of the following is true:
    # 1. Partner created the task
    # 2. Partner is assigned to the task
    # 3. Partner is assigned CA of the client related to the task
    # 4. Partner is in manage sequence (TaskAssignmentStatus) of the task
    from home.models import TaskAssignmentStatus
    
    is_creator = task.created_by == user
    is_assignee = user in task.assignees.all()
    is_client_ca = task.client.assigned_ca == user
    is_in_sequence = TaskAssignmentStatus.objects.filter(task=task, user=user).exists()
    
    return is_creator or is_assignee or is_client_ca or is_in_sequence


@register.filter
def can_edit_invoice(invoice, user):
    """Check if user can edit an invoice (Partner role restrictions)"""
    if not hasattr(user, 'employee'):
        return True
    
    if user.employee.role != 'PARTNER':
        return True
    
    # Partner can edit ONLY IF they are the client's assigned CA or created the invoice
    return invoice.client.assigned_ca == user or invoice.created_by == user


@register.filter
def can_edit_payment(payment, user):
    """Check if user can edit a payment (Partner role restrictions)"""
    if not hasattr(user, 'employee'):
        return True
    
    if user.employee.role != 'PARTNER':
        return True
    
    # Partner can edit ONLY IF they have access to the invoice
    # (created the payment OR created the invoice OR are the client's assigned CA)
    return (
        payment.created_by == user or 
        payment.invoice.created_by == user or 
        payment.invoice.client.assigned_ca == user
    )