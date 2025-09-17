from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404, HttpResponse
from django.conf import settings
import os
from .models import UploadedFile, ExtractedEpub, TranslatedEpub, AuditLog, ReadingProgress
from .serializers import (
    UploadedFileSerializer,
    RegisterSerializer,
    UserSerializer,
    ExtractedEpubSerializer,
    TranslatedEpubSerializer,
    ReadingProgressSerializer,
)
import ebooklib
from ebooklib import epub
import os
import mimetypes
import hashlib
from pathlib import Path
import re
from bs4 import BeautifulSoup
try:
    from drf_yasg.utils import swagger_auto_schema
    from drf_yasg import openapi
except ImportError:  # drf_yasg might not be available in some environments
    swagger_auto_schema = None
    openapi = None


# Create your views here.

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

class LoginView(generics.GenericAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            # Log de auditoria para login
            AuditLog.objects.create(
                user=user,
                action='login',
                description='Login realizado com sucesso',
                ip_address=self.request.META.get('REMOTE_ADDR'),
                user_agent=self.request.META.get('HTTP_USER_AGENT')
            )
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class UserInfoView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class RefreshTokenView(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                refresh = RefreshToken(refresh_token)
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                })
            except Exception:
                return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)

class SupportedLanguagesView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        # Common languages supported by Google Translate
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

class UploadFileView(generics.CreateAPIView):
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if file_obj:
            # Validate file type
            if not file_obj.name.lower().endswith('.epub'):
                return Response({'error': 'Only EPUB files are allowed'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file size (max 50MB)
            if file_obj.size > 50 * 1024 * 1024:
                return Response({'error': 'File size must be less than 50MB'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Try to read as EPUB to validate
            try:
                import zipfile
                with zipfile.ZipFile(file_obj, 'r') as zip_ref:
                    # Check for mimetype file
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
        
        # Log de auditoria
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

        # Trigger EPUB extraction
        extracted, created = ExtractedEpub.objects.get_or_create(uploaded_file=instance)
        if created:
            try:
                self.extract_epub(extracted)
            except Exception as e:
                print(f"Erro ao extrair EPUB: {str(e)}")

    def extract_epub(self, extracted):
        book = epub.read_epub(extracted.uploaded_file.file.path)

        # Extract metadata
        metadata = {}
        for item in book.get_metadata('DC', 'title'):
            metadata['title'] = item[0]
        for item in book.get_metadata('DC', 'creator'):
            metadata['author'] = item[0]
        extracted.title = metadata.get('title', '')
        extracted.metadata = metadata

        # Extract and sanitize chapters
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
            # Primeiro, tenta encontrar tags de título no conteúdo
            for tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                title_element = soup_doc.find(tag_name)
                if title_element:
                    title_text = title_element.get_text().strip()
                    if title_text and len(title_text) > 0:
                        return title_text
            
            # Se não encontrou, tenta a tag <title>
            title_tag = soup_doc.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                # Verifica se não é apenas o nome do arquivo
                if title_text and not title_text.endswith('.html') and not title_text.endswith('.xhtml'):
                    return title_text
            
            # Se não encontrou título adequado, tenta pegar a primeira frase do conteúdo
            # Remove scripts, styles e outros elementos não textuais
            content_copy = soup_doc.__copy__()
            for tag in content_copy.find_all(['script', 'style', 'meta', 'link']):
                tag.decompose()
            
            # Pega todos os parágrafos e outros elementos de texto
            text_elements = content_copy.find_all(['p', 'div', 'span'], string=True)
            for element in text_elements:
                text = element.get_text().strip()
                if text and len(text) > 10:  # Ignora textos muito curtos
                    # Pega a primeira frase (até o primeiro ponto, exclamação ou interrogação)
                    import re
                    first_sentence = re.split(r'[.!?]', text)[0].strip()
                    if len(first_sentence) > 5 and len(first_sentence) <= 100:
                        return first_sentence + ('...' if len(first_sentence) < len(text.split('.')[0]) else '')
            
            # Se ainda não encontrou nada, pega qualquer texto disponível
            all_text = content_copy.get_text().strip()
            if all_text:
                words = all_text.split()[:10]  # Primeiras 10 palavras
                if words:
                    return ' '.join(words) + ('...' if len(all_text.split()) > 10 else '')
            
            # Fallback final
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
                from PIL import Image, ImageDraw, ImageFont
                import io
                
                width, height = 600, 900
                img = Image.new('RGB', (width, height), color=(128, 0, 0))
                draw = ImageDraw.Draw(img)
                
                try:
                    font_title = ImageFont.truetype('arial.ttf', 40)
                    font_author = ImageFont.truetype('arial.ttf', 28)
                    font_footer = ImageFont.truetype('arial.ttf', 20)
                except Exception:
                    font_title = ImageFont.load_default()
                    font_author = ImageFont.load_default()
                    font_footer = ImageFont.load_default()

                # Função para quebrar texto
                def wrap_text(text, max_width, font):
                    words = text.split()
                    lines = []
                    current_line = ''
                    for word in words:
                        test_line = f"{current_line} {word}".strip()
                        if draw.textlength(test_line, font=font) <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)
                    return lines

                # Desenhar título
                title_lines = wrap_text(title[:200], 520, font_title)
                y = 120
                for line in title_lines[:8]:
                    line_width = draw.textlength(line, font=font_title)
                    x = (width - line_width) / 2
                    draw.text((x, y), line, font=font_title, fill='white')
                    y += 50

                # Desenhar autor
                if author:
                    author_width = draw.textlength(author, font=font_author)
                    x = (width - author_width) / 2
                    draw.text((x, y + 20), author[:100], font=font_author, fill='#ffd')

                # Footer
                footer = 'Generated Cover'
                footer_width = draw.textlength(footer, font=font_footer)
                x = (width - footer_width) / 2
                draw.text((x, height - 60), footer, font=font_footer, fill='#eee')

                # Salvar a capa gerada
                image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', str(extracted.uploaded_file.id))
                os.makedirs(image_dir, exist_ok=True)
                
                cover_path = os.path.join(image_dir, 'generated_cover.jpg')
                img.save(cover_path, format='JPEG', quality=85)
                
                # Retornar o caminho web
                web_path = f'/media/epub_images/{extracted.uploaded_file.id}/generated_cover.jpg'
                return web_path
                
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
            # Primeiro, tenta encontrar a capa através dos metadados
            cover_item = None
            
            # Método 1: Procura por meta tag cover
            for meta in book.get_metadata('OPF', 'meta'):
                if len(meta) >= 2 and meta[1].get('name') == 'cover':
                    cover_id = meta[1].get('content')
                    if cover_id:
                        cover_item = book.get_item_with_id(cover_id)
                        if cover_item:
                            break
            
            # Método 2: Procura por item com propriedade cover-image
            if not cover_item:
                for item in book.get_items():
                    if hasattr(item, 'properties') and 'cover-image' in item.properties:
                        cover_item = item
                        break
            
            # Método 3: Tenta usar book.get_item_with_href para capas definidas via set_cover
            if not cover_item:
                try:
                    # Tenta encontrar cover.jpg ou cover.jpeg (padrão do AO3)
                    for cover_name in ['cover.jpg', 'cover.jpeg', 'Images/cover.jpg', 'images/cover.jpg']:
                        try:
                            cover_item = book.get_item_with_href(cover_name)
                            if cover_item:
                                break
                        except:
                            continue
                except:
                    pass
            
            # Método 4: Procura por imagem com nome "cover"
            if not cover_item:
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_IMAGE:
                        name = item.get_name().lower()
                        if 'cover' in name or name.startswith('cover'):
                            cover_item = item
                            break
            
            # Método 5: Primeira imagem encontrada como fallback
            if not cover_item:
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_IMAGE:
                        cover_item = item
                        break
            
            if cover_item:
                try:
                    # Processar e salvar a capa
                    content = cover_item.get_content()
                    original_name = cover_item.get_name()
                    
                    # Criar nome seguro para a capa
                    cover_name = "cover.jpeg"
                    ext = Path(original_name).suffix.lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        cover_name = f"cover{ext}"
                    
                    # Diretório de imagens
                    image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', str(extracted.uploaded_file.id))
                    os.makedirs(image_dir, exist_ok=True)
                    
                    # Caminho completo para a capa
                    cover_path = os.path.join(image_dir, cover_name)
                    
                    # Salvar a imagem
                    with open(cover_path, 'wb') as f:
                        f.write(content)
                    
                    # Retornar o caminho web
                    web_path = f'/media/epub_images/{extracted.uploaded_file.id}/{cover_name}'
                    return web_path
                    
                except Exception as e:
                    print(f"Erro ao extrair capa: {str(e)}")
                    return None
            
            return None

        # Extract images with improved handling
        images = []
        cover_image_path = None
        # Extract images with improved handling
        images = []
        cover_image_path = None
        
        # Primeiro, extrair a capa
        cover_image_path = _extract_cover_image(book, extracted)
        
        # Se não encontrou capa, sempre gerar uma com Pillow
        if not cover_image_path:
            title = extracted.title or 'Título Desconhecido'
            author = extracted.metadata.get('author', '') if extracted.metadata else ''
            cover_image_path = _generate_cover_for_ao3(title, author, extracted)
            
            if cover_image_path:
                print(f"Capa gerada com Pillow para: {title}")
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                try:
                    # Get the original name and content
                    original_name = item.get_name()
                    content = item.get_content()

                    # Verificar se é a capa (evitar duplicar)
                    if cover_image_path and 'cover' in original_name.lower():
                        continue

                    # Create safe filename
                    # Remove or replace problematic characters
                    safe_name = original_name.replace('/', '_').replace('\\', '_').replace('..', '_')
                    safe_name = os.path.basename(safe_name)  # Get just the filename

                    # If no extension, try to detect from content
                    if '.' not in safe_name:
                        # Try to detect mime type from content
                        mime_type, _ = mimetypes.guess_type(original_name)
                        if not mime_type:
                            # Fallback: detect from content header
                            if content.startswith(b'\xff\xd8\xff'):
                                safe_name += '.jpg'
                            elif content.startswith(b'\x89PNG'):
                                safe_name += '.png'
                            elif content.startswith(b'GIF'):
                                safe_name += '.gif'
                            elif content.startswith(b'\x00\x00\x01\x00') or content.startswith(b'\x00\x00\x02\x00'):
                                safe_name += '.ico'
                            else:
                                safe_name += '.bin'  # fallback
                        else:
                            ext = mimetypes.guess_extension(mime_type)
                            if ext:
                                safe_name += ext

                    # Ensure filename is not empty and has reasonable length
                    if not safe_name or safe_name == '.' or len(safe_name) > 255:
                        # Generate a hash-based filename if original is problematic
                        hash_name = hashlib.md5(content).hexdigest()
                        # Try to preserve extension
                        ext = Path(original_name).suffix if Path(original_name).suffix else '.bin'
                        safe_name = f"{hash_name}{ext}"

                    # Create directory structure
                    image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', str(extracted.uploaded_file.id))
                    os.makedirs(image_dir, exist_ok=True)

                    # Full path for the image
                    image_path = os.path.join(image_dir, safe_name)

                    # Ensure we don't overwrite existing files by adding a counter
                    counter = 1
                    base_name = safe_name
                    while os.path.exists(image_path):
                        name_parts = os.path.splitext(base_name)
                        safe_name = f"{name_parts[0]}_{counter}{name_parts[1]}"
                        image_path = os.path.join(image_dir, safe_name)
                        counter += 1

                    # Save the image
                    with open(image_path, 'wb') as f:
                        f.write(content)

                    # Store the web-accessible path
                    web_path = f'/media/epub_images/{extracted.uploaded_file.id}/{safe_name}'
                    images.append(web_path)

                except Exception as e:
                    # Log the error but continue processing other images
                    print(f"Erro ao extrair imagem {item.get_name()}: {str(e)}")
                    continue

        extracted.images = images
        extracted.cover_image = cover_image_path  # Armazenar o caminho da capa

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
        # Log de auditoria antes de deletar
        AuditLog.objects.create(
            user=self.request.user,
            action='delete',
            description=f'Arquivo deletado: {instance.title or instance.file.name}',
            resource_id=instance.pk,
            resource_type='file',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            metadata={
                'file_size': instance.file.size,
                'file_name': instance.file.name
            }
        )
        super().perform_destroy(instance)

class DeleteAllBooksView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        files_qs = UploadedFile.objects.filter(user=user)
        count = files_qs.count()
        if count == 0:
            return Response({'message': 'Nenhum livro para remover', 'deleted': 0})

        # Gather IDs for logging metadata
        file_ids = list(files_qs.values_list('id', flat=True))

        # Cascade will remove ExtractedEpub and TranslatedEpub due to FK constraints
        files_qs.delete()

        AuditLog.objects.create(
            user=user,
            action='delete',
            description=f'Delete em massa de {count} arquivo(s) EPUB',
            resource_type='file',
            metadata={'deleted_count': count, 'file_ids': file_ids[:50]}  # limit metadata size
        )

        return Response({'message': 'Livros removidos', 'deleted': count})

class DeleteTranslationView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = TranslatedEpub.objects.all()

    def get_queryset(self):
        return TranslatedEpub.objects.filter(extracted_epub__uploaded_file__user=self.request.user)

    def perform_destroy(self, instance):
        # Log de auditoria antes de deletar
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
        
        # Log de auditoria
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
        from .tasks import extract_epub_sync
        extract_epub_sync(extracted.pk)

class TranslateEpubView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        obj_id = self.kwargs['pk']
        # Accept either ExtractedEpub ID or UploadedFile ID
        extracted = ExtractedEpub.objects.filter(pk=obj_id, uploaded_file__user=request.user).first()
        if not extracted:
            uploaded_file = get_object_or_404(UploadedFile, pk=obj_id, user=request.user)
            extracted = get_object_or_404(ExtractedEpub, uploaded_file=uploaded_file)
        
        chapter_param = request.data.get('chapter')
        source_lang = (request.data.get('source_lang') or 'auto').strip()
        target_lang = (request.data.get('target_lang') or 'pt').strip()

        # Basic language validation based on SupportedLanguagesView
        allowed_langs = {'auto','en','pt','es','fr','de','it','ja','ko','zh','ru','ar'}
        if target_lang not in allowed_langs:
            return Response({'error': 'Invalid target language'}, status=status.HTTP_400_BAD_REQUEST)
        if source_lang != 'auto' and source_lang not in allowed_langs:
            return Response({'error': 'Invalid source language'}, status=status.HTTP_400_BAD_REQUEST)
        
        chapter_index = None
        if chapter_param is not None:
            try:
                chapter_index = int(chapter_param)
                if not (0 <= chapter_index < len(extracted.chapters or [])):
                    return Response({'error': 'Chapter index out of range'}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({'error': 'Invalid chapter number'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Perform synchronous translation and return translation data
        try:
            from .tasks import translate_epub_sync
            translation = translate_epub_sync(
                extracted.pk, source_lang, target_lang, chapter_index, request.user.pk
            )
            serializer = TranslatedEpubSerializer(translation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        import tempfile
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
        import tempfile
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

class AuditLogsView(generics.ListAPIView):
    serializer_class = None  # We'll return raw data
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AuditLog.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Filtros opcionais
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
        
        # Paginação simples
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

class EpubReaderView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        """Retrieve EPUB content for the reader"""
        uploaded_file = get_object_or_404(UploadedFile, pk=file_id, user=request.user)

        # Check if the EPUB has been extracted
        extracted = ExtractedEpub.objects.filter(uploaded_file=uploaded_file).first()
        if not extracted:
            return Response({
                'error': 'EPUB content not extracted yet. Please extract content first.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Translations list
        translations_qs = TranslatedEpub.objects.filter(extracted_epub=extracted)
        translations_data = TranslatedEpubSerializer(translations_qs, many=True).data

        # User reading progress
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
            # Remove XML declaration / doctype quickly
            cleaned = re.sub(r'^\s*<\?xml[^>]*>\s*', '', raw_html, flags=re.IGNORECASE)
            cleaned = re.sub(r'<!DOCTYPE[^>]*>\s*', '', cleaned, flags=re.IGNORECASE)
            # Parse with BeautifulSoup to extract <body> content if present
            try:
                soup = BeautifulSoup(cleaned, 'html.parser')
                # Remove scripts and potentially dangerous tags
                for tag in soup.find_all(['script', 'iframe', 'object', 'embed', 'style']):
                    tag.decompose()
                body = soup.body
                # Prefer body contents; fallback to entire soup
                if body:
                    # Keep inner HTML of body
                    final_html = ''.join(str(c) for c in body.contents)
                else:
                    final_html = str(soup)
                # Strip outer <html> tags if still present
                final_html = re.sub(r'^\s*<html[^>]*>\s*', '', final_html, flags=re.IGNORECASE)
                final_html = re.sub(r'</html>\s*$', '', final_html, flags=re.IGNORECASE)
                return final_html.strip()
            except Exception:
                return cleaned

            
        sanitized_chapters = []
        chapters_obj = extracted.chapters if isinstance(extracted.chapters, list) else []
        for ch in chapters_obj:
            if isinstance(ch, dict):
                raw_content = ch.get('content') or ''
                if not isinstance(raw_content, str):
                    raw_content = str(raw_content)
                sanitized_chapters.append({
                    'title': ch.get('title') or '',
                    'content': sanitize_html(raw_content)
                })

        response_data = {
            'id': extracted.pk,
            'title': extracted.title,
            'metadata': extracted.metadata,
            'chapters': sanitized_chapters,
            'images': extracted.images,
            'translations': translations_data,
            'progress': progress_data,
        }

        return Response(response_data)



class ReadingProgressView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, extracted_epub_id, *args, **kwargs):
        extracted = get_object_or_404(ExtractedEpub, pk=extracted_epub_id, uploaded_file__user=request.user)

        payload = {
            'current_chapter': int(request.data.get('current_chapter', 0) or 0),
            'current_position': int(request.data.get('current_position', 0) or 0),
            'progress_percentage': float(request.data.get('progress_percentage', 0.0) or 0.0),
        }
        serializer = ReadingProgressSerializer(data={ 'extracted_epub': extracted.pk, **payload })

        if serializer.is_valid():
            # upsert by user + extracted_epub
            obj, _created = ReadingProgress.objects.update_or_create(
                user=request.user,
                extracted_epub=extracted,
                defaults=payload
            )

            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action='read',
                description='Reading progress updated',
                resource_id=extracted.pk,
                resource_type='extraction',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={
                    'current_chapter': obj.current_chapter,
                    'current_position': obj.current_position,
                    'progress_percentage': obj.progress_percentage,
                }
            )

            return Response(ReadingProgressSerializer(obj).data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        def post(self, request, *args, **kwargs):  # type: ignore
            return self._post_impl(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._post_impl(request, *args, **kwargs)

    def _post_impl(self, request, *args, **kwargs):
        from .ao3_utils import extract_work_id, fetch_ao3_work, build_epub_from_ao3
        from .tasks import extract_epub_sync
        from django.core.files import File
        import os
        import uuid
        import logging
        import traceback
        import time

        log = logging.getLogger(__name__)
        start_ts = time.time()
        corr_id = uuid.uuid4().hex[:12]
        log.info(f"[AO3Import][{corr_id}] Início request data_keys={list(request.data.keys())}")
        url = request.data.get('url', '').strip()
        if not url:
            log.warning(f"[AO3Import][{corr_id}] URL ausente")
            return Response({'error': 'URL required', 'debug_id': corr_id}, status=status.HTTP_400_BAD_REQUEST)

        work_id = extract_work_id(url)
        if not work_id:
            log.warning(f"[AO3Import][{corr_id}] URL inválida: {url}")
            return Response({'error': 'Invalid AO3 work URL', 'debug_id': corr_id}, status=status.HTTP_400_BAD_REQUEST)

        # Check duplicate by metadata.external_work_id
        existing_extracted = ExtractedEpub.objects.filter(metadata__external_work_id=work_id, uploaded_file__user=request.user).first()
        if existing_extracted:
            log.info(f"[AO3Import][{corr_id}] Duplicado encontrado extracted_id={existing_extracted.id}")
            return Response({
                'already_imported': True,
                'uploaded_file_id': existing_extracted.uploaded_file.id,
                'extracted_epub_id': existing_extracted.id,
                'title': existing_extracted.title,
                'debug_id': corr_id,
            })
        try:
            log.info(f"[AO3Import][{corr_id}] Fetching AO3 work_id={work_id}")
            data = fetch_ao3_work(work_id)
            log.info(f"[AO3Import][{corr_id}] Fetch OK title='{data.get('title')}' chapters={len(data.get('chapters', []))}")
        except Exception as e:
            log.error(f"[AO3Import][{corr_id}] Erro fetch: {e}\n{traceback.format_exc()}")
            return Response({'error': f'Failed fetching AO3 work: {e}', 'debug_id': corr_id}, status=status.HTTP_400_BAD_REQUEST)

        # Simple size guard
        total_chars = sum(len(c['html']) for c in data['chapters'])
        if total_chars > 500_000:
            log.warning(f"[AO3Import][{corr_id}] Excedeu limite chars={total_chars}")
            return Response({'error': 'Work too large for direct import (limit 500k chars)', 'debug_id': corr_id}, status=413)

        try:
            log.info(f"[AO3Import][{corr_id}] Gerando EPUB")
            epub_path = build_epub_from_ao3(data, url)
            log.info(f"[AO3Import][{corr_id}] EPUB gerado path={epub_path}")
        except Exception as e:
            log.error(f"[AO3Import][{corr_id}] Erro build EPUB: {e}\n{traceback.format_exc()}")
            return Response({'error': f'Failed building EPUB: {e}', 'debug_id': corr_id}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save as UploadedFile
        filename = f"ao3_{work_id}.epub"
        with open(epub_path, 'rb') as f:
            django_file = File(f, name=filename)
            uploaded = UploadedFile.objects.create(user=request.user, file=django_file, title=data['title'][:255])
        # Create ExtractedEpub and run extraction pipeline for consistency
        extracted = ExtractedEpub.objects.create(uploaded_file=uploaded, title=data['title'][:255], metadata={
            'source_type': 'ao3',
            'source_url': url,
            'external_work_id': work_id,
            'authors': data.get('authors'),
            'summary': data.get('summary'),
            'fandoms': data.get('fandoms'),
            'tags': data.get('tags'),
            'language': data.get('language'),
            'word_count': data.get('word_count'),
            'published': data.get('published'),
            'updated': data.get('updated')
        })
        try:
            log.info(f"[AO3Import][{corr_id}] Extraindo EPUB para DB extracted_id={extracted.id}")
            extract_epub_sync(extracted.id)
        except Exception as e:
            log.error(f"[AO3Import][{corr_id}] Erro extração pipeline: {e}\n{traceback.format_exc()}")

        # Audit logs
        AuditLog.objects.create(
            user=request.user,
            action='upload',
            description=f'Arquivo AO3 importado: {data["title"]}',
            resource_id=uploaded.pk,
            resource_type='file',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'origin': 'ao3', 'work_id': work_id}
        )
        AuditLog.objects.create(
            user=request.user,
            action='extract',
            description='Extração pós-import AO3',
            resource_id=extracted.pk,
            resource_type='extraction',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'origin': 'ao3', 'work_id': work_id}
        )

        # Cleanup temp file
        try:
            os.remove(epub_path)
        except OSError:
            pass

        metadata_preview = {
            'authors': data.get('authors'),
            'summary': data.get('summary'),
            'fandoms': data.get('fandoms'),
            'language': data.get('language'),
        }
        duration_ms = int((time.time() - start_ts)*1000)
        log.info(f"[AO3Import][{corr_id}] Sucesso uploaded_id={uploaded.id} extracted_id={extracted.id} duration_ms={duration_ms}")
        return Response({
            'uploaded_file_id': uploaded.id,
            'extracted_epub_id': extracted.id,
            'title': data['title'],
            'metadata_preview': metadata_preview,
            'already_imported': False,
            'debug_id': corr_id,
        }, status=status.HTTP_201_CREATED)


class ReaderImageView(generics.GenericAPIView):
    """Serve images for the reader with the /reader/images/ URL pattern"""
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id, image_name):
        """Serve an image file for a specific uploaded file"""
        try:
            # Get the uploaded file and verify ownership
            uploaded_file = get_object_or_404(UploadedFile, pk=file_id, user=request.user)
            
            # Construct the image path
            image_path = os.path.join(
                settings.MEDIA_ROOT, 
                'epub_images', 
                str(uploaded_file.pk), 
                image_name
            )
            
            # Check if file exists
            if not os.path.exists(image_path):
                raise Http404("Image not found")
            
            # Determine content type based on file extension
            content_type = 'image/jpeg'  # default
            if image_name.lower().endswith('.png'):
                content_type = 'image/png'
            elif image_name.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif image_name.lower().endswith('.webp'):
                content_type = 'image/webp'
            elif image_name.lower().endswith('.svg'):
                content_type = 'image/svg+xml'
            
            # Return the image file
            return FileResponse(
                open(image_path, 'rb'),
                content_type=content_type
            )
            
        except Exception as e:
            raise Http404(f"Image not found: {str(e)}")


