# uploads/tasks_scheduled.py
# Example scheduled tasks for Celery Beat using shared_task

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import UploadedFile, TranslatedEpub
from datetime import timedelta
from django.utils import timezone


@shared_task(name='uploads.cleanup_old_files')
def cleanup_old_files():
    """
    Remove files older than 30 days that haven't been accessed
    """
    cutoff_date = timezone.now() - timedelta(days=30)

    # Clean up uploaded files
    old_uploads = UploadedFile.objects.filter(
        uploaded_at__lt=cutoff_date
    )

    deleted_count = 0
    for upload in old_uploads:
        try:
            # Delete file from storage
            if upload.file:
                upload.file.delete()
            upload.delete()
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting file {upload.pk}: {e}")

    return f"Cleaned up {deleted_count} old files"


@shared_task(name='uploads.send_daily_statistics')
def send_daily_statistics():
    """
    Send daily statistics email to admin
    """
    today = timezone.now().date()

    # Get statistics
    uploads_today = UploadedFile.objects.filter(uploaded_at__date=today).count()
    translations_today = TranslatedEpub.objects.filter(translated_at__date=today).count()
    total_users = UploadedFile.objects.values('user').distinct().count()

    subject = f"EPUB Translator Daily Stats - {today}"
    message = f"""
Daily Statistics for EPUB Translator:

Uploads today: {uploads_today}
Translations today: {translations_today}
Total registered users: {total_users}

Generated at: {timezone.now()}
"""

    try:
        send_mail(
            subject,
            message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            [getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')],
            fail_silently=False,
        )
        return "Daily statistics sent successfully"
    except Exception as e:
        return f"Failed to send statistics: {e}"


@shared_task(name='uploads.check_failed_translations')
def check_failed_translations():
    """
    Check for translations that might need attention
    """
    # Find old translations that might need cleanup
    cutoff_time = timezone.now() - timedelta(days=7)
    old_translations = TranslatedEpub.objects.filter(
        translated_at__lt=cutoff_time
    )

    cleaned_count = 0
    for translation in old_translations:
        try:
            # Here you could implement cleanup logic
            # For now, just count them
            cleaned_count += 1
        except Exception as e:
            print(f"Error processing translation {translation.pk}: {e}")

    return f"Processed {cleaned_count} old translations"
