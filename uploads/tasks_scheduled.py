from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import UploadedFile, TranslatedEpub, ExtractedEpub
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q


@shared_task(name='uploads.cleanup_old_files')
def cleanup_old_files():
    """
    Remove files older than 30 days that haven't been accessed
    and don't have any associated extracted content or translations
    """
    cutoff_date = timezone.now() - timedelta(days=30)

    old_uploads = UploadedFile.objects.filter(
        uploaded_at__lt=cutoff_date
    ).select_related()

    deleted_count = 0
    skipped_count = 0
    error_count = 0
    
    for upload in old_uploads:
        try:
            try:
                extracted = ExtractedEpub.objects.get(uploaded_file=upload)
                has_extracted = True
            except ExtractedEpub.DoesNotExist:
                extracted = None
                has_extracted = False
            
            has_translations = False
            if has_extracted:
                has_translations = TranslatedEpub.objects.filter(extracted_epub=extracted).exists()

            has_recent_activity = False
            if has_extracted:
                from .models import ReadingProgress
                recent_cutoff = timezone.now() - timedelta(days=7)
                has_recent_activity = ReadingProgress.objects.filter(
                    extracted_epub=extracted,
                    last_read_at__gte=recent_cutoff
                ).exists()
            
            if not has_extracted and not has_translations and not has_recent_activity:
                if upload.file:
                    upload.file.delete()
                upload.delete()
                deleted_count += 1
                print(f"Deleted old unused upload: {upload.title or upload.file.name}")
            else:
                skipped_count += 1
                print(f"Skipped upload with activity: {upload.title or upload.file.name}")
                
        except Exception as e:
            error_count += 1
            print(f"Error processing file {upload.pk}: {e}")

    result = f"Cleaned up {deleted_count} old files, skipped {skipped_count} active files"
    if error_count > 0:
        result += f", {error_count} errors occurred"
    
    return result


@shared_task(name='uploads.cleanup_orphaned_files')
def cleanup_orphaned_files():
    """
    Clean up uploaded files that don't have corresponding ExtractedEpub records
    and are older than 24 hours (to allow time for processing)
    """
    cutoff_time = timezone.now() - timedelta(hours=24)
    orphaned_uploads = UploadedFile.objects.filter(
        uploaded_at__lt=cutoff_time
    ).exclude(
        pk__in=ExtractedEpub.objects.values_list('uploaded_file_id', flat=True)
    )
    
    cleaned_count = 0
    error_count = 0
    
    for upload in orphaned_uploads:
        try:
            print(f"Cleaning up orphaned upload: ID={upload.pk}, "
                  f"file={upload.file.name}, uploaded={upload.uploaded_at}")
            
            if upload.file:
                upload.file.delete()
            upload.delete()
            cleaned_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"Error cleaning up orphaned file {upload.pk}: {e}")
    
    result = f"Cleaned up {cleaned_count} orphaned files"
    if error_count > 0:
        result += f", {error_count} errors occurred"
    
    return result


@shared_task(name='uploads.send_daily_statistics')
def send_daily_statistics():
    """
    Send daily statistics email to admin
    """
    today = timezone.now().date()

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
    Check for translations that might need attention and clean up failed ones
    """
    
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    failed_translations = TranslatedEpub.objects.filter(
        Q(translated_at__lt=cutoff_time) & (
            Q(translated_chapters__isnull=True) |
            Q(translated_chapters__exact='') |
            Q(translated_chapters__exact=[]) |
            Q(translated_title__exact='') |
            Q(translated_title__isnull=True)
        )
    )
    
    cleaned_count = 0
    error_count = 0
    
    for translation in failed_translations:
        try:

            print(f"Cleaning up failed translation: ID={translation.pk}, "
                  f"extracted_epub={translation.extracted_epub.title}, "
                  f"target_lang={translation.target_lang}, "
                  f"created={translation.translated_at}")

            has_content = (
                translation.translated_chapters and 
                len(translation.translated_chapters) > 0 and
                translation.translated_title
            )
            
            if not has_content:
                translation.delete()
                cleaned_count += 1
            else:
                print(f"Keeping translation ID={translation.pk} - has content")
                
        except Exception as e:
            error_count += 1
            print(f"Error processing translation {translation.pk}: {e}")
    very_old_cutoff = timezone.now() - timedelta(days=30)
    old_translations = TranslatedEpub.objects.filter(
        translated_at__lt=very_old_cutoff
    )
    
    old_count = old_translations.count()
    
    result_message = f"Cleaned up {cleaned_count} failed translations"
    if error_count > 0:
        result_message += f", {error_count} errors occurred"
    if old_count > 0:
        result_message += f", found {old_count} old translations (30+ days)"
    
    return result_message
