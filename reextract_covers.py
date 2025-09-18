#!/usr/bin/env python3
"""
Script para re-extrair capas de EPUBs existentes
"""
import os
import sys
import django
from django.conf import settings
from pathlib import Path

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'epub_api.settings')
django.setup()

#!/usr/bin/env python3
"""
Script para re-extrair capas de EPUBs existentes e gerar capas quando necessário
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'epub_api.settings')
django.setup()

from uploads.models import ExtractedEpub, UploadedFile
import ebooklib
from ebooklib import epub

def re_extract_covers():
    """Re-extrai capas para todos os EPUBs existentes"""
    extracted_epubs = ExtractedEpub.objects.all()
    
    print(f"Encontrados {extracted_epubs.count()} EPUBs extraídos")
    
    for extracted in extracted_epubs:
        print(f"Processando: {extracted.title}")
        
        try:
            # Verificar se o arquivo ainda existe
            if not os.path.exists(extracted.uploaded_file.file.path):
                print(f"  ✗ Arquivo não encontrado: {extracted.uploaded_file.file.path}")
                continue
                
            # Abrir o EPUB
            book = epub.read_epub(extracted.uploaded_file.file.path)
            
            # Simular as funções internas da view

            
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
                    print("    Pillow não está instalado. Não é possível gerar capa.")
                    return None
                except Exception as e:
                    print(f"    Erro ao gerar capa: {str(e)}")
                    return None
            
            def _extract_cover_image(book, extracted):
                """Função extraída da view para re-extrair capas"""
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
                        print(f"    Erro ao extrair capa: {str(e)}")
                        return None
                
                return None
            
            # Extrair capa
            cover_path = _extract_cover_image(book, extracted)
            
            # Se não encontrou capa, gerar uma com Pillow
            if not cover_path:
                title = extracted.title or 'Título Desconhecido'
                author = extracted.metadata.get('author', '') if extracted.metadata else ''
                cover_path = _generate_cover_for_ao3(title, author, extracted)
                
                if cover_path:
                    print(f"  ✓ Capa gerada com Pillow: {cover_path}")
                else:
                    print(f"  ✗ Falha ao gerar capa")
            else:
                print(f"  ✓ Capa extraída: {cover_path}")
            
            if cover_path:
                extracted.cover_image = cover_path
                extracted.save()
            
        except Exception as e:
            print(f"  ✗ Erro: {str(e)}")
    
    print("Processo concluído!")

if __name__ == "__main__":
    re_extract_covers()