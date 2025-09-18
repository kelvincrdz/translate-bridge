import os
import zipfile
import mimetypes
import hashlib
from pathlib import Path
import re
from bs4 import BeautifulSoup

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from ebooklib import epub
import ebooklib

from ..models import UploadedFile, ExtractedEpub, AuditLog
from ..serializers import UploadedFileSerializer


class UploadFileView(generics.CreateAPIView):
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if file_obj:
            if not file_obj.name.lower().endswith('.epub'):
                return Response({'error': 'Only EPUB files are allowed'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file size (max 150MB)
            if file_obj.size > 150 * 1024 * 1024:
                return Response({'error': 'File size must be less than 150MB'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                with zipfile.ZipFile(file_obj, 'r') as zip_ref:
                    if 'mimetype' not in zip_ref.namelist():
                        return Response({'error': 'Invalid EPUB file'}, status=status.HTTP_400_BAD_REQUEST)
                    mimetype = zip_ref.read('mimetype').decode('utf-8').strip()
                    if mimetype != 'application/epub+zip':
                        return Response({'error': 'Invalid EPUB file'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                return Response({'error': 'Invalid EPUB file'}, status=status.HTTP_400_BAD_REQUEST)
        
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        AuditLog.objects.create(
            user=self.request.user,
            action='upload',
            description=f'Arquivo EPUB enviado: {instance.title or instance.file.name}',
            resource_id=instance.pk,
            resource_type='file',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            metadata={
                'file_size': instance.file.size,
                'file_name': instance.file.name
            }
        )
        extracted, created = ExtractedEpub.objects.get_or_create(uploaded_file=instance)
        if created:
            try:
                self.extract_epub(extracted)
            except Exception as e:
                print(f"Erro ao extrair EPUB: {str(e)}")

    def extract_epub(self, extracted):
        book = epub.read_epub(extracted.uploaded_file.file.path)
        metadata = {}
        for item in book.get_metadata('DC', 'title'):
            metadata['title'] = item[0]
        for item in book.get_metadata('DC', 'creator'):
            metadata['author'] = item[0]
        extracted.title = metadata.get('title', '')
        extracted.metadata = metadata

        from bs4 import BeautifulSoup as _BS
        import re as _re
        def _sanitize(raw_html: str) -> str:
            if not raw_html:
                return ''
            tmp = _re.sub(r'^\s*<\?xml[^>]*?>', '', raw_html, flags=_re.IGNORECASE)
            tmp = _re.sub(r'<!DOCTYPE[^>]*?>', '', tmp, flags=_re.IGNORECASE)
            soup_local = _BS(tmp, 'html.parser')
            for tag in soup_local.find_all(['script','iframe','object','embed','style']):
                tag.decompose()
            body = soup_local.body
            if body:
                inner = ''.join(str(c) for c in body.contents)
            else:
                inner = str(soup_local)
            inner = _re.sub(r'^\s*<html[^>]*>','', inner, flags=_re.IGNORECASE)
            inner = _re.sub(r'</html>\s*$','', inner, flags=_re.IGNORECASE)
            return inner.strip()

        def _extract_chapter_title(soup_doc, item, chapter_index):
            """
            Extrai o título do capítulo seguindo a prioridade:
            1. Tags de título (h1, h2, h3, etc.)
            2. Tag <title>
            3. Primeira frase do conteúdo
            4. Fallback para "Capítulo X"
            """
            for tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                title_element = soup_doc.find(tag_name)
                if title_element:
                    title_text = title_element.get_text().strip()
                    if title_text and len(title_text) > 0:
                        return title_text
            
            title_tag = soup_doc.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                if title_text and not title_text.endswith('.html') and not title_text.endswith('.xhtml'):
                    return title_text
            
            content_copy = soup_doc.__copy__()
            for tag in content_copy.find_all(['script', 'style', 'meta', 'link']):
                tag.decompose()
            text_elements = content_copy.find_all(['p', 'div', 'span'], string=True)
            for element in text_elements:
                text = element.get_text().strip()
                if text and len(text) > 5:
                    first_sentence = re.split(r'[.!?]', text)[0].strip()
                    if len(first_sentence) > 5 and len(first_sentence) <= 100:
                        return first_sentence + ('...' if len(first_sentence) < len(text.split('.')[0]) else '')
            
            # Se ainda não encontrou nada, pega qualquer texto disponível
            all_text = content_copy.get_text().strip()
            if all_text:
                words = all_text.split()[:10] 
                if words:
                    return ' '.join(words) + ('...' if len(all_text.split()) > 10 else '')

            return f"Capítulo {chapter_index + 1}"

        chapters = []
        chapter_index = 0
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup_doc = _BS(item.get_content(), 'html.parser')
                title_text = _extract_chapter_title(soup_doc, item, chapter_index)
                raw_content = item.get_content().decode('utf-8')
                cleaned = _sanitize(raw_content)
                chapters.append({'title': title_text, 'content': cleaned})
                chapter_index += 1
        extracted.chapters = chapters

        def _generate_cover_for_ao3(title, author, extracted):
            """
            Gera uma capa usando Pillow para livros do AO3 ou outros sem capa
            """
            try:
                from ..cover_utils import generate_epub_cover_file
                return generate_epub_cover_file(title, author, extracted.uploaded_file.id)
                
            except ImportError:
                print("Pillow não está instalado. Não é possível gerar capa.")
                return None
            except Exception as e:
                print(f"Erro ao gerar capa: {str(e)}")
                return None

        def _extract_cover_image(book, extracted):
            """
            Extrai a imagem de capa do EPUB
            Retorna o caminho web da capa ou None se não encontrar
            """
            cover_item = None

            for meta in book.get_metadata('OPF', 'meta'):
                if len(meta) >= 2 and meta[1].get('name') == 'cover':
                    cover_id = meta[1].get('content')
                    if cover_id:
                        cover_item = book.get_item_with_id(cover_id)
                        if cover_item:
                            break

            if not cover_item:
                for item in book.get_items():
                    if hasattr(item, 'properties') and 'cover-image' in item.properties:
                        cover_item = item
                        break

            if not cover_item:
                try:
                    for cover_name in ['cover.jpg', 'cover.jpeg', 'Images/cover.jpg', 'images/cover.jpg']:
                        try:
                            cover_item = book.get_item_with_href(cover_name)
                            if cover_item:
                                break
                        except:
                            continue
                except:
                    pass

            if not cover_item:
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_IMAGE:
                        name = item.get_name().lower()
                        if 'cover' in name or name.startswith('cover'):
                            cover_item = item
                            break
            
            if not cover_item:
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_IMAGE:
                        cover_item = item
                        break
            
            if cover_item:
                try:
                    content = cover_item.get_content()
                    original_name = cover_item.get_name()
                    cover_name = "cover.jpeg"
                    ext = Path(original_name).suffix.lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        cover_name = f"cover{ext}"
                    image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', str(extracted.uploaded_file.id))
                    os.makedirs(image_dir, exist_ok=True)
                    cover_path = os.path.join(image_dir, cover_name)
                    with open(cover_path, 'wb') as f:
                        f.write(content)
                    web_path = f'/media/epub_images/{extracted.uploaded_file.id}/{cover_name}'
                    return web_path
                    
                except Exception as e:
                    print(f"Erro ao extrair capa: {str(e)}")
                    return None
            
            return None

        images = []
        cover_image_path = None
        cover_image_path = _extract_cover_image(book, extracted)
        if not cover_image_path:
            title = extracted.title or 'Título Desconhecido'
            author = extracted.metadata.get('author', '') if extracted.metadata else ''
            cover_image_path = _generate_cover_for_ao3(title, author, extracted)
            
            if cover_image_path:
                print(f"Capa gerada com Pillow para: {title}")
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                try:
                    original_name = item.get_name()
                    content = item.get_content()
                    if cover_image_path and 'cover' in original_name.lower():
                        continue
                    safe_name = original_name.replace('/', '_').replace('\\', '_').replace('..', '_')
                    safe_name = os.path.basename(safe_name)
                    if '.' not in safe_name:
                        mime_type, _ = mimetypes.guess_type(original_name)
                        if not mime_type:
                            if content.startswith(b'\xff\xd8\xff'):
                                safe_name += '.jpg'
                            elif content.startswith(b'\x89PNG'):
                                safe_name += '.png'
                            elif content.startswith(b'GIF'):
                                safe_name += '.gif'
                            elif content.startswith(b'\x00\x00\x01\x00') or content.startswith(b'\x00\x00\x02\x00'):
                                safe_name += '.ico'
                            else:
                                safe_name += '.bin'
                        else:
                            ext = mimetypes.guess_extension(mime_type)
                            if ext:
                                safe_name += ext
                    if not safe_name or safe_name == '.' or len(safe_name) > 255:
                        hash_name = hashlib.md5(content).hexdigest()
                        ext = Path(original_name).suffix if Path(original_name).suffix else '.bin'
                        safe_name = f"{hash_name}{ext}"
                    image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', str(extracted.uploaded_file.id))
                    os.makedirs(image_dir, exist_ok=True)
                    image_path = os.path.join(image_dir, safe_name)
                    counter = 1
                    base_name = safe_name
                    while os.path.exists(image_path):
                        name_parts = os.path.splitext(base_name)
                        safe_name = f"{name_parts[0]}_{counter}{name_parts[1]}"
                        image_path = os.path.join(image_dir, safe_name)
                        counter += 1
                    with open(image_path, 'wb') as f:
                        f.write(content)
                    web_path = f'/media/epub_images/{extracted.uploaded_file.id}/{safe_name}'
                    images.append(web_path)
                except Exception as e:
                    print(f"Erro ao extrair imagem {item.get_name()}: {str(e)}")
                    continue

        extracted.images = images
        extracted.cover_image = cover_image_path
        extracted.save()


class FileListView(generics.ListAPIView):
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user)


class DeleteFileView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = UploadedFile.objects.all()

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        from .utils import cleanup_orphaned_records
        
        file_metadata = {
            'file_size': instance.file.size,
            'file_name': instance.file.name
        }
        
        try:
            extracted = ExtractedEpub.objects.get(uploaded_file=instance)
            if extracted.metadata and 'external_work_id' in extracted.metadata:
                file_metadata['external_work_id'] = extracted.metadata['external_work_id']
                file_metadata['source_type'] = extracted.metadata.get('source_type', 'unknown')
        except ExtractedEpub.DoesNotExist:
            pass
        
        AuditLog.objects.create(
            user=self.request.user,
            action='delete',
            description=f'Arquivo deletado: {instance.title or instance.file.name}',
            resource_id=instance.pk,
            resource_type='file',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            metadata=file_metadata
        )
        
        super().perform_destroy(instance)
        
        try:
            cleanup_orphaned_records()
        except Exception as e:
            print(f"Aviso: Erro na limpeza de registros órfãos: {e}")


class DeleteAllBooksView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        files_qs = UploadedFile.objects.filter(user=user)
        count = files_qs.count()
        if count == 0:
            return Response({'message': 'Nenhum livro para remover', 'deleted': 0})

        file_ids = list(files_qs.values_list('id', flat=True))
        files_qs.delete()
        AuditLog.objects.create(
            user=user,
            action='delete',
            description=f'Delete em massa de {count} arquivo(s) EPUB',
            resource_type='file',
            metadata={'deleted_count': count, 'file_ids': file_ids[:50]}  # limit metadata size
        )

        return Response({'message': 'Livros removidos', 'deleted': count})