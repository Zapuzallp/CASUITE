"""
Management command to process recurring tasks.
This command can be run via cronjob in production environments.

Usage:
    python manage.py run_recurring_tasks

Cronjob example (runs daily at 2:00 AM):
    0 2 * * * cd /path/to/project && /path/to/venv/bin/python manage.py run_recurring_tasks >> /var/log/recurring_tasks.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from home.models import Task, TaskRecurrence, Notification
from home.scheduler.recurrence import get_next_recurrence_date
from home.tasks.task_copy import copy_task
import logging
import sys

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process recurring tasks and create new tasks for overdue recurrences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating tasks',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
        parser.add_argument(
            '--no-notifications',
            action='store_true',
            help='Skip sending notifications',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        send_notifications = not options.get('no_notifications', False)
        
        start_time = timezone.now()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No tasks will be created\n'))
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 Starting recurring task processor at {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        )
        
        try:
            result = self.process_recurring_tasks(
                dry_run=dry_run,
                verbose=verbose,
                send_notifications=send_notifications
            )
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            # Summary
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✅ EXECUTION SUMMARY'))
            self.stdout.write('='*60)
            self.stdout.write(f'Started:  {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'Finished: {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'Duration: {duration:.2f} seconds')
            self.stdout.write(f'Tasks Created: {result["created"]}')
            self.stdout.write(f'Tasks Failed:  {result["failed"]}')
            self.stdout.write(f'Recurrences Processed: {result["processed"]}')
            
            if dry_run:
                self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No changes were made'))
            
            if result["failed"] > 0:
                self.stdout.write(self.style.ERROR(f'\n⚠️  {result["failed"]} tasks failed to create'))
                sys.exit(1)  # Exit with error code for cronjob monitoring
            else:
                self.stdout.write(self.style.SUCCESS('\n✅ All tasks processed successfully'))
                sys.exit(0)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ FATAL ERROR: {str(e)}')
            )
            logger.error(f'Fatal error in recurring task processor: {e}', exc_info=True)
            sys.exit(1)

    def process_recurring_tasks(self, dry_run=False, verbose=False, send_notifications=True):
        """
        Main processing logic for recurring tasks.
        Returns dict with statistics: created, failed, processed
        """
        now = timezone.now()
        
        if verbose:
            self.stdout.write(f'\n🔍 Scanning for overdue recurrences (current time: {now.strftime("%Y-%m-%d %H:%M:%S")})\n')
        
        # Fetch overdue recurrences
        recurrences = (
            TaskRecurrence.objects
            .filter(
                is_recurring=True,
                next_run_at__isnull=False,
                next_run_at__lte=now,
            )
            .select_related("task", "task__client", "task__created_by")
        )
        
        total_recurrences = recurrences.count()
        
        if total_recurrences == 0:
            self.stdout.write(self.style.WARNING('ℹ️  No overdue recurring tasks found'))
            return {'created': 0, 'failed': 0, 'processed': 0}
        
        self.stdout.write(
            self.style.WARNING(f'📋 Found {total_recurrences} overdue recurrence(s)\n')
        )
        
        total_created = 0
        total_failed = 0
        processed_count = 0

        for recurrence in recurrences:
            processed_count += 1
            
            if verbose:
                overdue_days = (now - recurrence.next_run_at).days
                self.stdout.write(
                    f'\n[{processed_count}/{total_recurrences}] Processing: {recurrence.task.task_title}'
                )
                self.stdout.write(f'  Client: {recurrence.task.client.client_name}')
                self.stdout.write(f'  Period: {recurrence.recurrence_period}')
                self.stdout.write(f'  Overdue: {overdue_days} days')
            
            try:
                if dry_run:
                    # Simulate without creating
                    tasks_to_create = 0
                    temp_next_run = recurrence.next_run_at
                    
                    while temp_next_run <= now:
                        tasks_to_create += 1
                        # Simulate next run calculation
                        temp_next_run = self._calculate_next_run(recurrence, temp_next_run)
                    
                    self.stdout.write(
                        self.style.WARNING(f'  Would create: {tasks_to_create} task(s)')
                    )
                    total_created += tasks_to_create
                    
                else:
                    # Actually create tasks
                    created_count = self._process_single_recurrence(
                        recurrence, 
                        now, 
                        verbose,
                        send_notifications
                    )
                    total_created += created_count
                    
                    if verbose:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ Created: {created_count} task(s)')
                        )
                        
            except Exception as e:
                total_failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Failed: {str(e)}')
                )
                logger.error(
                    f'Failed to process recurrence for task {recurrence.task.id}: {e}',
                    exc_info=True
                )
                
                # Send failure notification
                if send_notifications and not dry_run:
                    self._send_failure_notification(recurrence.task)
        
        return {
            'created': total_created,
            'failed': total_failed,
            'processed': processed_count
        }

    def _process_single_recurrence(self, recurrence, now, verbose, send_notifications):
        """
        Process a single recurrence and create all overdue tasks.
        Returns count of tasks created.
        """
        tasks_created = 0
        
        with transaction.atomic():
            while recurrence.next_run_at <= now:
                try:
                    # Create task for this expected occurrence
                    new_task = copy_task(
                        recurrence.task,
                        is_auto=True,
                        next_due_date=recurrence.next_run_at,
                    )
                    
                    # Track actual creation timestamp
                    created_at = timezone.now()
                    recurrence.last_auto_created_at = created_at
                    recurrence.task.last_auto_created_at = created_at
                    
                    # Move EXPECTED schedule forward
                    recurrence.next_run_at = get_next_recurrence_date(recurrence)
                    
                    tasks_created += 1
                    
                    # Send success notification
                    if send_notifications:
                        self._send_success_notification(recurrence.task, new_task)
                    
                    if verbose:
                        self.stdout.write(
                            f'    → Created: {new_task.task_title} (ID: {new_task.id})'
                        )
                    
                    logger.info(
                        f'Created recurring task: {new_task.task_title} '
                        f'(ID: {new_task.id}) for client {new_task.client.client_name}'
                    )
                    
                except Exception as task_error:
                    logger.error(
                        f'Failed to create recurring task for {recurrence.task.task_title}: {task_error}',
                        exc_info=True
                    )
                    # Move schedule forward even on failure to avoid infinite retry
                    recurrence.next_run_at = get_next_recurrence_date(recurrence)
                    raise
            
            # Persist once per recurrence
            recurrence.save(update_fields=[
                "last_auto_created_at",
                "next_run_at",
            ])
            recurrence.task.save(update_fields=[
                "last_auto_created_at",
            ])
        
        return tasks_created

    def _calculate_next_run(self, recurrence, current_next_run):
        """Calculate next run date for dry-run simulation"""
        from home.scheduler.recurrence import calculate_next_run
        anchor_date = recurrence.task.created_at.date()
        return calculate_next_run(
            anchor_date=anchor_date,
            base_date=current_next_run,
            recurrence_period=recurrence.recurrence_period,
        )

    def _send_success_notification(self, original_task, new_task):
        """Send success notification to creator and superusers"""
        try:
            recipients = set()
            
            if original_task.created_by:
                recipients.add(original_task.created_by)
            
            superusers = User.objects.filter(is_superuser=True)
            recipients.update(superusers)
            
            title = f"Recurring Task Created: {new_task.task_title}"
            message = (
                f"A new recurring task has been automatically created.\n\n"
                f"Task: {new_task.task_title}\n"
                f"Client: {new_task.client.client_name}\n"
                f"Service: {new_task.service_type}\n"
                f"Priority: {new_task.priority}\n"
                f"Status: {new_task.status}"
            )
            
            for user in recipients:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    tag='success',
                    target_url=f"/tasks/{new_task.id}/"
                )
        except Exception as e:
            logger.error(f'Failed to send success notification: {e}')

    def _send_failure_notification(self, original_task):
        """Send failure notification to creator and superusers"""
        try:
            recipients = set()
            
            if original_task.created_by:
                recipients.add(original_task.created_by)
            
            superusers = User.objects.filter(is_superuser=True)
            recipients.update(superusers)
            
            title = f"Recurring Task Creation Failed: {original_task.task_title}"
            message = (
                f"Failed to create recurring task automatically.\n\n"
                f"Original Task: {original_task.task_title}\n"
                f"Client: {original_task.client.client_name}\n"
                f"Please check the task configuration."
            )
            
            for user in recipients:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    tag='error',
                    target_url=f"/tasks/{original_task.id}/"
                )
        except Exception as e:
            logger.error(f'Failed to send failure notification: {e}')
