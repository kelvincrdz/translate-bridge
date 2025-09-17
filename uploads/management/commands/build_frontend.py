import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Build the React frontend and prepare it for Django static files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-install',
            action='store_true',
            help='Skip npm install step',
        )

    def handle(self, *args, **options):
        frontend_dir = os.path.join(settings.BASE_DIR, 'frontend')
        
        if not os.path.exists(frontend_dir):
            self.stdout.write(
                self.style.ERROR('Frontend directory not found at: %s' % frontend_dir)
            )
            return

        # Change to frontend directory
        original_dir = os.getcwd()
        os.chdir(frontend_dir)

        try:
            # Install dependencies if not skipped
            if not options['skip_install']:
                self.stdout.write('Installing frontend dependencies...')
                result = subprocess.run(['npm', 'install'], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    self.stdout.write(
                        self.style.ERROR('Failed to install dependencies: %s' % result.stderr)
                    )
                    return
                self.stdout.write(self.style.SUCCESS('Dependencies installed successfully'))

            # Build the frontend
            self.stdout.write('Building frontend...')
            result = subprocess.run(['npm', 'run', 'build'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                self.stdout.write(
                    self.style.ERROR('Frontend build failed: %s' % result.stderr)
                )
                return

            self.stdout.write(self.style.SUCCESS('Frontend built successfully'))
            
            # Collect static files
            self.stdout.write('Collecting static files...')
            from django.core.management import call_command
            call_command('collectstatic', '--noinput')
            
            self.stdout.write(
                self.style.SUCCESS('Frontend integration completed successfully!')
            )

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR('npm not found. Please install Node.js and npm.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('An error occurred: %s' % str(e))
            )
        finally:
            # Return to original directory
            os.chdir(original_dir)
