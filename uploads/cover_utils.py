"""
Utilitários centralizados para geração de capas de EPUB
"""
import os
import io
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings


def generate_cover_image(
    title: str,
    author: Optional[str] = None,
    footer_text: str = "Generated Cover",
    width: int = 600,
    height: int = 900,
    background_color = (128, 0, 0),  # type: ignore
    title_color: str = 'white',
    author_color: str = '#ffd',
    footer_color: str = '#eee'
) -> Image.Image:
    """
    Gera uma imagem de capa para EPUB.
    
    Args:
        title: Título do livro
        author: Nome do autor (opcional)
        footer_text: Texto do rodapé
        width: Largura da imagem
        height: Altura da imagem
        background_color: Cor de fundo (R, G, B)
        title_color: Cor do texto do título
        author_color: Cor do texto do autor
        footer_color: Cor do texto do rodapé
        
    Returns:
        PIL Image object
    """
    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img)
    
    # Carrega fontes ou usa padrão
    try:
        font_title = ImageFont.truetype('arial.ttf', 40)
        font_author = ImageFont.truetype('arial.ttf', 28)
        font_footer = ImageFont.truetype('arial.ttf', 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_author = ImageFont.load_default()
        font_footer = ImageFont.load_default()

    def wrap_text(text: str, max_width: int, font):
        """Quebra o texto em múltiplas linhas se necessário"""
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

    # Desenha o título
    title_lines = wrap_text(title[:200], width - 80, font_title)  # margem de 40px de cada lado
    y = 120
    
    for line in title_lines[:8]:  # máximo 8 linhas
        line_width = draw.textlength(line, font=font_title)
        x = (width - line_width) / 2
        draw.text((x, y), line, font=font_title, fill=title_color)
        y += 50

    # Desenha o autor se fornecido
    if author:
        author_text = author[:100]  # limita o tamanho do autor
        author_width = draw.textlength(author_text, font=font_author)
        x = (width - author_width) / 2
        draw.text((x, y + 20), author_text, font=font_author, fill=author_color)

    # Desenha o rodapé
    footer_width = draw.textlength(footer_text, font=font_footer)
    x = (width - footer_width) / 2
    draw.text((x, height - 60), footer_text, font=font_footer, fill=footer_color)

    return img


def generate_cover_bytes(
    title: str,
    author: Optional[str] = None,
    footer_text: str = "Generated Cover",
    **kwargs
) -> bytes:
    """
    Gera uma capa e retorna como bytes JPEG.
    
    Args:
        title: Título do livro
        author: Nome do autor (opcional)
        footer_text: Texto do rodapé
        **kwargs: Argumentos adicionais para generate_cover_image
        
    Returns:
        Bytes da imagem JPEG
    """
    img = generate_cover_image(title, author, footer_text, **kwargs)
    
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()


def generate_cover_file(
    title: str,
    author: Optional[str] = None,
    footer_text: str = "Generated Cover",
    output_dir: Optional[str] = None,
    filename: str = "generated_cover.jpg",
    uploaded_file_id: Optional[int] = None,
    **kwargs
) -> str:
    """
    Gera uma capa e salva como arquivo, retornando o path web.
    
    Args:
        title: Título do livro
        author: Nome do autor (opcional)
        footer_text: Texto do rodapé
        output_dir: Diretório de saída (se None, usa padrão do Django)
        filename: Nome do arquivo
        uploaded_file_id: ID do arquivo carregado (para criar path padrão)
        **kwargs: Argumentos adicionais para generate_cover_image
        
    Returns:
        Path web da imagem salva
    """
    img = generate_cover_image(title, author, footer_text, **kwargs)
    
    # Define diretório de saída
    if output_dir is None:
        if uploaded_file_id is not None:
            image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', str(uploaded_file_id))
        else:
            image_dir = os.path.join(settings.MEDIA_ROOT, 'epub_images', 'generated')
    else:
        image_dir = output_dir
    
    # Cria diretório se não existir
    os.makedirs(image_dir, exist_ok=True)
    
    # Salva arquivo
    cover_path = os.path.join(image_dir, filename)
    img.save(cover_path, format='JPEG', quality=85)
    
    # Retorna path web
    if uploaded_file_id is not None:
        web_path = f'/media/epub_images/{uploaded_file_id}/{filename}'
    else:
        web_path = f'/media/epub_images/generated/{filename}'
    
    return web_path


def generate_ao3_cover_bytes(title: str, author: Optional[str] = None) -> bytes:
    """
    Gera uma capa específica para conteúdo do AO3.
    
    Args:
        title: Título do trabalho
        author: Nome do autor (opcional)
        
    Returns:
        Bytes da imagem JPEG
    """
    return generate_cover_bytes(
        title=title,
        author=author,
        footer_text="Imported from AO3"
    )


def generate_epub_cover_file(
    title: str, 
    author: Optional[str] = None, 
    uploaded_file_id: Optional[int] = None
) -> str:
    """
    Gera uma capa para EPUB extraído e salva no sistema de arquivos.
    
    Args:
        title: Título do livro
        author: Nome do autor (opcional)
        uploaded_file_id: ID do arquivo carregado
        
    Returns:
        Path web da imagem salva
    """
    return generate_cover_file(
        title=title,
        author=author,
        footer_text="Generated Cover",
        uploaded_file_id=uploaded_file_id,
        filename="generated_cover.jpg"
    )