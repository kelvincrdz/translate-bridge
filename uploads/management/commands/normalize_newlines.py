from django.core.management.base import BaseCommand
from uploads.models import ExtractedEpub, TranslatedEpub
import bleach
from typing import List, Dict

ALLOWED_TAGS = ['p','div','span','strong','em','b','i','u','a','ul','ol','li','br','hr','h1','h2','h3','h4','h5','h6','img','blockquote','code','pre','table','thead','tbody','tr','td','th']
ALLOWED_ATTRS = {'*': ['class','id','style'], 'a': ['href','title','target','rel'], 'img': ['src','alt','title']}


def needs_normalization(html: str) -> bool:
    if not html:
        return False
    lowered = html.lower()
    # Se já contém tags de parágrafo ou quebra explícita, assume formatado
    if '<p' in lowered or '<div' in lowered or '<br' in lowered:
        return False
    # Se parece markup (qualquer tag), não mexe
    if '<' in html and '>' in html:
        return False
    # Se tem múltiplas quebras de linha, candidato
    return '\n' in html


def normalize_plain_text(html: str) -> str:
    if not html:
        return html
    normalized = html.replace('\r\n', '\n').replace('\r', '\n')
    blocks = [b.strip() for b in normalized.split('\n\n') if b.strip()]
    if len(blocks) > 1:
        parts: List[str] = []
        for b in blocks:
            safe = bleach.clean(b, tags=[], strip=True)
            safe = safe.replace('\n', '<br />')
            parts.append(f'<p>{safe}</p>')
        return ''.join(parts)
    # Single block: só converter quebras simples
    safe = bleach.clean(normalized, tags=[], strip=True).replace('\n', '<br />')
    return safe

class Command(BaseCommand):
    help = 'Normaliza capítulos (e traduções) que ainda estão em texto plano com \n para HTML com <p>/<br />.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Mostra o que seria alterado sem salvar')
        parser.add_argument('--limit', type=int, default=None, help='Limite de registros a processar por tipo')
        parser.add_argument('--sample', type=int, default=0, help='Quantidade de exemplos de antes/depois a exibir')

    def handle(self, *args, **options):
        dry = options['dry_run']
        limit = options.get('limit')
        sample = options.get('sample') or 0

        total_checked = 0
        total_changed = 0
        samples: List[Dict[str, str]] = []

        # Processa ExtractedEpub
        qs = ExtractedEpub.objects.exclude(chapters=None)
        if limit:
            qs = qs[:limit]
        for extracted in qs:
            changed = False
            chapters = extracted.chapters or []
            for ch in chapters:
                content = ch.get('content') or ''
                if needs_normalization(content):
                    before = content
                    ch['content'] = normalize_plain_text(content)
                    changed = True
                    total_changed += 1
                    if len(samples) < sample:
                        samples.append({'type': 'extracted', 'id': extracted.id, 'before': before[:400], 'after': ch['content'][:400]})
                total_checked += 1
            if changed and not dry:
                extracted.save(update_fields=['chapters'])

        # Processa TranslatedEpub
        tqs = TranslatedEpub.objects.exclude(translated_chapters=None)
        if limit:
            tqs = tqs[:limit]
        for tr in tqs:
            changed = False
            chapters = tr.translated_chapters or []
            for ch in chapters:
                content = ch.get('content') or ''
                if needs_normalization(content):
                    before = content
                    ch['content'] = normalize_plain_text(content)
                    changed = True
                    total_changed += 1
                    if len(samples) < sample:
                        samples.append({'type': 'translated', 'id': tr.id, 'before': before[:400], 'after': ch['content'][:400]})
                total_checked += 1
            if changed and not dry:
                tr.save(update_fields=['translated_chapters'])

        self.stdout.write(self.style.SUCCESS(f'Verificados capítulos: {total_checked} | Alterados: {total_changed}'))
        if dry:
            self.stdout.write('(dry-run) Nenhuma alteração salva.')
        if samples:
            self.stdout.write('\nAmostras:')
            for s in samples:
                self.stdout.write(f"[{s['type']} id={s['id']}] BEFORE:\n{s['before']}\n--- AFTER:\n{s['after']}\n---")
