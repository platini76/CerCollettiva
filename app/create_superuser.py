import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cercollettiva.settings.local')
django.setup()

from users.models import CustomUser

# Crea superuser
if not CustomUser.objects.filter(username='admin').exists():
    user = CustomUser.objects.create_superuser(
        username='admin',
        email='admin@cercollettiva.local',
        password='CerAdmin2024!',
        first_name='Admin',
        last_name='CER',
        legal_type='BUSINESS',
        legal_name='CerCollettiva Admin',
        vat_number='12345678901',
        pec='admin@pec.cercollettiva.local',
        profit_type='NON_PROFIT',
        privacy_accepted=True
    )
    print('Superuser creato con successo')
else:
    print('Superuser già esistente')