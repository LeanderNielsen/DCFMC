Leander har været her >_< !!! 
MINECRAFT SERVER — DOCKER SWARM SETUP

Et containeriseret Minecraft Java Edition server med DMZ arkitektur, Nginx
reverse proxy, MariaDB whitelist database og automatisk synkronisering via RCON.'

KRAV
- Windows Server med WSL 2 (Ubuntu)
- Docker Engine installeret i WSL
- Port 25565 forwardet på router til serverens lokale IP (10.2.0.38)
- netsh portproxy regel fra Windows til WSL IP (172.23.254.228)

MAPPESTRUKTUR
DCFMC/
    Dockerfile2.txt         Minecraft server image (Alpine + OpenJDK 25)
    Dockerfile.nginx        Nginx reverse proxy image (Alpine)
    Dockerfile.python       Python whitelist sync image (Alpine)
    Dockerfile.mariadb      MariaDB image
    compose.yaml            Docker Compose til lokal udvikling og build
    stack.yaml              Docker Swarm stack til produktion
    nginx.conf              Nginx TCP proxy konfiguration
    server.properties       Minecraft server konfiguration
    init.sql                Database tabel og rettigheder
    rcon.py                 Custom RCON implementation (Source RCON protokol)
    whitelist_sync.py       Whitelist synkroniseringsscript (kører hvert minut)
    README.txt              <- You are here >_<

ARKITEKTUR
Internet
    |
    v
EdgeRouter (port forward 25565 -> 10.2.0.38)
    |
    v
Windows Server / netsh portproxy (10.2.0.38 -> 172.23.254.228)
    |
    v
WSL 2 Ubuntu / Docker Swarm
    |
    v
DMZ netværk
    |
    v
Nginx container (TCP reverse proxy — eneste indgangspunkt fra internettet)
    |
    v
Internal netværk
    |
    + Minecraft container (spilserveren)
    + MariaDB container (whitelist database)
    + Python whitelist-sync container (synkroniserer DB med Minecraft)

NETVÆRK
DMZ (overlay):
    - Nginx og Minecraft er tilknyttet dette netværk
    - Eksponeret mod internettet via port 25565
    - Minecraft skal være her for at nå Mojang auth servere (Kan evt rykkes på internal ved at lave et lidt kompleks firewall setup)

Internal (overlay):
    - Alle 4 services er tilknyttet dette netværk
    - MariaDB og whitelist-sync er KUN her — aldrig eksponeret mod internettet
    - RCON kommunikation foregår her (port 25575)


SIKKERHED
- Nginx er det eneste indgangspunkt fra internettet
- Alle containers kører som non-root bruger (mcuser/nginx)
- MariaDB er kun tilgængelig på internal netværket 
- RCON er kun tilgængelig internt på port 25575
- Alpine base images bruges for at minimere angrebsfladen
- Trivy vulnerability scanning er kørt på alle images 
- Nginx DDoS begrænsning — maks 3 samtidige forbindelser per IP



FØRSTE GANG OPSÆTNING

1. Opret mappe og kopiér alle filer til serveren
   mkdir /mnt/c/DCFMC

    
2. Opret netsh portproxy regel i PowerShell (kør som administrator)
   netsh interface portproxy add v4tov4 listenaddress=10.2.0.38 listenport=25565 connectaddress=172.23.254.228 connectport=25565

3. Initialiser Docker Swarm i WSL
   sudo docker swarm init --advertise-addr 172.23.254.228

4. Byg og push images til Docker Hub (kun nødvendigt ved kodeændringer)
   sudo docker compose build
   sudo docker login
   sudo docker tag dcfmc-minecraft leanderfn/minecraft:latest
   sudo docker tag dcfmc-nginx leanderfn/nginx-mc:latest
   sudo docker tag dcfmc-whitelist-sync leanderfn/whitelist-sync:latest
   sudo docker tag dcfmc-mariadb leanderfn/mariadb-mc:latest
   sudo docker push leanderfn/minecraft:latest
   sudo docker push leanderfn/nginx-mc:latest
   sudo docker push leanderfn/whitelist-sync:latest
   sudo docker push leanderfn/mariadb-mc:latest
   sudo docker logout

5. Deploy stacken
   sudo docker stack deploy -c /mnt/c/DCFMC/stack.yaml minecraft

6. Tjek at alle 4 services kører
   sudo docker stack services minecraft

   Forventet output:
   minecraft_nginx          1/1
   minecraft_minecraft      1/1
   minecraft_mariadb        1/1
   minecraft_whitelist-sync 1/1



WHITELIST ADMINISTRATION
Tilføj spiller:
   sudo docker exec -it $(sudo docker ps | grep minecraft_mariadb | awk '{print $1}') mariadb -h 127.0.0.1 -u mcuser -pFievguys123! minecraft -e "INSERT INTO whitelist (username) VALUES ('SpillerNavn');"
 
Vis alle spillere:
   sudo docker exec -it $(sudo docker ps | grep minecraft_mariadb | awk '{print $1}') mariadb -h 127.0.0.1 -u mcuser -pFievguys123! minecraft -e "SELECT * FROM whitelist;"
 
Fjern spiller:
   sudo docker exec -it $(sudo docker ps | grep minecraft_mariadb | awk '{print $1}') mariadb -h 127.0.0.1 -u mcuser -pFievguys123! minecraft -e "DELETE FROM whitelist WHERE username='SpillerNavn';"
 
Ændringer synkroniseres automatisk til Minecraft inden for 60 sekunder.


DAGLIGE KOMMANDOER
Se status på alle services:
   sudo docker stack services minecraft
 
Se live logs fra Minecraft:
   sudo docker service logs -f minecraft_minecraft
 
Se live logs fra whitelist sync:
   sudo docker service logs -f minecraft_whitelist-sync
 
Genstart en service:
   sudo docker service update --force minecraft_minecraft
 
Stop hele stacken:
   sudo docker stack rm minecraft
 
Start stacken igen:
   sudo docker stack deploy -c /mnt/c/DCFMC/stack.yaml minecraft


OPDATERING AF KODE
Når du ændrer kode skal du rebuilde og pushe det ændrede image:
 
   sudo docker compose build minecraft        (kun Minecraft)
   sudo docker compose build whitelist-sync   (kun Python sync)
   sudo docker compose build nginx            (kun Nginx)
 
   sudo docker login
   sudo docker tag dcfmc-minecraft leanderfn/minecraft:latest
   sudo docker push leanderfn/minecraft:latest
   sudo docker logout
 
   sudo docker service update --image leanderfn/minecraft:latest --force minecraft_minecraft


SLET ALT OG START FORFRA
Stop stacken og slet alle volumes (ADVARSEL: sletter verden og database):
   sudo docker stack rm minecraft
   sleep 15
   sudo docker volume rm minecraft_minecraft-world minecraft_minecraft-logs minecraft_db_data
 
Start forfra:
   sudo docker stack deploy -c /mnt/c/DCFMC/stack.yaml minecraft


PORTE
25565   Minecraft (eksponeret mod internettet via Nginx)
25575   RCON (kun intern adgang)
3306    MariaDB (kun intern adgang)


TEST/BEVIS NGINX PROXY
Når serveren kører sluk for Nginx. Server kører stadig men du kan ikke nå den.
sudo docker service scale minecraft_nginx=0 

Tænd for Nginx igen og genskab tunnel til server
sudo docker service scale minecraft_nginx=1


OPSÆT SECRETS
echo "Skibidi123!" | sudo docker secret create mysql_root_password -
echo "Fievguys123!" | sudo docker secret create mysql_password -
echo "Fiveguys123!" | sudo docker secret create rcon_password -

HVIS PASSWORD ER FORGOR eksempel

# Slet det gamle secret
sudo docker secret rm mysql_password

# Opret et nyt med det nye password
echo "NytPassword123!" | sudo docker secret create mysql_password -

# Redeploy så containers bruger det nye secret
sudo docker stack deploy -c /mnt/c/DCFMC/stack.yaml minecraft
 

# PIPELINE
    Hver gang du pusher kode til main branchen bygger GitHub Actions automatisk
    alle 4 Docker images og pusher dem til Docker Hub. 

Flow:
    1. Du ændrer kode lokalt
    2. git add . && git commit -m "besked" && git push
    3. GitHub Actions starter automatisk
    4. Alle 4 images bygges og pushes til Docker Hub
    5. Du opdaterer stacken på serveren med:
       sudo docker service update --force minecraft_minecraft

Secrets der skal være sat på GitHub:
    DOCKER_USERNAME = leanderfn
    DOCKER_TOKEN    = Docker Hub access token (Read & Write)
    Sættes under: Settings -> Secrets and variables -> Actions

Se om pipelinen kørte korrekt:
    github.com/LeanderNielsen/DCFMC -> Actions fanen

Hvornår skal du manuelt opdatere stacken på serveren?
    Pipelinen pusher kun images til Docker Hub — den deployer ikke automatisk
    til serveren. Efter et vellykket build skal du køre:
    sudo docker stack deploy -c /mnt/c/DCFMC/stack.yaml minecraft
