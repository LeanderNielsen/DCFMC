import mysql.connector
from rcon import RCON
import time

def get_secret(secret_name):
    # Læser secret fra /run/secrets/ — mountet af Docker Swarm
    try:
        with open(f'/run/secrets/{secret_name}', 'r') as f:
            return f.read().strip()
    except:
        return None

def sync_whitelist():
    # Hent passwords fra secrets
    mysql_password = get_secret('mysql_password')
    rcon_password = get_secret('rcon_password')

    # Hent alle spillere fra databasen
    db = mysql.connector.connect(
        host="minecraft_mariadb",
        user="mcuser",
        password=mysql_password,
        database="minecraft"
    )
    cursor = db.cursor()
    cursor.execute("SELECT username FROM whitelist")
    db_players = set(row[0] for row in cursor.fetchall())
    db.close()

    # Forbind til Minecraft via RCON
    rcon = RCON("minecraft_minecraft", rcon_password)
    rcon.connect()

    # Hent nuværende whitelist fra Minecraft
    response = rcon.command("whitelist list")
    mc_players = set()
    if ":" in response:
        names = response.split(":")[1].strip()
        if names:
            mc_players = set(n.strip() for n in names.split(","))

    # Tilføj spillere der er i DB men ikke i Minecraft
    for player in db_players - mc_players:
        rcon.command(f"whitelist add {player}")
        print(f"Tilføjet {player}")

    # Fjern spillere der er i Minecraft men ikke i DB
    for player in mc_players - db_players:
        rcon.command(f"whitelist remove {player}")
        print(f"Fjernet {player}")

    rcon.command("whitelist reload")
    rcon.disconnect()
    print("Whitelist synkroniseret!")

# Kør hvert minut
while True:
    try:
        sync_whitelist()
    except Exception as e:
        print(f"Fejl: {e}")
    time.sleep(60)
