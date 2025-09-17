import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'epub_api.settings')

app = Celery('epub_api')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule (optional - uncomment to enable)
# Uncomment the following lines and import crontab if you want scheduled tasks
# from celery.schedules import crontab
# app.conf.beat_schedule = {
#     'cleanup-old-files-daily': {
#         'task': 'uploads.tasks_scheduled.cleanup_old_files',
#         'schedule': crontab(hour=2, minute=0),  # Every day at 2 AM
#     },
#     'send-daily-stats': {
#         'task': 'uploads.tasks_scheduled.send_daily_statistics',
#         'schedule': crontab(hour=6, minute=0),  # Every day at 6 AM
#     },
#     'check-translations-weekly': {
#         'task': 'uploads.tasks_scheduled.check_failed_translations',
#         'schedule': crontab(day_of_week=1, hour=3, minute=0),  # Every Monday at 3 AM
#     },
# }

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
