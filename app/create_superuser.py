import os
import sys
import django
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurazione Django
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cercollettiva.settings.local')
    django.setup()
except Exception as e:
    logger.error(f"Errore durante l'inizializzazione di Django: {e}")
    sys.exit(1)

# Import dei modelli
try:
    from users.models import CustomUser
except ImportError as e:
    logger.error(f"Errore durante l'importazione dei modelli: {e}")
    sys.exit(1)

def main():
    # Verifica se l'utente admin esiste già
    try:
        admin_exists = CustomUser.objects.filter(username='admin').exists()
        
        if not admin_exists:
            # Crea superuser
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
            logger.info('Superuser creato con successo')
        else:
            logger.info('Superuser già esistente')
            
    except Exception as e:
        logger.error(f"Errore durante la creazione del superuser: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()