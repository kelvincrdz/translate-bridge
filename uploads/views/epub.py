import logging
import re
import traceback
from bs4 import BeautifulSoup

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ..models import (
    UploadedFile, ExtractedEpub, TranslatedEpub, AuditLog, ReadingProgress
)
from ..serializers import (
    ExtractedEpubSerializer, TranslatedEpubSerializer, ReadingProgressSerializer
)


class ExtractEpubView(generics.RetrieveAPIView):
    serializer_class = ExtractedEpubSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        file_id = self.kwargs['pk']
        uploaded_file = get_object_or_404(UploadedFile, pk=file_id, user=self.request.user)
        extracted, created = ExtractedEpub.objects.get_or_create(uploaded_file=uploaded_file)
        if created:
            self.extract_epub(extracted)
        return extracted

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        chapter_param = request.GET.get('chapter')
        if chapter_param is not None:
            try:
                chapter_index = int(chapter_param)
                if instance.chapters and isinstance(instance.chapters, list) and 0 <= chapter_index < len(instance.chapters):
                    chapter = instance.chapters[chapter_index]
                    data = {
                        'title': instance.title,
                        'chapter': chapter,
                        'chapter_index': chapter_index
                    }
                else:
                    return Response({'error': 'Chapter index out of range or no chapters available'}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({'error': 'Invalid chapter number'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = self.get_serializer(instance)
            data = serializer.data
        chapter_info = f" - Capítulo {chapter_param}" if chapter_param else " - Todo o conteúdo"
        AuditLog.objects.create(
            user=self.request.user,
            action='extract',
            description=f'Extração de conteúdo visualizada{chapter_info}',
            resource_id=instance.pk,
            resource_type='extraction',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            metadata={
                'chapter_requested': chapter_param,
                'file_id': instance.uploaded_file.pk
            }
        )
        
        return Response(data)

    def extract_epub(self, extracted):
        from ..tasks import extract_epub_sync
        extract_epub_sync(extracted.pk)


class TranslateEpubView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        log = logging.getLogger(__name__)
        
        obj_id = self.kwargs['pk']
        log.info("[Translation] === INÍCIO DA REQUISIÇÃO ===")
        log.info(f"[Translation] Iniciando tradução para ID={obj_id}, user={request.user.username}")
        log.info(f"[Translation] Request data: {request.data}")
        log.info(f"[Translation] Request method: {request.method}")
        
        extracted = ExtractedEpub.objects.filter(pk=obj_id, uploaded_file__user=request.user).first()
        if not extracted:
            log.info("[Translation] ExtractedEpub não encontrado diretamente, buscando via UploadedFile")
            uploaded_file = get_object_or_404(UploadedFile, pk=obj_id, user=request.user)
            extracted = get_object_or_404(ExtractedEpub, uploaded_file=uploaded_file)
        
        log.info(f"[Translation] ExtractedEpub encontrado: ID={extracted.pk}, title='{extracted.title}'")
        
        chapter_param = request.data.get('chapter')
        source_lang = (request.data.get('source_lang') or 'auto').strip()
        target_lang = (request.data.get('target_lang') or 'pt').strip()
        
        log.info(f"[Translation] Parâmetros: chapter={chapter_param}, source_lang={source_lang}, target_lang={target_lang}")
        allowed_langs = {'auto','en','pt','es','fr','de','it','ja','ko','zh','ru','ar'}
        if target_lang not in allowed_langs:
            log.error(f"[Translation] Idioma de destino inválido: {target_lang}")
            return Response({'error': 'Invalid target language'}, status=status.HTTP_400_BAD_REQUEST)
        if source_lang != 'auto' and source_lang not in allowed_langs:
            log.error(f"[Translation] Idioma de origem inválido: {source_lang}")
            return Response({'error': 'Invalid source language'}, status=status.HTTP_400_BAD_REQUEST)
        
        chapter_index = None
        if chapter_param is not None:
            try:
                chapter_index = int(chapter_param)
                total_chapters = len(extracted.chapters or [])
                log.info(f"[Translation] Traduzindo capítulo {chapter_index} de {total_chapters} capítulos disponíveis")
                if not (0 <= chapter_index < total_chapters):
                    log.error(f"[Translation] Índice de capítulo fora do range: {chapter_index} (0-{total_chapters-1})")
                    return Response({'error': 'Chapter index out of range'}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                log.error(f"[Translation] Número de capítulo inválido: {chapter_param}")
                return Response({'error': 'Invalid chapter number'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            log.info("[Translation] Traduzindo obra completa")
        try:
            log.info("[Translation] Iniciando translate_epub_sync...")
            from ..tasks import translate_epub_sync
            translation = translate_epub_sync(
                extracted.pk, source_lang, target_lang, chapter_index, request.user.pk
            )
            log.info(f"[Translation] Tradução concluída: translation_id={translation.pk}")
            
            serializer = TranslatedEpubSerializer(translation)
            log.info("[Translation] Retornando dados serializados")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            log.error(f"[Translation] Erro durante tradução: {str(e)}")
            log.error(f"[Translation] Traceback: {traceback.format_exc()}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BooksListView(generics.ListAPIView):
    """Lista livros (EPUB extraídos) do usuário com progresso resumido.
    Retorna campos mínimos para montar biblioteca; capítulos completos só via EpubReaderView.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def list(self, request, *args, **kwargs):
        extracted_qs = ExtractedEpub.objects.filter(uploaded_file__user=request.user).order_by('-pk')
        data = []
        progress_map = {rp.extracted_epub_id: rp for rp in ReadingProgress.objects.filter(
            user=request.user,
            extracted_epub__in=[e.pk for e in extracted_qs]
        )}
        for ext in extracted_qs:
            prog = progress_map.get(ext.pk)
            chapters = ext.chapters if isinstance(ext.chapters, list) else []
            data.append({
                'id': ext.pk,
                'uploaded_file_id': ext.uploaded_file.pk,
                'title': ext.title,
                'metadata': ext.metadata or {},
                'chapter_count': len(chapters),
                'cover_image': getattr(ext, 'cover_image', None),
                'progress': {
                    'current_chapter': prog.current_chapter if prog else 0,
                    'progress_percentage': prog.progress_percentage if prog else 0.0,
                }
            })
        return Response({'results': data, 'count': len(data)})


class EpubReaderView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        """Retrieve EPUB content for the reader"""
        log = logging.getLogger(__name__)
        
        log.info(f"[EpubReader] Requisição para file_id={file_id}, user={request.user.username}")
        log.info(f"[EpubReader] Parâmetros da query: {dict(request.GET)}")
        
        uploaded_file = get_object_or_404(UploadedFile, pk=file_id, user=request.user)

        extracted = ExtractedEpub.objects.filter(uploaded_file=uploaded_file).first()
        if not extracted:
            log.error(f"[EpubReader] EPUB não extraído para file_id={file_id}")
            return Response({
                'error': 'EPUB content not extracted yet. Please extract content first.'
            }, status=status.HTTP_400_BAD_REQUEST)

        log.info(f"[EpubReader] ExtractedEpub encontrado: id={extracted.pk}, title='{extracted.title}'")
        source_lang = request.GET.get('source_lang', 'auto')
        target_lang = request.GET.get('target_lang', 'pt')
        chapter_param = request.GET.get('chapter')
        log.info(f"[EpubReader] Parâmetros de tradução: source_lang={source_lang}, target_lang={target_lang}, chapter={chapter_param}")
        translations_qs = TranslatedEpub.objects.filter(extracted_epub=extracted)
        translations_data = TranslatedEpubSerializer(translations_qs, many=True).data
        log.info(f"[EpubReader] Traduções disponíveis: {len(translations_data)}")
        for trans in translations_data:
            log.info(f"[EpubReader] - Tradução: {trans.get('source_lang')} -> {trans.get('target_lang')}, chapter_index={trans.get('chapter_index')}")

        progress_obj = ReadingProgress.objects.filter(user=request.user, extracted_epub=extracted).first()
        if progress_obj:
            progress_data = ReadingProgressSerializer(progress_obj).data
        else:
            progress_data = {
                'current_chapter': 0,
                'current_position': 0,
                'progress_percentage': 0.0,
            }

        def sanitize_html(raw_html: str) -> str:
            if not raw_html:
                return ''
            cleaned = re.sub(r'^\s*<\?xml[^>]*>\s*', '', raw_html, flags=re.IGNORECASE)
            cleaned = re.sub(r'<!DOCTYPE[^>]*>\s*', '', cleaned, flags=re.IGNORECASE)
            try:
                soup = BeautifulSoup(cleaned, 'html.parser')
                for tag in soup.find_all(['script', 'iframe', 'object', 'embed', 'style']):
                    tag.decompose()
                body = soup.body
                if body:
                    final_html = ''.join(str(c) for c in body.contents)
                else:
                    final_html = str(soup)
                final_html = re.sub(r'^\s*<html[^>]*>\s*', '', final_html, flags=re.IGNORECASE)
                final_html = re.sub(r'</html>\s*$', '', final_html, flags=re.IGNORECASE)
                return final_html.strip()
            except Exception:
                return cleaned

        sanitized_chapters = []
        chapters_obj = extracted.chapters if isinstance(extracted.chapters, list) else []
        
        log.info(f"[EpubReader] Preparando {len(chapters_obj)} capítulos")
        
        chapter_translations = {}
        
        if target_lang != 'auto':
            if chapter_param is not None:
                try:
                    chapter_index = int(chapter_param)
                    specific_translation = TranslatedEpub.objects.filter(
                        extracted_epub=extracted,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        chapter_index=chapter_index
                    ).first()
                    
                    if specific_translation and specific_translation.translated_chapters:
                        chapter_translations[chapter_index] = specific_translation.translated_chapters[0]['content']
                        log.info(f"[EpubReader] Tradução específica encontrada para capítulo {chapter_index}")
                except ValueError:
                    pass

            if not chapter_translations:
                log.info(f"[EpubReader] Buscando tradução completa do livro")
                full_translation = TranslatedEpub.objects.filter(
                    extracted_epub=extracted,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    chapter_index__isnull=True
                ).first()
                
                if full_translation and full_translation.translated_chapters:
                    for i, trans_chapter in enumerate(full_translation.translated_chapters):
                        if i < len(chapters_obj):
                            chapter_translations[i] = trans_chapter['content']
                    log.info(f"[EpubReader] Tradução completa encontrada com {len(chapter_translations)} capítulos")
                else:
                    log.info("[EpubReader] Nenhuma tradução completa encontrada")

        for i, ch in enumerate(chapters_obj):
            if isinstance(ch, dict):
                if i in chapter_translations:
                    sanitized_content = sanitize_html(chapter_translations[i])
                    sanitized_chapters.append({
                        'title': ch.get('title', f'Capítulo {i + 1}'),
                        'content': sanitized_content,
                        'translated': True,
                        'original_content': sanitize_html(ch.get('content', ''))
                    })
                    log.info(f"[EpubReader] Capítulo {i} com tradução aplicada")
                else:
                    sanitized_content = sanitize_html(ch.get('content', ''))
                    sanitized_chapters.append({
                        'title': ch.get('title', f'Capítulo {i + 1}'),
                        'content': sanitized_content,
                        'translated': False
                    })

        log.info(f"[EpubReader] Capítulos preparados: {len(sanitized_chapters)} capítulos, {sum(1 for ch in sanitized_chapters if ch.get('translated', False))} traduzidos")

        response_data = {
            'id': extracted.pk,
            'title': extracted.title,
            'metadata': extracted.metadata,
            'chapters': sanitized_chapters,
            'images': extracted.images,
            'translations': translations_data,
            'progress': progress_data,
        }

        log.info(f"[EpubReader] Retornando resposta com {len(sanitized_chapters)} capítulos")
        return Response(response_data)