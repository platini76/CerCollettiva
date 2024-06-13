#!/bin/bash

# Aggiornamento del sistema
sudo apt update
sudo apt upgrade -y
sudo apt clean

# Installazione di Apache, PHP e MariaDB
sudo apt-get install apache2 -y
sudo wget -qO /etc/apt/trusted.gpg.d/php.gpg https://packages.sury.org/php/apt.gpg
echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/php.list
sudo apt update
sudo apt install -y php8.2 php8.2-common php8.2-cli php8.2-mbstring php8.2-xml php8.2-pdo php8.2-mysql php8.2-curl php8.2-zip unzip libapache2-mod-php8.2
sudo rm /var/www/html/index.html
sudo systemctl restart apache2

# Configurazione di Apache
sudo mkdir /var/www/html/cercollettiva/public
sudo nano /etc/apache2/sites-available/cercollettiva.conf  # Inserisci la configurazione qui
sudo a2ensite cercollettiva.conf
sudo a2dissite 000-default.conf
sudo a2enmod rewrite
sudo systemctl restart apache2

# Installazione e configurazione di MariaDB
sudo apt install mariadb-server
sudo mysql_secure_installation  # Segui le istruzioni per impostare la password di root

# Accesso a MariaDB e creazione del database (sostituisci le credenziali)
sudo mysql -u root -p <<MYSQL_SCRIPT
CREATE DATABASE cercollettiva_database;
CREATE USER 'cercollettiva'@'localhost' IDENTIFIED BY '*metti qua la tua password*';
GRANT ALL PRIVILEGES ON cercollettiva_database.* TO 'cercollettiva'@'localhost';
EXIT;
MYSQL_SCRIPT

# Installazione di Composer e Laravel
curl -sS https://getcomposer.org/installer | php
sudo mv composer.phar /usr/local/bin/composer
composer global require laravel/installer
export PATH="$PATH:$HOME/.config/composer/vendor/bin"
cd /var/www/html
sudo chown -R $USER:$USER /var/www/html
laravel new cercollettiva
sudo chown -R www-data:www-data /var/www/html/cercollettiva
sudo chmod -R 755 /var/www/html/cercollettiva/storage

# Configurazione di Laravel (.env)
cd /var/www/html/cercollettiva
sudo nano .env  # Inserisci le impostazioni corrette nel file .env
php artisan key:generate

# Installazione di Node.js, NPM e dipendenze frontend
sudo apt install nodejs npm
sudo npm install
sudo npm run build

# Installazione e configurazione di Mosquitto
sudo apt install mosquitto mosquitto-clients
sudo nano /etc/mosquitto/mosquitto.conf  # Inserisci la configurazione MQTT
sudo systemctl restart mosquitto
