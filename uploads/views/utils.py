import os
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings

from ..models import TranslatedEpub, AuditLog, UploadedFile, ExtractedEpub, ReadingProgress


class SupportedLanguagesView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        languages = {
            'auto': 'Detect Language',
            'en': 'English',
            'pt': 'Portuguese',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ru': 'Russian',
            'ar': 'Arabic'
        }
        return Response({'languages': languages})


class DeleteTranslationView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = TranslatedEpub.objects.all()

    def get_queryset(self):
        return TranslatedEpub.objects.filter(extracted_epub__uploaded_file__user=self.request.user)

    def perform_destroy(self, instance):
        AuditLog.objects.create(
            user=self.request.user,
            action='delete',
            description=f'Tradução deletada: {instance.source_lang} -> {instance.target_lang}',
            resource_id=instance.pk,
            resource_type='translation',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            metadata={
                'source_lang': instance.source_lang,
                'target_lang': instance.target_lang,
                'chapter_index': instance.chapter_index
            }
        )
        super().perform_destroy(instance)


class AuditLogsView(generics.ListAPIView):
    serializer_class = None
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AuditLog.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        action = request.GET.get('action')
        resource_type = request.GET.get('resource_type')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if action:
            queryset = queryset.filter(action=action)
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        logs = queryset[start:end]
        
        data = []
        for log in logs:
                data.append({
                    'id': log.pk,
                    'action': log.action,
                    'description': log.description,
                    'resource_type': log.resource_type,
                    'resource_id': log.resource_id,
                    'timestamp': log.timestamp,
                    'ip_address': log.ip_address,
                    'metadata': log.metadata
                })
        
        return Response({
            'logs': data,
            'total': queryset.count(),
            'page': page,
            'page_size': page_size
        })


def cleanup_orphaned_records():
    """
    Função utilitária para limpar registros órfãos que podem causar problemas
    de duplicação quando obras são re-importadas.
    """
    from django.db import transaction
    
    with transaction.atomic():
        orphaned_extracted = ExtractedEpub.objects.filter(uploaded_file__isnull=True)
        orphaned_count = orphaned_extracted.count()
        
        if orphaned_count > 0:
            print(f"Removendo {orphaned_count} registros órfãos de ExtractedEpub")
            orphaned_extracted.delete()
        orphaned_translated = TranslatedEpub.objects.filter(extracted_epub__isnull=True)
        orphaned_translated_count = orphaned_translated.count()
        if orphaned_translated_count > 0:
            print(f"Removendo {orphaned_translated_count} registros órfãos de TranslatedEpub")
            orphaned_translated.delete()
        orphaned_progress = ReadingProgress.objects.filter(extracted_epub__isnull=True)
        orphaned_progress_count = orphaned_progress.count()
        
        if orphaned_progress_count > 0:
            print(f"Removendo {orphaned_progress_count} registros órfãos de ReadingProgress")
            orphaned_progress.delete()
            
        return {
            'extracted_epub_orphans': orphaned_count,
            'translated_epub_orphans': orphaned_translated_count, 
            'reading_progress_orphans': orphaned_progress_count
        }


class DiagnosticsView(generics.GenericAPIView):
    """
    View para diagnóstico de problemas no banco de dados
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        user_uploaded_files = UploadedFile.objects.filter(user=user).count()
        user_extracted_epubs = ExtractedEpub.objects.filter(uploaded_file__user=user).count()
        user_translated_epubs = TranslatedEpub.objects.filter(extracted_epub__uploaded_file__user=user).count()
        user_reading_progress = ReadingProgress.objects.filter(user=user).count()
        
        return Response({
            'user_stats': {
                'uploaded_files': user_uploaded_files,
                'extracted_epubs': user_extracted_epubs,
                'translated_epubs': user_translated_epubs,
                'reading_progress': user_reading_progress,
            }
        })


class ReaderImageView(generics.GenericAPIView):
    """Serve images for the reader with the /reader/images/ URL pattern"""
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id, image_name):
        """Serve an image file for a specific uploaded file"""
        try:
            uploaded_file = get_object_or_404(UploadedFile, pk=file_id, user=request.user)
            image_path = os.path.join(
                settings.MEDIA_ROOT, 
                'epub_images', 
                str(uploaded_file.pk), 
                image_name
            )
            if not os.path.exists(image_path):
                raise Http404("Image not found")
            content_type = 'image/jpeg' 
            if image_name.lower().endswith('.png'):
                content_type = 'image/png'
            elif image_name.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif image_name.lower().endswith('.webp'):
                content_type = 'image/webp'
            elif image_name.lower().endswith('.svg'):
                content_type = 'image/svg+xml'
            return FileResponse(
                open(image_path, 'rb'),
                content_type=content_type
            )
            
        except Exception as e:
            raise Http404(f"Image not found: {str(e)}")