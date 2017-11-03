[OpenVDMv2_Logo]: http://www.oceandatarat.org/wp-content/uploads/2014/11/openVDM_LogoV2_1_long.png "Open Vessel Data Managment v2" 

![OpenVDMv2_Logo]
# Open Vessel Data Management v2.2

## Installation Guide
This is the installation guide for installing OpenVDM on the E/V Nautilus. It will be installed on the computer named NautilusFS which is running Debian 8.

### Operating System
Debian 8 was already installed at the time of OpenVDM's isntallation. We upgraded from Debian 7.8.

We are using the account `datafetcher` to write data to disk and to rysnc over ssh (with public key) into other computers.

Please run `sudo apt-get update` & `sudo apt-get upgrade` to get new versions pf packages etc.


### SSH Client/Server
SSH is used thoughout OpenVDM for providing secure communication between the Warehouse and collection systems workstations aboard the vessel.  SSH is also used for OpenVDM's ship-to-shore communications.

To install SSH open a terminal window and type:
```
sudo apt-get install ssh sshpass
```

### Rsync
Rsync is used thoughout OpenVDM for providing efficient data transfers to/from the Warehouse.

To install rsync open a terminal window and type:
```
sudo apt-get install rsync
```

### Samba
One of the ways OpenVDM communicates with data collection system is through Windows Shares configured on the collection system workstation.  Windows shares are also configured on the data warehouse to allow scientists and crew to easily access data stored on the Warehouse from their Windows or Mac Laptops.  Windows shares on a non-windows machine are made possible thanks to the Samba project.  

To install Samba open a terminal window and type:
```
sudo apt-get install samba smbclient cifs-utils
```

Unclear if needed for Nautilus installation:
```
Initialize the username creating during the OS installation for samba.  Change the username in the command below to the appropriate username for the current installation.  When prompted, set the password to the same password set of the user during the OS installation.

sudo smbpasswd -a survey
```


### MySQL Database Server
All of the commonly used variables, tranfer profiles, and user creditials for OpenVDM are stored in a SQL database.  This allows fast access to the stored information as well as a proven mechanism for multiple clients to change records without worry of write collisions.

To install MySQL open a terminal window and type:
```
sudo apt-get install mysql-server
```
When installing MySQL you will be prompted to provide a 'root' password.  This is different than the 'root' password for the operating system but just as important to remember. This password is saved in the data-docs password master spreadsheet.

### PHP7.1
The language used to write the OpenVDMv2 web-interface is PHP.

There is not an official package for debian 8 yet, so use [instructions from sury.org](https://packages.sury.org/php/README.txt) to add the repo for php 7.x packages.

To install PHP open a terminal window and type:
```
sudo apt-get install php7.1 php7.1-cli php7.1-mysql php7.1-dev php7.1-zip php7.1-curl
```

### Apache2 Web-server
The OpenVDM web-application is served by the Warehouse via the Apache2 Web-Server

To install Apache open a terminal window and type:
```
sudo apt-get install apache2 libapache2-mod-php7.1
```

Apache2 is installed by Xubuntu by default but an Apache2 module must be enabled.  To enable the additional module open a terminal window and type:
```
sudo a2enmod rewrite
```

After enabling the module the webserver must be restarted:
```
sudo service apache2 restart
```

### Gearman and Supervisor
Behind the OpenVDM web-application are several background processes that perform the various data transfers and other tasks.  Managing these background processes is a job broker and processes manager.

The job broker listens for requests to perform a specific task.  Once a request has arrived, the job broker farms the task out to the next available process that can perform that specific task.  OpenVDM uses Gearman as it's job broker.

Making sure the right type and number of worker processes are available to Gearman is the role of the process manager.  OpenVDM uses Supervisor as it's process manager.

#### Installing Gearman
To install Gearman open and terminal window and type the following commands:
```
sudo apt-get install gearman-job-server libgearman-dev python-gearman
```

Restart the Gearman Job Broker
```
sudo service gearman-job-server restart
```

### Gearman-UI
Gearman-UI is not directly part of OpenVDM or the Gearman job broker however it is extremely useful when troubleshooting problems with Gearman.

#### Installing composer

From a terminal window type:
```
cd /mnt/nautilusfs/share/software/openvdm
sudo apt-get install curl
curl -sS https://getcomposer.org/installer | php
sudo mv composer.phar /usr/local/bin/composer
```

#### Install bower
```
sudo apt-get install npm nodejs-legacy
sudo npm install -g bower
```

#### Install Gearman-UI
Download the code from GitHub
```
cd /mnt/nautilusfs/share/software/openvdm
sudo apt-get install git
git clone git://github.com/gaspaio/gearmanui.git /mnt/nautilusfs/share/software/openvdm/gearman-ui
```

Configure the site using the default configuration file
```
cd /mnt/nautilusfs/share/software/openvdm/gearman-ui
composer install --no-dev
bower install
cp config.yml.dist config.yml
```

Move the site to where Apache2 can access it.
```
cd /mnt/nautilusfs/share/software/openvdm
sudo mv gearman-ui /var/www/
sudo chown -R root:root /var/www/gearman-ui
```

Edit the default Apache2 VHost file.
```
sudo vim /etc/apache2/sites-available/000-default.conf
```

Copy text below into the Apache2 configuration file just above `</VirtualHost>`.
```
Alias /gearman-ui /var/www/gearman-ui/web
<Directory "/var/www/gearman-ui/web">
  <IfModule mod_rewrite.c>
    Options -MultiViews
    RewriteEngine On
    RewriteBase /gearman-ui/
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteRule ^ index.php [QSA,L]
  </IfModule>
</Directory>
```

Reload Apache2
```
sudo service apache2 reload
```

Verify the installation was successful by going to: <http://127.0.0.1/gearman-ui>

#### Installing Supervisor
To install Supervisor open and terminal window and type the following command:
```
sudo apt-get install supervisor
```

Add the following lines to `/etc/supervisor/supervisord.conf`:

```
[inet_http_server]
port = 9001
```

Editing this file will require root privledges.
```
sudo vim /etc/supervisor/supervisord.conf
```

Restart Supervisor:
```
sudo service supervisor restart
```

Enable Supervisor to start at boot
```
sudo systemctl enable supervisor
```

Verify the istallation was successful by going to <http://127.0.0.1:9001>.

### MapProxy
In order to add GIS capability to OpenVDMv2 without eccessive requests to the internet for baselayer tiles a map tile proxy needs to be installed.

Install the dependencies
```
sudo apt-get install python-pip python-imaging python-yaml libgeos-dev python-lxml libgdal-dev python-shapely
```

Install MapProxy
```
sudo pip install MapProxy
```

We encountered an error here with pip, so ran: `sudo apt-get purge -y python-pip` & `sudo easy_install pip` and then `sudo pip install MapProxy` worked.

Build the initial configuration
```
cd /mnt/nautilusfs/share/software/openvdm
mapproxy-util create -t base-config mapproxy
```

Copy the following into `/mnt/nautilusfs/share/software/openvdm/mapproxy/mapproxy.yaml`
```
# -------------------------------
# MapProxy configuration.
# -------------------------------

# Start the following services:
services:
  demo:
  tms:
    use_grid_names: false
    # origin for /tiles service
    origin: 'nw'
  kml:
    #use_grid_names: true
  wmts:
  wms:
    srs: ['EPSG:900913']
    image_formats: ['image/png']
    md:
      title: MapProxy WMS Proxy
      abstract: This is a minimal MapProxy installation.

#Make the following layers available
layers:
  - name: WorldOceanBase
    title: ESRI World Ocean Base
    sources: [esri_worldOceanBase_cache]

  - name: WorldOceanReference
    title: ESRI World Ocean Reference
    sources: [esri_worldOceanReference_cache]

  - name: GMRTBase
    title: GMRT Basemap
    sources: [gmrt_wms_cache]

caches:
  esri_worldOceanBase_cache:
    grids: [esri_online]
    sources: [esri_worldOceanBase]

  esri_worldOceanReference_cache:
    grids: [esri_online]
    sources: [esri_worldOceanReference]

  gmrt_wms_cache:
    grids: [gmrt]
    sources: [gmrt_wms]

sources:
  esri_worldOceanBase:
    type: tile
    url: http://server.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Base/MapServer/tile/%(z)s/%(y)s/%(x)s.png
    grid: esri_online

  esri_worldOceanReference:
    type: tile
    transparent: true
    url: http://server.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/%(z)s/%(y)s/%(x)s.png
    grid: esri_online

  gmrt_wms:
    type: wms
    grid: gmrt
    supported_srs: ['EPSG:4326', 'EPSG:3395', 'EPSG:3031', 'EPSG:3857','EPSG:900913']
    wms_opts:
      version: 1.0.0
    req:
      url: http://gmrt.marine-geo.org/cgi-bin/mapserv?map=/public/mgg/web/gmrt.marine-geo.org/htdocs/services/map/wms_merc.map&
      layers: topo
      transparent: false

grids:
  webmercator:
    base: GLOBAL_WEBMERCATOR

  esri_online:
     tile_size: [256, 256]
     srs: EPSG:900913
     origin: 'nw'
     num_levels: 11

  gmrt:
    tile_size: [256,256]
    srs: EPSG:900913
    origin: 'nw'

globals:
```

Move the installation to it's final location and set the user/group ownership
```
sudo cp -r /mnt/nautilusfs/share/software/openvdm/mapproxy /var/www/
sudo mkdir /var/www/mapproxy/cache_data
sudo chmod 777 /var/www/mapproxy/cache_data
sudo chown -R root:root /var/www/mapproxy
```

Prepare Apache2 to host the MapProxy installation
```
sudo apt-get install libapache2-mod-wsgi
```

Prepare the MapProxy installation for integration with the Apache2 web-server
```
cd /var/www/mapproxy
sudo mapproxy-util create -t wsgi-app -f mapproxy.yaml config.py
```

Edit the apache conf

```
sudo vim /etc/apache2/sites-available/000-default.conf
```

Add the following just above `</VirutalHost>` at the end of the file

```
WSGIScriptAlias /mapproxy /var/www/mapproxy/config.py

<Directory /var/www/mapproxy/>
  Order deny,allow
  Allow from all
</Directory>
```

Restart Apache2

```
sudo service apache2 restart
```

Verify the installation works by going to: <http://127.0.0.1/mapproxy/demo/>

### OpenVDMv2

#### Install the dependencies

#### Installing the python dependencies

```
sudo apt-get install python-requests python-yaml
```

#### Installing the gearman php module
The gearman extension team at pecl has not yet updated the gearman php module to work with php7.1.  Luckily the open-source community has come to the rescue.

Download the module
```
cd /mnt/nautilusfs/share/software/openvdm
git clone https://github.com/wcgallego/pecl-gearman.git /mnt/nautilusfs/share/software/openvdm/pecl-gearman
```

Build the module
```
cd /mnt/nautilusfs/share/software/openvdm/pecl-gearman
phpize
./configure
make
sudo make install
```

Create the file `/etc/php/7.1/mods-available/gearman.ini`
```
sudo vim /etc/php/7.1/mods-available/gearman.ini
```

Copy the following into `gearman.ini`
```
; configuration for php common module
; priority=20
extension=gearman.so
```

Enable the new module
```
sudo phpenmod gearman
```

Restart apache
```
sudo service apache2 restart
```

#### Installing the yaml php module
```
sudo apt-get install libyaml-dev
sudo pecl install yaml-2.0.0
```

Create the file `/etc/php/7.1/mods-available/yaml.ini`
```
sudo vim /etc/php/7.1/mods-available/yaml.ini
```

Copy the following into `gearman.ini`
```
; configuration for php common module
; priority=20
extension=yaml.so
```

Enable the new module
```
sudo phpenmod yaml
```

Restart apache
```
sudo service apache2 restart
```

#### Mapping OpenVDM Required Directories to Existing File System
In order for OpenVDMv2 to properly store data serveral directories must exist on NautilusFS.

 - **FTPRoot** (/mnt/nautilusfs)- This will become the document root for the ProFTP server. (FTP will NOT be enabled)
 - **CruiseData** (/mnt/nautilusfs/data)- This is the location where the Cruise Data directories will be located.  This directory needs to live within the **FTPRoot**
 - **PublicData** (/mnt/nautilusfs/share/dataguest/2017)- This is the location where the Public Data share will be located.  This directory needs to live within the **FTPRoot**
 - **VisitorInformation** (unclear as of now if this will be used)- This is the location where ship-specific information will be located.  This directory needs to live within the **FTPRoot**

The Location of the **FTPRoot** needs to be large enough to hold multiple cruises worth of data.  In typical installation of OpenVDMv2, the location of the **FTPRoot** is on dedicated hardware (internal RAID array).  In these cases the volume is mounted at boot by the OS to a specific location (i.e. `/vault`).  Instructions on mounting volumes at boot is beyond the scope of these installation procedures however.

For installation on the Nautilus, we have a file server NautilusFS with a external chassis connected by SAS cables. This is the main file system for all data on the ship. It resides at /mnt/nautilusfs - the datafetcher user will have write permissions to the /mnt/nautilusfs/data/current directory.

All directories and permissions already existed.

#### Download the OpenVDM Files from Github

From a terminal window type:
```
cd /mnt/nautilusfs/share/software/openvdm
git clone git://github.com/webbpinner/OpenVDMv2.git git-repo
```

#### Create OpenVDMv2 Database
To create a new database first connect to MySQL by typing:
```
mysql -h localhost -u root -p
```

Once connected to MySQL, create the database by typing:
```
CREATE DATABASE OpenVDMv2;
```

Now create a new MySQL user specifically for interacting with only the OpenVDM database.  In the example provided below the name of the user is `openvdmDBUser` and the password for that new user is `notArealPASSWORD`.
```
GRANT ALL PRIVILEGES ON OpenVDMv2.* To openvdmDBUser@localhost IDENTIFIED BY 'notArealPASSWORD';
```

It is not important what the name and password are for this new user however it is important to remember the designated username/password as it will be reference later in the installation.

To build the database schema and perform the initial import type:
```
USE OpenVDMv2;
source /mnt/nautilusfs/share/software/openvdm/git-repo/OpenVDMv2_db.sql;
```

Exit the MySQL console:
```
exit
```

#### Install the OpenVDM configuration files
```
sudo mkdir -p /usr/local/etc/openvdm
sudo cp /mnt/nautilusfs/share/software/openvdm/git-repo/usr/local/etc/openvdm/openvdm.yaml.dist /usr/local/etc/openvdm/openvdm.yaml
sudo cp /mnt/nautilusfs/share/software/openvdm/git-repo/usr/local/etc/openvdm/datadashboard.yaml.dist /usr/local/etc/openvdm/datadashboard.yaml
```

#### Modify the OpenVDM configuation file
```
sudo vim /usr/local/etc/openvdm/openvdm.yaml
```
Look for the following line:
```
siteRoot: "http://127.0.0.1/OpenVDMv2/"
```

If the web-application is NOT going to be accessed as `http://<server IP>/OpenVDMv2/` Change the URL to match the intended location i.e. `http://127.0.0.1/CustomURLJustForOpenVDM/`.   If URL is changed you will need to specified the exact same URL within the `Config.php` and `.htaccess` files.  Editing the `Config.php` and `.htaccess` files is covered below.

Copy the web-application code to a directory that can be accessed by Apache

```
sudo cp -r /mnt/nautilusfs/share/software/openvdm/git-repo/var/www/OpenVDMv2 /var/www/
sudo chown -R root:root /var/www/OpenVDMv2
```

Create the two required configuration files from the example files provided.
```
cd /var/www/OpenVDMv2
sudo cp ./.htaccess.dist ./.htaccess
sudo cp ./app/Core/Config.php.dist ./app/Core/Config.php
```

Modify the two configuration files.

Edit the `.htaccess` file:
```
sudo vim /var/www/OpenVDMv2/.htaccess
```

 - Set the `RewriteBase` to part of the URL after the hostname that will become the landing page for OpenVDMv2.  By default this is set to `OpenVDMv2` meaning that once active users will go to http://<hostname or IP>/OpenVDMv2/.  If the default URL was changed in the `openvdm.yaml` file, you will need to change the `RewriteBase` accordingly.  Be sure to include the trailing `/`.

Edit the `./app/Core/Config.php` file:
```
sudo vim /var/www/OpenVDMv2/app/Core/Config.php
```

 - Set the URL of the OpenVDMv2 installation.  If the default URL was changed in the `openvdm.yaml` file, you will need to change this line accordingly.  Be sure to include the trailing `/`.  Look for the following lines and change the IP address in the URL to the actual IP address or hostname of the warehouse:
```
//site address
define('DIR', '/OpenVDMv2/');
```

- Set the base directory containing the cruise data as defined earlier.
```
/*
 * Define path on webserver that contains cruise data
 */
define('CRUISEDATA_BASEDIR', '/mnt/nautilusfs/data');
```

 - Set the access creditials for the MySQL database.  Look for the following lines and modify them to fit the actual database name (`DB_NAME`), database username (`DB_USER`), and database user password (`DB_PASS`).
```
/*
 * Database name.
 */
define('DB_NAME', 'OpenVDMv2');

/*
 * Database username.
 */
define('DB_USER', 'openvdmDBUser');

/*
 * Database password.
 */
define('DB_PASS', 'notArealPASSWORD');
```

and change line 123 `date_default_timezone_set('Europe/London');` to `date_default_timezone_set('UTC');`

Edit the default Apache2 VHost file.
```
sudo vim /etc/apache2/sites-available/000-default.conf
```

Copy text below into the Apache2 configuration file just above `</VirtualHost>`.  If you changed the default URL for OpenVDM you will need to edit the Alias definition.  You will need to alter the directory locations to match the locations selected for the **CruiseData**, **PublicData** and **VisitorInformation** directories:
```
  Alias /OpenVDMv2 /var/www/OpenVDMv2
  <Directory "/var/www/OpenVDMv2">
    AllowOverride all
  </Directory>

  <IfModule mod_rewrite.c>
    RewriteEngine on
    RewriteRule ^/$ /OpenVDMv2/ [R]
  </IfModule>

  Alias /CruiseData/ /mnt/nautilusfs/data
  <Directory "/mnt/nautilusfs/data">
    AllowOverride None
    Options +Indexes -FollowSymLinks +MultiViews
    Order allow,deny
    Allow from all
    Require all granted
  </Directory>
  
  Alias /PublicData/ /mnt/nautilusfs/share/dataguest/current
  <Directory "/mnt/nautilusfs/share/dataguest/current">
    AllowOverride None
    Options +Indexes -FollowSymLinks +MultiViews
    Order allow,deny
    Allow from all
    Require all granted
  </Directory>

  #Alias /VisitorInformation/ /vault/FTPRoot/VisitorInformation/
  #<Directory "/vault/FTPRoot/VisitorInformation">
    #AllowOverride None
    #Options +Indexes -FollowSymLinks +MultiViews
    #Order allow,deny
    #Allow from all
    #Require all granted
  #</Directory>
```

`/etc/apache2/apache2.conf` by default blocks all access to the root file system. You must add the following to enable the abvove accesses:
```
stuff
```

Reload Apache2
```
sudo service apache2 reload
```

Additionally a log directory must be created for the OpenVDMv2 web-application
```
sudo mkdir /var/log/OpenVDM
```

#### Install OpenVDMv2 Processes
Copy the OpenVDMv2 processes to the `/usr/local/bin` folder
```
sudo cp -r /mnt/nautilusfs/share/software/openvdm/git-repo/usr/local/bin/* /usr/local/bin/
```

#### Install the Supervisor configuration files
```
sudo cp -r /mnt/nautilusfs/share/software/openvdm/git-repo/etc/supervisor/conf.d/* /etc/supervisor/conf.d/
sudo cp /etc/supervisor/conf.d/OVDM_runCollectionSystemTransfer.conf.dist /etc/supervisor/conf.d/OVDM_runCollectionSystemTransfer.conf
sudo cp /etc/supervisor/conf.d/OVDM_postCollectionSystemTransfer.conf.dist /etc/supervisor/conf.d/OVDM_postCollectionSystemTransfer.conf
```

Restart Supervisor
```
sudo service supervisor restart
```

Please note: supervisor < v3.2 does not always restart or stop cleanly on Debian. [Ref bug report](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=805920) Get around this by running `sudo service supervisor force-stop` and `sudo service supervisor force-stop` and then waiting a minute or two and running `sudo service supervisor start` 

#### Setup the Samba shares

-----------------
Unclear if Samba shares will be used at this point
-----------------

Edit the Samba configuration file located at: `/etc/samba/smb.conf`.

Within the authentication section search for the `obey pam restrictions` line as set it to:
```
obey pam restrictions = no
```

Add the following to end of the `smb.conf` file.  Set the user in `write list` to the username created during the OS installation.
```
[CruiseData]
  comment=Cruise Data, read-only access to guest
  path=/vault/FTPRoot/CruiseData
  browsable = yes
  public = yes
  guest ok = yes
  writable = yes
  write list = survey
  create mask = 0644
  directory mask = 0755
  veto files = /._*/.DS_Store/.Trashes*/
  delete veto files = yes

[VisitorInformation]
  comment=Visitor Information, read-only access to guest
  path=/vault/FTPRoot/VisitorInformation
  browsable = yes
  public = yes
  guest ok = yes
  writable = yes
  write list = survey
  create mask = 0644
  directory mask = 0755
  veto files = /._*/.DS_Store/.Trashes*/
  delete veto files = yes

[PublicData]
  comment=Public Data, read/write access to all
  path=/vault/FTPRoot/PublicData
  browseable = yes
  public = yes
  guest ok = yes
  writable = yes
  create mask = 0000
  directory mask = 0000
  veto files = /._*/.DS_Store/.Trashes*/
  delete veto files = yes
  force create mode = 666
  force directory mode = 777
```

Restart the Samba service
```
sudo systemctl restart samba-ad-dc.service
```

#### Accessing the application
At this point NautilusFS should have a working installation of OpenVDMv2 however the vessel operator will still need to configure data dashboard collection system transfers, cruise data transfers and the shoreside data warehouse.

To access the OpenVDM web-application goto: <http://nautilusfs.nautilus.oet.org/OpenVDMv2/>
The default username/passwd is admin/demo

#### Set the controlling username
Goto <http://nautilusfs.nautilus.oet.org/OpenVDMv2/config> and login

Goto <http://nautilusfs.nautilus.oet.org/OpenVDMv2/config/system> and scroll down to the bottom of the page.

In the "Data Warehouses" section Click "Edit" next to Shipboard Data Warehouse (SBDW)

Set the Server Username to match the user that was created for the data warehouse, which on the Nautilus is 'datafetcher'


