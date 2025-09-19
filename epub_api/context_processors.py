# Custom context processor for adding template variables
def app_context(request):
    """
    Add common variables to template context
    """
    context = {
        'app_name': 'Tradutor EPUB',
        'app_version': '2.0',
    }
    
    # Add theme preference
    if request.user.is_authenticated:
        context['user_theme'] = request.session.get('theme', 'light')
    
    return context