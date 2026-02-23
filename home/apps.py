from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'

    def ready(self):
        import home.signals
        # starting the scheduler
        from .scheduler.start_scheduler import start_scheduler
        start_scheduler()
