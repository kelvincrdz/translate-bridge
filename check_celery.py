#!/usr/bin/env python
"""
Script para verificar se o ambiente Celery está funcionando corretamente
"""
import os
import sys
import django
from pathlib import Path

# Adicionar o diretório do projeto ao Python path
sys.path.append(str(Path(__file__).parent))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'epub_api.settings')
django.setup()

def test_redis_connection():
    """Testa a conexão com o Redis"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis está funcionando")
        return True
    except Exception as e:
        print(f"❌ Erro na conexão com Redis: {e}")
        return False

def test_celery_import():
    """Testa se o Celery pode ser importado"""
    try:
        from celery_app import app
        print("✅ Celery app importado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar Celery: {e}")
        return False

def test_task_import():
    """Testa se as tasks podem ser importadas"""
    try:
        from uploads.tasks import translate_epub_task
        print("✅ Tasks importadas com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar tasks: {e}")
        return False

def test_database_connection():
    """Testa a conexão com o banco de dados"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ Banco de dados funcionando")
        return True
    except Exception as e:
        print(f"❌ Erro na conexão com o banco: {e}")
        return False

def test_dependencies():
    """Testa se as dependências estão instaladas"""
    try:
        import deep_translator
        print("✅ deep_translator disponível")
    except ImportError:
        print("❌ deep_translator não encontrado")
        return False
    
    try:
        import bs4
        print("✅ BeautifulSoup4 disponível")
    except ImportError:
        print("❌ BeautifulSoup4 não encontrado")
        return False
    
    try:
        import ebooklib
        print("✅ ebooklib disponível")
    except ImportError:
        print("❌ ebooklib não encontrado")
        return False
    
    return True

def main():
    print("🔍 Verificando ambiente Celery/Redis...")
    print("=" * 50)
    
    all_good = True
    
    if not test_redis_connection():
        all_good = False
        print("\n💡 Para instalar Redis no Windows:")
        print("   1. Baixe Redis de: https://github.com/microsoftarchive/redis/releases")
        print("   2. Ou use Docker: docker run -d -p 6379:6379 redis:alpine")
        print("   3. Ou use o WSL: wsl --install e depois apt install redis-server")
    
    if not test_celery_import():
        all_good = False
    
    if not test_task_import():
        all_good = False
    
    if not test_database_connection():
        all_good = False
    
    if not test_dependencies():
        all_good = False
        print("\n💡 Para instalar dependências faltantes:")
        print("   pip install deep-translator beautifulsoup4 ebooklib")
    
    print("\n" + "=" * 50)
    if all_good:
        print("✅ Tudo funcionando! Você pode iniciar o Celery worker.")
        print("\n🚀 Para iniciar o worker:")
        print("   python -m celery -A epub_api worker --loglevel=info --pool=solo")
    else:
        print("❌ Problemas encontrados. Resolva-os antes de usar o Celery.")
    
    print("\n📋 Status dos serviços necessários:")
    print("   - Redis: Deve estar rodando na porta 6379")
    print("   - Django: Deve estar rodando na porta 8000")
    print("   - Celery Worker: Deve ser iniciado separadamente")

if __name__ == "__main__":
    main()
