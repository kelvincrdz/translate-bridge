#!/usr/bin/env python3
"""
Script para listar EPUBs disponíveis do usuário
"""
import requests
import json

def list_user_books():
    """Lista livros disponíveis do usuário"""
    print("=== LISTANDO LIVROS DO USUÁRIO ===")
    
    # URL base do servidor
    base_url = "http://127.0.0.1:8000"
    
    # Dados para login
    login_data = {
        "username": "kelvo2",
        "password": "535846"
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
    
    # Listar livros disponíveis
    print("2. Listando livros...")
    books_response = requests.get(f"{base_url}/api/books/", headers=headers)
    print(f"Status da listagem: {books_response.status_code}")
    
    if books_response.status_code == 200:
        response_data = books_response.json()
        print(f"Resposta completa: {response_data}")
        
        # Extrair a lista de livros
        books = response_data.get('results', [])
        print(f"Livros encontrados: {len(books)}")
        for book in books:
            print(f"  ID: {book.get('id')}, Título: {book.get('title')}")
        return books
    else:
        print(f"Erro na listagem: {books_response.text}")
        return []

if __name__ == "__main__":
    list_user_books()