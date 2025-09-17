from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UploadedFile, ExtractedEpub, TranslatedEpub, AuditLog, ReadingProgress

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(validated_data['username'], validated_data['email'], validated_data['password'])
        return user

class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ('id', 'user', 'file', 'uploaded_at', 'title')
        read_only_fields = ('user', 'uploaded_at')

class ExtractedEpubSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedEpub
        fields = ('id', 'uploaded_file', 'title', 'metadata', 'chapters', 'images', 'extracted_at')
        read_only_fields = ('uploaded_file', 'extracted_at')

class TranslatedEpubSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslatedEpub
        fields = ('id', 'extracted_epub', 'source_lang', 'target_lang', 'translated_title', 'translated_metadata', 'translated_chapters', 'chapter_index', 'translated_at')
        read_only_fields = ('extracted_epub', 'translated_at')

class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = ('id', 'user', 'extracted_epub', 'current_chapter', 'current_position', 'progress_percentage', 'last_read_at', 'created_at')
        read_only_fields = ('user', 'last_read_at', 'created_at')

class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ('id', 'action', 'action_display', 'description', 'resource_type', 'resource_id', 'timestamp', 'ip_address', 'metadata')
        read_only_fields = ('id', 'timestamp', 'ip_address')
