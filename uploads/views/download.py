import os
import re
import tempfile

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from ebooklib import epub
import ebooklib

from ..models import UploadedFile, ExtractedEpub, TranslatedEpub, AuditLog
from ..serializers import UploadedFileSerializer, ExtractedEpubSerializer, TranslatedEpubSerializer


class DownloadsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []
        for uploaded_file in queryset:
            file_data = UploadedFileSerializer(uploaded_file).data
            extracted = ExtractedEpub.objects.filter(uploaded_file=uploaded_file).first()
            extracted_data = None
            translations_data = []
            if extracted:
                extracted_data = ExtractedEpubSerializer(extracted).data
                translations = TranslatedEpub.objects.filter(extracted_epub=extracted)
                translations_data = TranslatedEpubSerializer(translations, many=True).data
            data.append({
                'file': file_data,
                'extracted': extracted_data,
                'translations': translations_data
            })
        return Response(data)


class DownloadOriginalView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        file_id = self.kwargs['pk']
        uploaded_file = get_object_or_404(UploadedFile, pk=file_id, user=request.user)
        file_path = uploaded_file.file.path
        if os.path.exists(file_path):
            # Log de auditoria
            AuditLog.objects.create(
                user=request.user,
                action='download',
                description=f'Download do arquivo original: {uploaded_file.title or uploaded_file.file.name}',
                resource_id=uploaded_file.pk,
                resource_type='file',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            response = FileResponse(open(file_path, 'rb'), content_type='application/epub+zip')
            response['Content-Disposition'] = f'attachment; filename="{uploaded_file.title or "original"}.epub"'
            return response
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)


class DownloadTranslatedView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        translation_id = self.kwargs['pk']
        translation = get_object_or_404(TranslatedEpub, pk=translation_id, extracted_epub__uploaded_file__user=request.user)
        
        # Read original EPUB
        original_book = epub.read_epub(translation.extracted_epub.uploaded_file.file.path)
        
        # Get document items
        doc_items = [item for item in original_book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
        
        # Replace content with translated
        if translation.translated_chapters:
            if translation.chapter_index is not None:
                # Single-chapter translation: replace only that specific chapter
                idx = translation.chapter_index
                if 0 <= idx < len(doc_items) and len(translation.translated_chapters) > 0:
                    doc_items[idx].set_content(translation.translated_chapters[0]['content'].encode('utf-8'))
            else:
                # Full translation: replace all chapters sequentially
                for i, item in enumerate(doc_items):
                    if i < len(translation.translated_chapters):
                        translated_content = translation.translated_chapters[i]['content']
                        item.set_content(translated_content.encode('utf-8'))
        
        # Update title if full translation
        if translation.chapter_index is None and translation.translated_title:
            original_book.set_title(translation.translated_title)

        # Write to a temporary file and return as response
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub.write_epub(tmp_file.name, original_book, {})
            tmp_file_path = tmp_file.name
        response = FileResponse(open(tmp_file_path, 'rb'), content_type='application/epub+zip')
        base_title = translation.translated_title or translation.extracted_epub.title or f"book_{translation.extracted_epub.uploaded_file.pk}"
        safe_base = re.sub(r'[^\w\-\. ]+', '_', base_title).strip() or 'translated'
        filename = f"{safe_base}_{translation.target_lang}.epub"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        # Log de auditoria
        AuditLog.objects.create(
            user=request.user,
            action='download',
            description=f'Download da tradução: {filename}',
            resource_id=translation.pk,
            resource_type='translation',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={
                'source_lang': translation.source_lang,
                'target_lang': translation.target_lang,
                'chapter_index': translation.chapter_index
            }
        )
        return response


class DownloadMixedView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Download EPUB with mixed content: translated chapters when available for a target language, otherwise original.

        Query params:
        - target_lang: required if more than one target translation exists.
        """
        file_id = self.kwargs['pk']
        target_lang = request.GET.get('target_lang')

        uploaded_file = get_object_or_404(UploadedFile, pk=file_id, user=request.user)
        extracted = get_object_or_404(ExtractedEpub, uploaded_file=uploaded_file)

        # Collect available translations for this extracted epub
        translations_qs = TranslatedEpub.objects.filter(extracted_epub=extracted)
        if not translations_qs.exists():
            return Response({'error': 'No translations available for this book'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine target language
        langs = sorted({t.target_lang for t in translations_qs})
        if not target_lang:
            if len(langs) == 1:
                target_lang = langs[0]
            else:
                return Response({'error': 'target_lang is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Prefer a full translation if exists
        full_translation = translations_qs.filter(target_lang=target_lang, chapter_index__isnull=True).first()

        original_book = epub.read_epub(uploaded_file.file.path)
        doc_items = [item for item in original_book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]

        if full_translation and full_translation.translated_chapters:
            for i, item in enumerate(doc_items):
                if i < len(full_translation.translated_chapters):
                    item.set_content(full_translation.translated_chapters[i]['content'].encode('utf-8'))
            if full_translation.translated_title:
                original_book.set_title(full_translation.translated_title)
        else:
            # Merge partials for the selected target language
            chapter_map = {}
            partials = translations_qs.filter(target_lang=target_lang, chapter_index__isnull=False)
            for t in partials:
                if t.translated_chapters and len(t.translated_chapters) > 0 and t.chapter_index is not None:
                    chapter_map[t.chapter_index] = t.translated_chapters[0]['content']

            for idx, item in enumerate(doc_items):
                if idx in chapter_map:
                    item.set_content(chapter_map[idx].encode('utf-8'))
                # else keep original content

        # Write out epub
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
            epub.write_epub(tmp_file.name, original_book, {})
            tmp_file_path = tmp_file.name

        response = FileResponse(open(tmp_file_path, 'rb'), content_type='application/epub+zip')
        base_title = extracted.title or uploaded_file.title or f"book_{uploaded_file.pk}"
        safe_base = re.sub(r'[^\w\-\. ]+', '_', base_title).strip() or 'book'
        suffix = f"_{target_lang}_mixed"
        response['Content-Disposition'] = f'attachment; filename="{safe_base}{suffix}.epub"'

        # Audit
        AuditLog.objects.create(
            user=request.user,
            action='download',
            description=f'Download mixed EPUB: {safe_base}{suffix}.epub',
            resource_id=uploaded_file.pk,
            resource_type='file',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'target_lang': target_lang}
        )

        return response