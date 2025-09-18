#!/usr/bin/env python3
"""
Script para testar requisições HTTP para a API de tradução
"""
import requests
import json

def test_http_request():
    """Testa requisição HTTP para tradução"""
    print("=== TESTE DE REQUISIÇÃO HTTP ===")
    
    # URL base do servidor
    base_url = "http://127.0.0.1:8000"
    
    # Dados para login (precisamos de token)
    login_data = {
        "username": "kelvo2",  # Usuário fornecido
        "password": "535846"   # Senha fornecida
    }
    
    # Primeiro, fazer login para obter token
    print("1. Fazendo login...")
    login_response = requests.post(f"{base_url}/api/login/", json=login_data)
    print(f"Status do login: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"Erro no login: {login_response.text}")
        return
    
    login_result = login_response.json()
    token = login_result.get('access')
    if not token:
        print(f"Token não encontrado na resposta: {login_result}")
        return
    
    print(f"Token obtido: {token[:20]}...")
    
    # Headers com autorização
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Dados para tradução (ID do EPUB que sabemos que existe)
    epub_id = 14  # EPUB do usuário kelvo2: "A Promise on an Apple"
    translation_data = {
        "source_lang": "auto",
        "target_lang": "pt",
        "chapter": 0  # Traduzir apenas primeiro capítulo
    }
    
    print(f"2. Fazendo requisição de tradução para EPUB ID {epub_id}...")
    print(f"URL: {base_url}/api/translate/{epub_id}/")
    print(f"Dados: {translation_data}")
    
    # Fazer requisição de tradução
    translate_response = requests.post(
        f"{base_url}/api/translate/{epub_id}/",
        json=translation_data,
        headers=headers
    )
    
    print(f"Status da tradução: {translate_response.status_code}")
    print(f"Headers da resposta: {dict(translate_response.headers)}")
    
    if translate_response.status_code == 200 or translate_response.status_code == 201:
        result = translate_response.json()
        print(f"Tradução criada com sucesso!")
        print(f"ID da tradução: {result.get('id')}")
        print(f"Título traduzido: {result.get('translated_title')}")
    else:
        print(f"Erro na tradução: {translate_response.status_code}")
        print(f"Resposta: {translate_response.text}")

if __name__ == "__main__":
    test_http_request()