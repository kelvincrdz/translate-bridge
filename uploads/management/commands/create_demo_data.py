# Management command to create demo data
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from uploads.models import UploadedFile, ExtractedEpub, ReadingProgress
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Create demo data for testing the application'
    
    def handle(self, *args, **options):
        # Create demo user
        demo_user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
            }
        )
        
        if created:
            demo_user.set_password('demo123')
            demo_user.save()
            self.stdout.write(
                self.style.SUCCESS('Created demo user: demo / demo123')
            )
        else:
            self.stdout.write('Demo user already exists')
        
        # Create demo books
        demo_books = [
            {
                'title': 'Dom Casmurro',
                'author': 'Machado de Assis',
                'metadata': {
                    'author': 'Machado de Assis',
                    'language': 'pt',
                    'publisher': 'Domínio Público',
                    'year': '1899'
                },
                'chapters': [
                    {
                        'title': 'Capítulo 1 - Do título',
                        'content': 'Uma noite destas, vindo da cidade para o Engenho Novo, encontrei no trem da Central um rapaz aqui do bairro, que eu conheço de vista e de chapéu...'
                    },
                    {
                        'title': 'Capítulo 2 - Do livro',
                        'content': 'Agora que expliquei o título, passo a escrever o livro. Antes disso, porém, digamos os motivos que me põem a pena na mão...'
                    },
                    {
                        'title': 'Capítulo 3 - A denúncia',
                        'content': 'Capitu era uma daquelas criaturas que trazem as ideias de longe, como as andorinhas trazem a primavera...'
                    }
                ]
            },
            {
                'title': 'O Cortiço',
                'author': 'Aluísio Azevedo',
                'metadata': {
                    'author': 'Aluísio Azevedo',
                    'language': 'pt',
                    'publisher': 'Domínio Público',
                    'year': '1890'
                },
                'chapters': [
                    {
                        'title': 'Capítulo 1',
                        'content': 'João Romão era o tipo do trabalhador moderno, o homem que, vindo de baixo, sobe à força de muito ralar, e vai se endurecendo...'
                    },
                    {
                        'title': 'Capítulo 2',
                        'content': 'Jerônimo era português, tinha vindo muito novo para o Brasil e aqui se estabelecera com uma vendinha de secos e molhados...'
                    }
                ]
            }
        ]
        
        for book_data in demo_books:
            # Create uploaded file
            uploaded_file, created = UploadedFile.objects.get_or_create(
                user=demo_user,
                title=book_data['title'],
                defaults={
                    'file': f"demo_{book_data['title'].lower().replace(' ', '_')}.epub"
                }
            )
            
            if created:
                self.stdout.write(f'Created uploaded file: {book_data["title"]}')
            
            # Create extracted epub
            extracted_epub, created = ExtractedEpub.objects.get_or_create(
                uploaded_file=uploaded_file,
                defaults={
                    'title': book_data['title'],
                    'metadata': book_data['metadata'],
                    'chapters': book_data['chapters']
                }
            )
            
            if created:
                self.stdout.write(f'Created extracted epub: {book_data["title"]}')
                
                # Create reading progress
                ReadingProgress.objects.get_or_create(
                    user=demo_user,
                    extracted_epub=extracted_epub,
                    defaults={
                        'current_chapter': 0,
                        'progress_percentage': 15.0
                    }
                )
        
        self.stdout.write(
            self.style.SUCCESS('Demo data created successfully!')
        )
        self.stdout.write(
            'You can now login with: demo@example.com / demo123'
        )