from .models import ExtractedEpub, TranslatedEpub, AuditLog
from celery import shared_task
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from ebooklib import epub
import ebooklib
import os
import hashlib
from pathlib import Path
from django.conf import settings
import time
from typing import Iterable
import bleach


def extract_epub_sync(extracted_epub_id):
    """
    Synchronous EPUB extraction
    """
    extracted = ExtractedEpub.objects.get(id=extracted_epub_id)
    
    book = epub.read_epub(extracted.uploaded_file.file.path)
    
    # Extract metadata
    metadata = {}
    for item in book.get_metadata('DC', 'title'):
        metadata['title'] = item[0]
    for item in book.get_metadata('DC', 'creator'):
        metadata['author'] = item[0]
    extracted.title = metadata.get('title', '')
    extracted.metadata = metadata
    
    # Extract chapters
    chapters = []
    document_items = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
    
    # Sanitização helper (duplicada mínima aqui para evitar dependência cíclica)
    import re
    def sanitize_html(raw_html: str) -> str:
        if not raw_html:
            return ''
        tmp = re.sub(r'^\s*<\?xml[^>]*?>', '', raw_html, flags=re.IGNORECASE)
        tmp = re.sub(r'<!DOCTYPE[^>]*?>', '', tmp, flags=re.IGNORECASE)
        soup_local = BeautifulSoup(tmp, 'html.parser')
        for tag in soup_local.find_all(['script','iframe','object','embed','style']):
            tag.decompose()
        body = soup_local.body
        if body:
            inner = ''.join(str(c) for c in body.contents)
        else:
            inner = str(soup_local)
        inner = re.sub(r'^\s*<html[^>]*>','', inner, flags=re.IGNORECASE)
        inner = re.sub(r'</html>\s*$','', inner, flags=re.IGNORECASE)
        return inner.strip()

    for item in document_items:
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        title_tag = soup.find('title')
        title_text = title_tag.get_text() if title_tag else item.get_name()
        raw_content = item.get_content().decode('utf-8')
        cleaned_content = sanitize_html(raw_content)
        chapters.append({'title': title_text, 'content': cleaned_content})
    
    extracted.chapters = chapters
    
    # Extract images
    images = []
    image_items = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_IMAGE]
    
    for item in image_items:
        try:
            # Get the original name and content
            original_name = item.get_name()
            content = item.get_content()
            
            # Create safe filename
            safe_name = original_name.replace('/', '_').replace('\\', '_').replace('..', '_')
            safe_name = os.path.basename(safe_name)
            
            # If no extension, try to detect from content
            if '.' not in safe_name:
                if content.startswith(b'\xff\xd8\xff'):
                    safe_name += '.jpg'
                elif content.startswith(b'\x89PNG'):
                    safe_name += '.png'
                elif content.startswith(b'GIF'):
                    safe_name += '.gif'
                else:
                    safe_name += '.bin'
            
            # Ensure filename is not empty
            if not safe_name or safe_name == '.':
                hash_name = hashlib.md5(content).hexdigest()
                ext = Path(original_name).suffix if Path(original_name).suffix else '.bin'
                safe_name = f"{hash_name}{ext}"
            
            # Create directory structure
            image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', str(extracted.uploaded_file.pk))
            os.makedirs(image_dir, exist_ok=True)
            
            # Full path for the image
            image_path = os.path.join(image_dir, safe_name)
            
            # Ensure we don't overwrite existing files
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
            web_path = f'/media/epub_images/{extracted.uploaded_file.pk}/{safe_name}'
            images.append(web_path)
            
        except Exception as e:
            print(f"Error extracting image {item.get_name()}: {str(e)}")
            continue
    
    extracted.images = images
    extracted.save()
    
    return extracted


def translate_epub_sync(extracted_epub_id, source_lang, target_lang, chapter_index=None, user_id=None):
    """
    Synchronous EPUB translation
    """
    extracted_epub = ExtractedEpub.objects.get(id=extracted_epub_id)
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    start_time = time.time()
    text_nodes_count = 0

    # Translate title
    translated_title = ''
    if extracted_epub.title:
        try:
            translated_title = translate_with_retry(translator, extracted_epub.title)
        except Exception as e:
            print(f"Error translating title: {str(e)}")
            translated_title = extracted_epub.title

    # Translate metadata
    translated_metadata = {}
    if extracted_epub.metadata and isinstance(extracted_epub.metadata, dict):
        for key, value in extracted_epub.metadata.items():
            if isinstance(value, str) and value.strip():
                try:
                    translated_metadata[key] = translate_with_retry(translator, value)
                except Exception as e:
                    print(f"Error translating metadata {key}: {str(e)}")
                    translated_metadata[key] = value
            else:
                translated_metadata[key] = value

    # Translate chapters
    translated_chapters = []
    if chapter_index is not None and extracted_epub.chapters and isinstance(extracted_epub.chapters, list):
        if 0 <= chapter_index < len(extracted_epub.chapters):
            chapters_to_translate = [extracted_epub.chapters[chapter_index]]
        else:
            raise ValueError(f"Chapter index {chapter_index} out of range")
    else:
        chapters_to_translate = extracted_epub.chapters or []

    for i, chapter in enumerate(chapters_to_translate):
        translated_chapter = {
            'title': '',
            'content': chapter['content']
        }
        
        # Translate chapter title
        try:
            if chapter.get('title'):
                translated_chapter['title'] = translate_with_retry(translator, chapter['title'])
            else:
                translated_chapter['title'] = f'Capítulo {i+1}'
        except Exception as e:
            print(f"Error translating chapter title {i+1}: {str(e)}")
            translated_chapter['title'] = chapter.get('title', f'Capítulo {i+1}')
        
        # Translate chapter content
        try:
            translated_html, nodes = translate_html(chapter['content'], translator)
            text_nodes_count += nodes
            translated_chapter['content'] = translated_html
        except Exception as e:
            print(f"Error translating chapter content {i+1}: {str(e)}")
        
        translated_chapters.append(translated_chapter)

    # Save translation idempotently
    translation, _created = TranslatedEpub.objects.update_or_create(
        extracted_epub=extracted_epub,
        source_lang=source_lang,
        target_lang=target_lang,
        chapter_index=chapter_index,
        defaults={
            'translated_title': translated_title,
            'translated_metadata': translated_metadata,
            'translated_chapters': translated_chapters,
        }
    )

    # Audit log
    if user_id:
        duration_ms = int((time.time() - start_time) * 1000)
        AuditLog.objects.create(
            user_id=user_id,
            action='translate',
            description=f'Translation completed: {source_lang} -> {target_lang}',
            resource_id=translation.pk,
            resource_type='translation',
            metadata={
                'extracted_epub_id': extracted_epub_id,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'chapter_index': chapter_index,
                'duration_ms': duration_ms,
                'text_nodes_translated': text_nodes_count
            }
        )

    return translation


def translate_html(html_content, translator):
    """
    Translate HTML content while preserving structure, with chunking, retries and sanitization.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Allowed tags/attrs for final sanitization
        allowed_tags = [
            'p','div','span','strong','em','b','i','u','a','ul','ol','li','br','hr','h1','h2','h3','h4','h5','h6',
            'img','blockquote','code','pre','table','thead','tbody','tr','td','th'
        ]
        allowed_attrs = {
            '*': ['class','id','style'],
            'a': ['href','title','target','rel'],
            'img': ['src','alt','title']
        }

        text_nodes = 0
        for element in soup.find_all(string=True):
            if hasattr(element, 'parent') and element.strip() and element.parent.name not in ['script', 'style']:
                original_text = element.strip()
                if original_text:
                    # Split long text into chunks respecting word boundaries
                    chunks = list(chunk_text(original_text, 4000))
                    translated_chunks = []
                    for ch in chunks:
                        translated_chunk = translate_with_retry(translator, ch)
                        translated_chunks.append(translated_chunk or ch)  # Fallback to original if translation fails
                    translated = ''.join(translated_chunks)
                    if translated and translated != original_text:
                        element.replace_with(translated)
                    text_nodes += 1

        cleaned = bleach.clean(str(soup), tags=allowed_tags, attributes=allowed_attrs, strip=False)
        return cleaned, text_nodes
    except Exception as e:
        print(f"General error in HTML translation: {str(e)}")
        return html_content, 0


def translate_with_retry(translator, text: str, retries: int = 2, backoff: float = 0.5) -> str:
    last_err = None
    for attempt in range(retries + 1):
        try:
            result = translator.translate(text)
            return result if result is not None else text
        except Exception as e:
            last_err = e
            time.sleep(backoff * (2 ** attempt))
    print(f"Translation failed after retries: {last_err}")
    # Fallback to original text
    return text


def chunk_text(text: str, max_len: int) -> Iterable[str]:
    if len(text) <= max_len:
        yield text
        return
    words = text.split()
    buf = []
    cur_len = 0
    for w in words:
        add_len = len(w) + (1 if buf else 0)
        if cur_len + add_len > max_len:
            yield ' '.join(buf)
            buf = [w]
            cur_len = len(w)
        else:
            buf.append(w)
            cur_len += add_len
    if buf:
        yield ' '.join(buf)


# Celery tasks wrappers
@shared_task(name='uploads.translate_epub_task')
def translate_epub_task(extracted_epub_id, source_lang, target_lang, chapter_index=None, user_id=None):
    """Async task wrapper for translate_epub_sync returning translation ID"""
    translation = translate_epub_sync(extracted_epub_id, source_lang, target_lang, chapter_index, user_id)
    return translation.id

@shared_task(name='uploads.extract_epub_task')
def extract_epub_task(extracted_epub_id):
    extracted = extract_epub_sync(extracted_epub_id)
    return extracted.id
