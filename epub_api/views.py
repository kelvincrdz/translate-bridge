from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from uploads.models import UploadedFile, ExtractedEpub, ReadingProgress
import json
import re
from .forms import RegistrationForm

def register_view(request):
    """User registration view with AJAX and standard POST support."""
    if request.user.is_authenticated:
        return redirect('library')

    if request.method == 'POST':
        content_type = request.content_type or ''
        is_json = content_type.startswith('application/json')
        if is_json:
            try:
                raw_body = request.body.decode('utf-8') or '{}'
                data = json.loads(raw_body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({'success': False, 'message': 'JSON inválido'}, status=400)
            form = RegistrationForm(data)
        else:
            form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            if is_json:
                return JsonResponse({'success': True, 'redirect_url': '/library/'})
            return redirect('library')
        else:
            if is_json:
                return JsonResponse({
                    'success': False,
                    'message': 'Erro de validação',
                    'errors': form.errors
                }, status=400)
            # Para POST tradicional, re-renderiza template com erros
            return render(request, 'epub_app/register.html', {'form': form})
    else:
        form = RegistrationForm()

    return render(request, 'epub_app/register.html', {'form': form})

def login_view(request):
    """
    Login page view
    """
    if request.user.is_authenticated:
        return redirect('library')
    
    if request.method == 'POST':
        content_type = request.content_type or ''
        is_json = content_type.startswith('application/json')
        if is_json:
            try:
                raw_body = request.body.decode('utf-8') or '{}'
                data = json.loads(raw_body)
                username = data.get('username')
                password = data.get('password')
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({'success': False, 'message': 'Dados inválidos'}, status=400)
        else:
            username = request.POST.get('username')
            password = request.POST.get('password')
        
        if username and password:
            # Primeira tentativa: autenticar diretamente (username)
            user = authenticate(request, username=username, password=password)

            # Se falhou e parece um email ou simplesmente não autenticou, tentar localizar usuário por email
            if user is None:
                from django.contrib.auth import get_user_model
                UserModel = get_user_model()
                if '@' in username:
                    try:
                        user_obj = UserModel.objects.filter(email__iexact=username).first()
                        if user_obj:
                            user = authenticate(request, username=user_obj.username, password=password)
                    except Exception:
                        user = None
                else:
                    # Tentativa extra: caso usuário tenha digitado email sem @ (improvável) ignoramos
                    pass

            if user is not None:
                login(request, user)
                if is_json:
                    return JsonResponse({'success': True, 'redirect_url': '/library/'})
                return redirect('library')
            error_message = 'Credenciais inválidas'
            if is_json:
                return JsonResponse({'success': False, 'message': error_message, 'errors': {'username': [error_message]}}, status=400)
            messages.error(request, error_message)
        else:
            error_message = 'Por favor, preencha todos os campos'
            if is_json:
                return JsonResponse({'success': False, 'message': error_message}, status=400)
            messages.error(request, error_message)
    
    return render(request, 'epub_app/login.html')

@login_required
def library_view(request):
    """
    Library page view - shows user's books
    """
    # Get uploaded files and their extracted epub data
    uploaded_files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    
    books = []
    for uploaded_file in uploaded_files:
        try:
            extracted = ExtractedEpub.objects.get(uploaded_file=uploaded_file)
            progress = ReadingProgress.objects.filter(
                user=request.user, 
                extracted_epub=extracted
            ).first()
            
            # Create book-like object for template compatibility
            book_data = {
                'id': extracted.id,  # extracted epub id (reader)
                'extracted_id': extracted.id,
                'uploaded_file_id': uploaded_file.id,
                'title': extracted.title or uploaded_file.title or 'Título não disponível',
                'author': extracted.metadata.get('author', '') if extracted.metadata else '',
                'cover_image': extracted.cover_image,  # Use the cover image from extracted epub
                'progress': progress.progress_percentage if progress else 0,
                'current_chapter': progress.current_chapter if progress else 0,
                'translation_available': extracted.translations.exists(),
                'translation_progress': 0,  # Calculate based on available translations
                'chapters': extracted.chapters or [],
                'created_at': uploaded_file.uploaded_at,
            }
            books.append(book_data)
            
        except ExtractedEpub.DoesNotExist:
            # File uploaded but not yet extracted
            book_data = {
                'id': f'upload_{uploaded_file.id}',
                'uploaded_file_id': uploaded_file.id,
                'title': uploaded_file.title or 'Processando...',
                'author': '',
                'cover_image': None,
                'progress': 0,
                'current_chapter': 0,
                'translation_available': False,
                'translation_progress': 0,
                'chapters': [],
                'created_at': uploaded_file.uploaded_at,
            }
            books.append(book_data)
    
    context = {
        'books': books,
    }
    
    return render(request, 'epub_app/library.html', context)

@login_required
def reader_view(request, book_id):
    """
    Book reader view
    """
    try:
        extracted_epub = get_object_or_404(ExtractedEpub, id=book_id)
        
        # Check if user has access (through uploaded file)
        if extracted_epub.uploaded_file.user != request.user:
            return redirect('library')
            
    except (ExtractedEpub.DoesNotExist, ValueError):
        return redirect('library')
    
    # Get current chapter from query parameter
    current_chapter = int(request.GET.get('chapter', 0))
    
    # Get chapters from extracted epub
    chapters = extracted_epub.chapters or []
    
    # Ensure chapter is within bounds
    if current_chapter < 0:
        current_chapter = 0
    elif current_chapter >= len(chapters):
        current_chapter = len(chapters) - 1 if chapters else 0
    
    def fix_image_urls(content, file_id):
        """Fix image URLs in HTML content to point to the correct media paths"""
        if not content:
            return content
        
        # Pattern to match img tags with src attributes
        img_pattern = r'<img([^>]*?)src=[\'"](.*?)[\'"]([^>]*?)>'
        
        def replace_img_src(match):
            before_src = match.group(1)
            src_value = match.group(2)
            after_src = match.group(3)
            
            # Skip if already absolute URL or data URL
            if src_value.startswith(('http://', 'https://', 'data:', '/media/')):
                return match.group(0)
            
            # Extract just the filename from the src path
            # Handle cases like "images/00001.jpeg" or "../images/00001.jpeg"
            filename = src_value.split('/')[-1]
            
            # Construct the correct media URL
            new_src = f'/media/epub_images/{file_id}/{filename}'
            
            return f'<img{before_src}src="{new_src}"{after_src}>'
        
        return re.sub(img_pattern, replace_img_src, content)
    
    # Get current chapter data and fix image URLs
    current_chapter_data = chapters[current_chapter] if chapters else {
        'title': 'Capítulo 1', 
        'content': 'Conteúdo não disponível.'
    }
    
    # Fix image URLs in the current chapter content
    if current_chapter_data.get('content'):
        current_chapter_data['content'] = fix_image_urls(
            current_chapter_data['content'], 
            extracted_epub.uploaded_file.pk
        )
    
    # Create book-like object for template
    book_data = {
        'id': extracted_epub.pk,
        'title': extracted_epub.title or 'Título não disponível',
        'author': extracted_epub.metadata.get('author', '') if extracted_epub.metadata else '',
        'chapters': chapters,
        'translation_available': True,  # Simplified for now
        'progress': 0,  # Will implement progress tracking
    }
    
    context = {
        'book': book_data,
        'current_chapter': current_chapter,
        'current_chapter_data': current_chapter_data,
    }
    
    return render(request, 'epub_app/reader.html', context)

def logout_view(request):
    """
    Logout view
    """
    logout(request)
    return redirect('login')

def frontend_view(request):
    """
    Redirect to library if user is authenticated, otherwise to login
    """
    if request.user.is_authenticated:
        return redirect('library')
    else:
        return redirect('login')

# API Views for AJAX functionality

@csrf_exempt
@require_http_methods(["POST"])
def api_theme_view(request):
    """
    API endpoint to save user theme preference
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'light')
        
        # Save theme to session for now (can be moved to user profile later)
        request.session['theme'] = theme
        
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid data'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_save_progress_view(request):
    """
    API endpoint to save reading progress
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        chapter_index = data.get('chapter_index', 0)
        progress = data.get('progress', 0)
        
        extracted_epub = get_object_or_404(ExtractedEpub, id=book_id)
        
        # Check user access
        if extracted_epub.uploaded_file.user != request.user:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        # Update or create reading progress
        progress_obj, created = ReadingProgress.objects.get_or_create(
            user=request.user,
            extracted_epub=extracted_epub,
            defaults={
                'current_chapter': chapter_index,
                'progress_percentage': progress
            }
        )
        
        if not created:
            progress_obj.current_chapter = chapter_index
            progress_obj.progress_percentage = progress
            progress_obj.save()
        
        return JsonResponse({'success': True})
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

# Legacy view for backwards compatibility
def old_frontend_view(request):
    """
    Legacy frontend view - now redirects to new interface
    """
    return HttpResponse(
        """
        <html>
        <head><title>Tradutor EPUB - Atualizado</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5;">
            <div style="max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h1 style="color: #333;">🎉 Frontend Atualizado!</h1>
                <p style="color: #666; font-size: 16px;">O frontend foi migrado para Django templates com design atualizado baseado no Font_figma.</p>
                
                <div style="background: #d4edda; padding: 20px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="margin-top: 0; color: #155724;">✅ Novo Frontend Ativo</h3>
                    <p style="color: #155724;">O sistema agora usa templates Django nativos com:</p>
                    <ul style="color: #155724;">
                        <li>Design baseado no Font_figma</li>
                        <li>Tailwind CSS para estilização</li>
                        <li>JavaScript vanilla para interatividade</li>
                        <li>Integração completa com Django</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="/" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                        🚀 Acessar Nova Interface
                    </a>
                </div>

                <div style="background: #f8f9fa; padding: 20px; border-radius: 4px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">📋 Funcionalidades Disponíveis</h3>
                    <ul>
                        <li>Sistema de login integrado</li>
                        <li>Biblioteca de livros com upload</li>
                        <li>Leitor de EPUB com configurações</li>
                        <li>Sistema de temas (claro/escuro)</li>
                        <li>Tradução de livros e capítulos</li>
                        <li>Download de livros</li>
                    </ul>
                </div>
                        <ul>
                            <li><a href="/admin/">Django Admin</a></li>
                            <li><a href="/swagger/">API Swagger</a></li>
                            <li><a href="/api/">API Endpoints</a></li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """,
            status=503
        )
    
    # Read the built index.html
    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Replace relative paths with Django static URLs
    html_content = html_content.replace('="/assets/', f'="{static("frontend/assets/")}')
    html_content = html_content.replace("='/assets/", f"='{static('frontend/assets/')}")
    html_content = html_content.replace('href="/vite.svg"', f'href="{static("frontend/vite.svg")}"')
    
    return HttpResponse(html_content)
