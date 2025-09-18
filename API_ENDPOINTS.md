# 📚 API Endpoints Documentation - Tradutor Fun

Este documento descreve todos os endpoints da API do sistema de tradução de EPUBs.

## 🔐 Autenticação

### POST `/register/`
**Descrição:** Registra um novo usuário no sistema.

**Parâmetros de entrada:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "password2": "string"
}
```

**Resposta de sucesso (201):**
```json
{
  "id": 1,
  "username": "user123",
  "email": "user@example.com"
}
```

**Erros possíveis:**
- `400` - Dados inválidos ou senhas não conferem

---

### POST `/login/`
**Descrição:** Autentica um usuário e retorna tokens JWT.

**Parâmetros de entrada:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Resposta de sucesso (200):**
```json
{
  "refresh": "jwt_refresh_token",
  "access": "jwt_access_token",
  "user": {
    "id": 1,
    "username": "user123",
    "email": "user@example.com"
  }
}
```

**Erros possíveis:**
- `401` - Credenciais inválidas

---

### GET `/user/`
**Descrição:** Retorna informações do usuário autenticado.

**Autenticação:** Bearer Token (obrigatório)

**Resposta de sucesso (200):**
```json
{
  "id": 1,
  "username": "user123",
  "email": "user@example.com"
}
```

---

### POST `/refresh/`
**Descrição:** Renova o token de acesso usando o refresh token.

**Parâmetros de entrada:**
```json
{
  "refresh": "jwt_refresh_token"
}
```

**Resposta de sucesso (200):**
```json
{
  "access": "new_jwt_access_token",
  "refresh": "same_or_new_refresh_token"
}
```

**Erros possíveis:**
- `401` - Refresh token inválido
- `400` - Refresh token não fornecido

---

## 🛠️ Utilitários

### GET `/languages/`
**Descrição:** Retorna lista de idiomas suportados para tradução.

**Resposta de sucesso (200):**
```json
{
  "languages": {
    "auto": "Detect Language",
    "en": "English",
    "pt": "Portuguese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ru": "Russian",
    "ar": "Arabic"
  }
}
```

---

### GET `/diagnostics/`
**Descrição:** Retorna estatísticas e diagnósticos do usuário.

**Autenticação:** Bearer Token (obrigatório)

**Resposta de sucesso (200):**
```json
{
  "user_stats": {
    "uploaded_files": 5,
    "extracted_epubs": 5,
    "translated_epubs": 3,
    "reading_progress": 2
  }
}
```

---

## 📁 Gerenciamento de Arquivos

### POST `/upload/`
**Descrição:** Faz upload de um arquivo EPUB.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de entrada (form-data):**
- `file`: Arquivo EPUB (máximo 50MB)
- `title`: Título do livro (opcional)

**Resposta de sucesso (201):**
```json
{
  "id": 1,
  "title": "Nome do Livro",
  "file": "/media/epubs/arquivo.epub",
  "uploaded_at": "2025-09-18T10:30:00Z",
  "user": 1
}
```

**Erros possíveis:**
- `400` - Arquivo não é EPUB válido, muito grande, ou ausente

---

### GET `/files/`
**Descrição:** Lista todos os arquivos EPUB do usuário.

**Autenticação:** Bearer Token (obrigatório)

**Resposta de sucesso (200):**
```json
[
  {
    "id": 1,
    "title": "Nome do Livro",
    "file": "/media/epubs/arquivo.epub",
    "uploaded_at": "2025-09-18T10:30:00Z",
    "user": 1
  }
]
```

---

### DELETE `/files/{pk}/delete/`
**Descrição:** Deleta um arquivo EPUB específico.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `pk`: ID do arquivo a ser deletado

**Resposta de sucesso (204):** Sem conteúdo

**Erros possíveis:**
- `404` - Arquivo não encontrado

---

### DELETE `/books/delete-all/`
**Descrição:** Deleta todos os livros do usuário.

**Autenticação:** Bearer Token (obrigatório)

**Resposta de sucesso (200):**
```json
{
  "message": "Livros removidos",
  "deleted": 5
}
```

---

## 📖 Processamento de EPUB

### GET `/extract/{pk}/`
**Descrição:** Extrai e processa o conteúdo de um EPUB.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `pk`: ID do arquivo EPUB

**Parâmetros de query (opcionais):**
- `chapter`: Índice do capítulo específico a extrair

**Resposta de sucesso (200):**
```json
{
  "id": 1,
  "title": "Nome do Livro",
  "metadata": {
    "title": "Nome do Livro",
    "author": "Autor"
  },
  "chapters": [
    {
      "title": "Capítulo 1",
      "content": "<p>Conteúdo HTML do capítulo...</p>"
    }
  ],
  "images": ["/media/epub_images/1/image1.jpg"],
  "cover_image": "/media/epub_images/1/cover.jpg"
}
```

**Erros possíveis:**
- `404` - Arquivo não encontrado
- `400` - Índice de capítulo inválido

---

### POST `/translate/{pk}/`
**Descrição:** Traduz um EPUB ou capítulo específico.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `pk`: ID do arquivo EPUB ou ExtractedEpub

**Parâmetros de entrada:**
```json
{
  "source_lang": "auto",
  "target_lang": "pt",
  "chapter": 0
}
```

**Resposta de sucesso (201):**
```json
{
  "id": 1,
  "source_lang": "en",
  "target_lang": "pt",
  "chapter_index": 0,
  "translated_title": "Título Traduzido",
  "translated_chapters": [
    {
      "title": "Capítulo 1 Traduzido",
      "content": "<p>Conteúdo traduzido...</p>"
    }
  ],
  "created_at": "2025-09-18T10:30:00Z"
}
```

**Erros possíveis:**
- `400` - Idioma inválido ou capítulo fora do range
- `500` - Erro na tradução

---

## 📚 Biblioteca e Leitura

### GET `/books/`
**Descrição:** Lista livros da biblioteca do usuário com progresso.

**Autenticação:** Bearer Token (obrigatório)

**Resposta de sucesso (200):**
```json
{
  "results": [
    {
      "id": 1,
      "uploaded_file_id": 1,
      "title": "Nome do Livro",
      "metadata": {"author": "Autor"},
      "chapter_count": 10,
      "cover_image": "/media/epub_images/1/cover.jpg",
      "progress": {
        "current_chapter": 3,
        "progress_percentage": 30.0
      }
    }
  ],
  "count": 1
}
```

---

### GET `/reader/{file_id}/`
**Descrição:** Carrega conteúdo do EPUB para leitura.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `file_id`: ID do arquivo EPUB

**Parâmetros de query (opcionais):**
- `source_lang`: Idioma de origem (padrão: "auto")
- `target_lang`: Idioma de destino (padrão: "pt")
- `chapter`: Capítulo específico

**Resposta de sucesso (200):**
```json
{
  "id": 1,
  "title": "Nome do Livro",
  "metadata": {"author": "Autor"},
  "chapters": [
    {
      "title": "Capítulo 1",
      "content": "<p>Conteúdo...</p>",
      "translated": false
    }
  ],
  "images": ["/media/epub_images/1/image1.jpg"],
  "translations": [],
  "progress": {
    "current_chapter": 0,
    "current_position": 0,
    "progress_percentage": 0.0
  }
}
```

---

### GET `/reader/{file_id}/images/{image_name}`
**Descrição:** Serve imagens do EPUB para o leitor.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `file_id`: ID do arquivo EPUB
- `image_name`: Nome da imagem

**Resposta de sucesso (200):** Arquivo de imagem (JPEG, PNG, etc.)

---

## 📊 Progresso de Leitura

### GET `/reading-progress/{extracted_epub_id}/`
**Descrição:** Obtém progresso de leitura de um livro.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `extracted_epub_id`: ID do EPUB extraído

**Resposta de sucesso (200):**
```json
{
  "current_chapter": 3,
  "current_position": 250,
  "progress_percentage": 30.5
}
```

---

### POST `/reading-progress/{extracted_epub_id}/`
**Descrição:** Atualiza progresso de leitura de um livro.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `extracted_epub_id`: ID do EPUB extraído

**Parâmetros de entrada:**
```json
{
  "current_chapter": 3,
  "current_position": 250,
  "progress_percentage": 30.5
}
```

**Resposta de sucesso (200):**
```json
{
  "current_chapter": 3,
  "current_position": 250,
  "progress_percentage": 30.5
}
```

---

## ⚙️ Preferências

### GET `/reader-preferences/`
**Descrição:** Obtém preferências do leitor.

**Autenticação:** Bearer Token (obrigatório)

**Resposta de sucesso (200):**
```json
{
  "font_size": 16,
  "font_family": "Arial",
  "theme": "light",
  "line_height": 1.5,
  "reading_speed": 250
}
```

---

### PUT/PATCH `/reader-preferences/`
**Descrição:** Atualiza preferências do leitor.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de entrada:**
```json
{
  "font_size": 18,
  "theme": "dark"
}
```

**Resposta de sucesso (200):**
```json
{
  "font_size": 18,
  "font_family": "Arial",
  "theme": "dark",
  "line_height": 1.5,
  "reading_speed": 250
}
```

---

## ⬇️ Downloads

### GET `/downloads/`
**Descrição:** Lista arquivos disponíveis para download.

**Autenticação:** Bearer Token (obrigatório)

**Resposta de sucesso (200):**
```json
[
  {
    "file": {
      "id": 1,
      "title": "Nome do Livro",
      "file": "/media/epubs/arquivo.epub"
    },
    "extracted": {
      "id": 1,
      "title": "Nome do Livro",
      "chapters": [...]
    },
    "translations": [
      {
        "id": 1,
        "source_lang": "en",
        "target_lang": "pt"
      }
    ]
  }
]
```

---

### GET `/download/original/{pk}/`
**Descrição:** Baixa arquivo EPUB original.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `pk`: ID do arquivo EPUB

**Resposta de sucesso (200):** Arquivo EPUB para download

---

### GET `/download/translation/{pk}/`
**Descrição:** Baixa EPUB com tradução aplicada.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `pk`: ID da tradução

**Resposta de sucesso (200):** Arquivo EPUB traduzido para download

---

### GET `/download/mixed/{pk}/`
**Descrição:** Baixa EPUB misto (original + traduções disponíveis).

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `pk`: ID do arquivo EPUB

**Parâmetros de query:**
- `target_lang`: Idioma de destino das traduções

**Resposta de sucesso (200):** Arquivo EPUB misto para download

---

## 🗑️ Exclusões

### DELETE `/translations/{pk}/delete/`
**Descrição:** Deleta uma tradução específica.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de URL:**
- `pk`: ID da tradução

**Resposta de sucesso (204):** Sem conteúdo

---

## 📥 Importação

### POST `/import-ao3/`
**Descrição:** Importa obra do Archive of Our Own (AO3).

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de entrada:**
```json
{
  "url": "https://archiveofourown.org/works/12345678"
}
```

**Resposta de sucesso (201):**
```json
{
  "uploaded_file_id": 1,
  "extracted_epub_id": 1,
  "title": "Título da Obra",
  "metadata_preview": {...},
  "already_imported": false,
  "debug_id": "unique_id"
}
```

**Erros possíveis:**
- `400` - URL inválida ou erro no fetch
- `413` - Obra muito grande
- `501` - Funcionalidade não implementada

---

## 📋 Logs e Auditoria

### GET `/audit-logs/`
**Descrição:** Lista logs de auditoria do usuário.

**Autenticação:** Bearer Token (obrigatório)

**Parâmetros de query (opcionais):**
- `action`: Filtrar por ação (login, upload, download, etc.)
- `resource_type`: Filtrar por tipo de recurso
- `date_from`: Data de início (YYYY-MM-DD)
- `date_to`: Data de fim (YYYY-MM-DD)
- `page`: Página (padrão: 1)
- `page_size`: Itens por página (padrão: 20)

**Resposta de sucesso (200):**
```json
{
  "logs": [
    {
      "id": 1,
      "action": "login",
      "description": "Login realizado com sucesso",
      "resource_type": null,
      "resource_id": null,
      "timestamp": "2025-09-18T10:30:00Z",
      "ip_address": "192.168.1.1",
      "metadata": {}
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

## 🔒 Autenticação e Permissões

### Autenticação Requerida
Todos os endpoints exceto `/register/`, `/login/`, `/refresh/` e `/languages/` requerem autenticação Bearer Token.

### Headers Necessários
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Códigos de Status Comuns
- `200` - Sucesso
- `201` - Criado com sucesso
- `204` - Sucesso sem conteúdo
- `400` - Dados inválidos
- `401` - Não autenticado
- `403` - Sem permissão
- `404` - Não encontrado
- `500` - Erro interno do servidor

---

## 📝 Notas Importantes

1. **Tamanho de Arquivo:** EPUBs limitados a 50MB
2. **Formatos Aceitos:** Apenas arquivos `.epub` válidos
3. **Rate Limiting:** Pode ser implementado em produção
4. **CORS:** Configurado para permitir origens específicas
5. **Logs:** Todas as ações importantes são registradas para auditoria