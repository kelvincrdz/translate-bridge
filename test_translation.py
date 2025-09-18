#!/usr/bin/env python3
"""
Script de teste para verificar se a tradução está funcionando
"""
import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'epub_api.settings')
django.setup()

from uploads.models import ExtractedEpub, UploadedFile, TranslatedEpub
from django.contrib.auth.models import User

def test_translation():
    """Testa se existe algum EPUB extraído e tenta traduzir"""
    print("=== TESTE DE TRADUÇÃO ===")
    
    # Listar todos os usuários
    users = User.objects.all()
    print(f"Usuários disponíveis: {[user.username for user in users]}")
    
    if not users:
        print("ERRO: Nenhum usuário encontrado!")
        return
    
    user = users.first()
    print(f"Usando usuário: {user.username}")
    
    # Listar EPUBs extraídos do usuário
    extracted_epubs = ExtractedEpub.objects.filter(uploaded_file__user=user)
    print(f"EPUBs extraídos encontrados para {user.username}: {extracted_epubs.count()}")
    
    # Verificar EPUBs extraídos para todos os usuários
    all_extracted = ExtractedEpub.objects.all()
    print(f"Total de EPUBs extraídos no sistema: {all_extracted.count()}")
    
    if all_extracted.exists():
        print("EPUBs encontrados:")
        for epub in all_extracted:
            print(f"- ID: {epub.pk}, Título: {epub.title}, Usuário: {epub.uploaded_file.user.username}")
    
    if not extracted_epubs and all_extracted.exists():
        # Usar qualquer EPUB disponível para teste
        test_epub = all_extracted.first()
        user = test_epub.uploaded_file.user
        print(f"Usando EPUB de outro usuário para teste: {user.username}")
        extracted_epubs = [test_epub]
    
    if not extracted_epubs:
        print("ERRO: Nenhum EPUB extraído encontrado!")
        return
    
    for epub in extracted_epubs:
        print(f"- ID: {epub.pk}, Título: {epub.title}")
        print(f"  Capítulos: {len(epub.chapters or [])}")
        if epub.chapters:
            print(f"  Primeiro capítulo: {epub.chapters[0].get('title', 'Sem título')[:50]}...")
    
    # Tentar traduzir o primeiro EPUB
    if extracted_epubs:
        test_epub = extracted_epubs[0] if isinstance(extracted_epubs, list) else extracted_epubs.first()
        print(f"\nTestando tradução do EPUB: {test_epub.title}")
    
    try:
        from uploads.tasks import translate_epub_sync
        print("Iniciando tradução síncrona...")
        
        # Traduzir apenas o primeiro capítulo para teste
        translation = translate_epub_sync(
            extracted_epub_id=test_epub.pk,
            source_lang='auto',
            target_lang='pt',
            chapter_index=0,  # Apenas primeiro capítulo
            user_id=user.pk
        )
        
        print(f"Tradução criada com sucesso! ID: {translation.pk}")
        print(f"Título traduzido: {translation.translated_title}")
        print(f"Capítulos traduzidos: {len(translation.translated_chapters or [])}")
        
    except Exception as e:
        print(f"ERRO na tradução: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_translation()