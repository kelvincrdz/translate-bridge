from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

try:
    from drf_yasg.utils import swagger_auto_schema
    from drf_yasg import openapi
except ImportError:
    swagger_auto_schema = None
    openapi = None
    
from ..ao3_utils import extract_work_id, fetch_ao3_work, build_epub_from_ao3
from ..tasks import extract_epub_sync
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings
import tempfile
import os
import logging

from ..models import UploadedFile, ExtractedEpub, AuditLog
from .utils import cleanup_orphaned_records

logger = logging.getLogger(__name__)


class AO3ImportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    if swagger_auto_schema and openapi:
        @swagger_auto_schema(
            operation_summary="Importar obra do AO3 por URL",
            operation_description="Recebe a URL de uma obra do Archive of Our Own (AO3), faz o fetch do conteúdo, gera um EPUB temporário e registra o arquivo extraído no sistema.",
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                required=['url'],
                properties={
                    'url': openapi.Schema(type=openapi.TYPE_STRING, format='uri', description='URL completa da obra no AO3 (ex: https://archiveofourown.org/works/12345678)')
                }
            ),
            responses={
                201: openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'uploaded_file_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'extracted_epub_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'title': openapi.Schema(type=openapi.TYPE_STRING),
                        'metadata_preview': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'already_imported': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'debug_id': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                ),
                400: 'Erro de validação ou fetch',
                413: 'Obra muito grande',
                500: 'Erro interno ao gerar/extrair EPUB'
            }
        )
        def post(self, request, *args, **kwargs):
            return self._post_impl(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._post_impl(request, *args, **kwargs)

    def _post_impl(self, request, *args, **kwargs):
        url = request.data.get('url', '').strip()
        if not url:
            return Response({'error': 'URL é obrigatória'}, status=status.HTTP_400_BAD_REQUEST)
        
        work_id = extract_work_id(url)
        if not work_id:
            return Response({'error': 'URL do AO3 inválida. Use o formato: https://archiveofourown.org/works/12345678'},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            debug_id = f'ao3_{work_id}'
            existing_upload = UploadedFile.objects.filter(debug_id=debug_id).first()
            if existing_upload:
                existing_extracted = ExtractedEpub.objects.filter(uploaded_file=existing_upload).first()
                if existing_extracted:
                    metadata = existing_extracted.metadata or {}
                    return Response({
                        'uploaded_file_id': existing_upload.id,
                        'extracted_epub_id': existing_extracted.id,
                        'title': existing_extracted.title,
                        'metadata_preview': {
                            'title': existing_extracted.title,
                            'authors': metadata.get('authors', []),
                            'language': metadata.get('language', 'en'),
                            'word_count': metadata.get('word_count', 0),
                        },
                        'already_imported': True,
                        'debug_id': debug_id,
                    }, status=status.HTTP_200_OK)
            
            logger.info(f"Fetching AO3 work {work_id}")
            ao3_data = fetch_ao3_work(work_id)
            
            logger.info(f"Building EPUB for AO3 work {work_id}")
            temp_epub_path = build_epub_from_ao3(ao3_data, url)
            
            try:
                with open(temp_epub_path, 'rb') as f:
                    uploaded_file = UploadedFile.objects.create(
                        user=request.user,
                        file_name=f"{ao3_data['title'][:100]}.epub",
                        debug_id=debug_id
                    )
                    uploaded_file.file.save(
                        f"ao3_{work_id}_{uploaded_file.id}.epub",
                        File(f),
                        save=True
                    )

                logger.info(f"Extracting EPUB for AO3 work {work_id}")
                extracted_epub = extract_epub_sync(uploaded_file.id)

                AuditLog.objects.create(
                    user=request.user,
                    action='ao3_import',
                    description=f'Imported AO3 work {work_id}: {ao3_data["title"]}',
                    resource_id=uploaded_file.id,
                    resource_type='uploaded_file',
                    metadata={
                        'work_id': work_id,
                        'url': url,
                        'title': ao3_data['title'],
                        'word_count': ao3_data['word_count'],
                        'chapters': len(ao3_data['chapters'])
                    }
                )
                
                return Response({
                    'uploaded_file_id': uploaded_file.id,
                    'extracted_epub_id': extracted_epub.id,
                    'title': extracted_epub.title,
                    'metadata_preview': {
                        'title': ao3_data['title'],
                        'authors': ao3_data['authors'],
                        'summary': ao3_data['summary'][:500] + '...' if len(ao3_data['summary']) > 500 else ao3_data['summary'],
                        'fandoms': ao3_data['fandoms'],
                        'language': ao3_data['language'],
                        'word_count': ao3_data['word_count'],
                        'chapters': len(ao3_data['chapters']),
                        'published': ao3_data['published'],
                        'updated': ao3_data['updated'],
                        'tags': ao3_data['tags']
                    },
                    'already_imported': False,
                    'debug_id': debug_id,
                }, status=status.HTTP_201_CREATED)
                
            finally:
                if os.path.exists(temp_epub_path):
                    os.unlink(temp_epub_path)
                    
        except ImportError as e:
            logger.error(f"AO3 dependency missing: {e}")
            return Response({'error': 'Biblioteca AO3 não está instalada. Contate o administrador.'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error importing AO3 work {work_id}: {e}")
            cleanup_orphaned_records()
            return Response({'error': f'Erro ao importar obra do AO3: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)