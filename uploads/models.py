from django.db import models

# Create your models here.

class UploadedFile(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    file = models.FileField(upload_to='epubs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title or self.file.name

class ExtractedEpub(models.Model):
    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(blank=True, null=True)
    chapters = models.JSONField(blank=True, null=True)  # list of {'title': str, 'content': str}
    images = models.JSONField(blank=True, null=True)  # list of image paths
    cover_image = models.CharField(max_length=500, blank=True, null=True)  # path to cover image
    extracted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extracted: {self.title}"

class TranslatedEpub(models.Model):
    extracted_epub = models.ForeignKey(ExtractedEpub, on_delete=models.CASCADE, related_name='translations')
    source_lang = models.CharField(max_length=10, default='auto')
    target_lang = models.CharField(max_length=10, default='pt')
    translated_title = models.CharField(max_length=255, blank=True)
    translated_metadata = models.JSONField(blank=True, null=True)
    translated_chapters = models.JSONField(blank=True, null=True)  # list of {'title': str, 'content': str}
    chapter_index = models.IntegerField(null=True, blank=True)  # None for full translation, index for single chapter
    translated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('extracted_epub', 'source_lang', 'target_lang', 'chapter_index')

    def __str__(self):
        if self.chapter_index is not None:
            return f"Translated Chapter {self.chapter_index}: {self.translated_title}"
        return f"Translated: {self.translated_title}"

class ReadingProgress(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    extracted_epub = models.ForeignKey(ExtractedEpub, on_delete=models.CASCADE)
    current_chapter = models.IntegerField(default=0)
    current_position = models.IntegerField(default=0)  # Character position within chapter
    progress_percentage = models.FloatField(default=0.0)  # Overall reading progress (0-100)
    last_read_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'extracted_epub')
        indexes = [
            models.Index(fields=['user', 'extracted_epub']),
            models.Index(fields=['last_read_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.extracted_epub.title} - {self.progress_percentage:.1f}%"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('upload', 'File Upload'),
        ('extract', 'Content Extraction'),
        ('translate', 'Translation'),
        ('download', 'File Download'),
        ('delete', 'File Deletion'),
        ('login', 'User Login'),
        ('register', 'User Registration'),
        ('read', 'Reading Progress'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    resource_id = models.IntegerField(null=True, blank=True)  # ID of the affected resource
    resource_type = models.CharField(max_length=50, blank=True)  # Type of resource (file, translation, etc.)
    metadata = models.JSONField(blank=True, null=True)  # Additional data
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
