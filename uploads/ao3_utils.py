import re
import tempfile
import datetime
from typing import Dict, Any, List
import bleach
from ebooklib import epub
from .cover_utils import generate_ao3_cover_bytes

ALLOWED_TAGS = [
    'p','div','span','strong','em','b','i','u','a','ul','ol','li','br','hr','h1','h2','h3','h4','h5','h6',
    'img','blockquote','code','pre','table','thead','tbody','tr','td','th'
]
ALLOWED_ATTRS = {
    '*': ['class','id','style'],
    'a': ['href','title','target','rel'],
    'img': ['src','alt','title']
}

WORK_URL_REGEX = re.compile(r'^https://(?:www\.)?archiveofourown.org/works/(\d+)')


def extract_work_id(url: str) -> str | None:
    m = WORK_URL_REGEX.match(url.strip())
    return m.group(1) if m else None


def sanitize_html(html: str) -> str:
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def fetch_ao3_work(work_id: str) -> Dict[str, Any]:
    """Fetch AO3 work data using ao3-api. Returns dict with metadata and chapters.
    Structure:
    {
      'title': str,
      'authors': [str],
      'summary': str,
      'fandoms': [str],
      'language': str,
      'tags': { 'rating':..., 'warnings':[], 'relationships':[], 'characters':[], 'freeforms':[] },
      'chapters': [ { 'index': int, 'title': str, 'html': str } ],
      'word_count': int,
      'published': str (ISO),
      'updated': str (ISO)
    }
    """
    import AO3  # type: ignore  # Biblioteca dinâmica
    import logging
    import traceback
    import time
    log = logging.getLogger(__name__)
    t0 = time.time()
    work = AO3.Work(int(work_id))

    chapters_list: List[Dict[str, Any]] = []
    for idx, ch in enumerate(work.chapters):
        title = getattr(ch, 'title', None) or f"Chapter {idx+1}"
        raw_html: str | None = None
        for attr in ('content', 'html', 'text', 'body'):
            if hasattr(ch, attr):
                candidate = getattr(ch, attr)
                if callable(candidate):
                    try:
                        candidate = candidate()
                    except Exception:
                        candidate = None
                if isinstance(candidate, str) and candidate.strip():
                    raw_html = candidate
                    break
        if (raw_html is None or not raw_html.strip()) and hasattr(ch, 'load_content'):
            try:
                ch.load_content()
                for attr in ('content', 'html', 'text', 'body'):
                    if hasattr(ch, attr):
                        candidate = getattr(ch, attr)
                        if callable(candidate):
                            try:
                                candidate = candidate()
                            except Exception:
                                candidate = None
                        if isinstance(candidate, str) and candidate.strip():
                            raw_html = candidate
                            break
            except Exception as e:
                log.warning(f"[AO3Utils] Falha load_content chapter={idx+1}: {e}")
        if raw_html is None or not raw_html.strip():
            log.warning(f"[AO3Utils] Capítulo {idx+1} sem conteúdo detectado; inserindo placeholder")
            raw_html = '<p><em>(Capítulo sem conteúdo extraído)</em></p>'
        if raw_html and raw_html.strip() and '<p' not in raw_html.lower() and '<div' not in raw_html.lower() and '<br' not in raw_html.lower():
            normalized = raw_html.replace('\r\n', '\n\n').replace('\r', '\n')
            blocks = [b.strip() for b in normalized.split('\n\n') if b.strip()]
            if len(blocks) > 1:
                raw_html = ''.join(f'<p>{bleach.clean(b, tags=[], strip=True).replace('\n', '<br />')}</p>' for b in blocks)
            else:
                raw_html = bleach.clean(normalized, tags=[], strip=True).replace('\n', '<br />')
        try:
            html = sanitize_html(raw_html)
        except Exception:
            log.error(f"[AO3Utils] Erro sanitizando capítulo {idx+1}\n{traceback.format_exc()}")
            html = '<p><em>(Erro ao sanitizar capítulo)</em></p>'
        chapters_list.append({'index': idx+1, 'title': title, 'html': html})
    log.info(f"[AO3Utils] Work {work_id} processado: chapters={len(chapters_list)} tempo_ms={int((time.time()-t0)*1000)}")

    data = {
        'title': work.title or f'AO3 Work {work_id}',
        'authors': [a.username for a in work.authors] if getattr(work, 'authors', None) else [],
        'summary': sanitize_html(work.summary or ''),
        'fandoms': getattr(work, 'fandoms', []) or [],
        'language': getattr(work, 'language', 'en'),
        'tags': {
            'rating': getattr(work, 'rating', ''),
            'warnings': getattr(work, 'warnings', []) or [],
            'relationships': getattr(work, 'relationships', []) or [],
            'characters': getattr(work, 'characters', []) or [],
            'freeforms': getattr(work, 'freeforms', []) or [],
        },
        'chapters': chapters_list,
        'word_count': getattr(work, 'words', 0) or 0,
        'published': getattr(work, 'date_published', None) and work.date_published.isoformat(),
        'updated': getattr(work, 'date_updated', None) and work.date_updated.isoformat(),
    }
    return data


def _generate_cover(title: str, author: str | None) -> bytes:
    return generate_ao3_cover_bytes(title, author)


def build_epub_from_ao3(data: Dict[str, Any], source_url: str) -> str:
    """Create an EPUB file from AO3 data using ebooklib. Returns path to temp epub."""
    book = epub.EpubBook()
    book.set_identifier(f"ao3-{hash(source_url) & 0xffffffff}")
    book.set_title(data['title'])
    if data['authors']:
        for a in data['authors']:
            book.add_author(a)
    else:
        book.add_author('Unknown')

    if data.get('summary'):
        book.add_metadata('DC', 'description', data['summary'])
    for fandom in data.get('fandoms', []):
        book.add_metadata('DC', 'subject', fandom)
    tag_groups = [data.get('tags', {}).get('relationships', []), data.get('tags', {}).get('characters', []), data.get('tags', {}).get('freeforms', [])]
    for group in tag_groups:
        for tag in group:
            book.add_metadata('DC', 'subject', tag)
    book.add_metadata('DC', 'language', data.get('language', 'en'))
    book.add_metadata(None, 'meta', '', {'name': 'source', 'content': source_url})
    book.add_metadata(None, 'meta', '', {'name': 'imported_at', 'content': datetime.datetime.utcnow().isoformat()})

    author_str = ', '.join(data['authors'])[:120] if data['authors'] else ''
    cover_bytes = _generate_cover(data['title'], author_str)
    book.set_cover('cover.jpg', cover_bytes)

    spine = ['nav']
    toc_items = []

    # Title page
    title_html = f"""<h1>{data['title']}</h1><p><strong>Author:</strong> {author_str}</p><p><strong>Source:</strong> <a href='{source_url}'>{source_url}</a></p><p>{data.get('summary','')}</p>"""
    title_page = epub.EpubHtml(title='Title Page', file_name='titlepage.xhtml', content=title_html)
    book.add_item(title_page)
    spine.append(title_page)
    toc_items.append(title_page)

    chapter_items = []
    for ch in data['chapters']:
        c = epub.EpubHtml(title=ch['title'], file_name=f"chapter_{ch['index']:03}.xhtml", content=f"<h2>{ch['title']}</h2>" + ch['html'])
        book.add_item(c)
        chapter_items.append(c)
    toc_items.extend(chapter_items)
    spine.extend(chapter_items)

    end_html = "<h2>End Notes</h2><p>Generated for personal use. Original at AO3.</p>"
    end_page = epub.EpubHtml(title='End Notes', file_name='endnotes.xhtml', content=end_html)
    book.add_item(end_page)
    spine.append(end_page)
    toc_items.append(end_page)

    book.toc = toc_items
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    tmp = tempfile.NamedTemporaryFile(suffix='.epub', delete=False)
    epub.write_epub(tmp.name, book, {})
    path = tmp.name
    tmp.close()
    return path
