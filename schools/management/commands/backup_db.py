import os
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Backups the SQLite database'

    def handle(self, *args, **kwargs):
        # We assume SQLite based on settings
        db_path = settings.DATABASES['default']['NAME']
        
        if not os.path.exists(db_path):
            self.stderr.write(self.style.ERROR(f"Database not found at {db_path}"))
            return

        # Create backups directory if not exists
        backups_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. raw copy SQLite file
        backup_file = os.path.join(backups_dir, f'db_backup_{timestamp}.sqlite3')
        shutil.copy2(db_path, backup_file)
        
        # 2. dumpdata output to json
        dump_file = os.path.join(backups_dir, f'db_dump_{timestamp}.json')
        with open(dump_file, 'w') as f:
            call_command('dumpdata', format='json', indent=2, stdout=f)
            
        self.stdout.write(self.style.SUCCESS(f"Successfully backed up database to:\n1) {backup_file}\n2) {dump_file}"))
