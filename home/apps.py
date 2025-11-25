from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'

    def ready(self):
        import home.signals
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
        from home.jobs import auto_generate_tasks
        from django.conf import settings
        import sys
        # Avoid running scheduler in migrations, shell, etc
        if 'runserver' not in sys.argv and 'gunicorn' not in sys.argv:
            return
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), 'default')
        scheduler.add_job(
            'home.jobs:auto_generate_tasks',
            trigger='cron',
            hour=2,
            minute=0,
            id='auto_generate_tasks',
            replace_existing=True
        )
        register_events(scheduler)
        scheduler.start()
