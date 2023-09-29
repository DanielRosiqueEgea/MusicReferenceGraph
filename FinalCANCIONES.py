import lyricsgenius as lg
import os
import json
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from unidecode import unidecode
import requests
from datetime import datetime
import re
from tqdm import tqdm

# Inicializa la barra de progreso


def clear_output():
    os.system('cls' if os.name == 'nt' else 'clear')

def extract_song_and_artist(text):
    # Patrones para reconocer las referencias
    patterns = [
        r"tema [“”\"]?(?P<cancion>[^“”\"]+)[“”\"]? de (?P<autor>[\w\s\.&]+)",
        r"canción [“”\"]?(?P<cancion>[^“”\"]+)[“”\"]? de (?P<autor>[\w\s\.&]+)",
        r"tema de (?P<autor>[\w\s\.&]+),? [“”\"]?(?P<cancion>[^“”\"]+)[“”\"]?",
        r"(?P<cancion>[^“”\"]+)\"? de (?P<autor>[\w\s\.&]+)",
        r"tema “(?P<cancion>[^“”\"]+)” de (?P<autor>[\w\s\.&]+)",
        r"tema [“”\"]?(?P<cancion>[^“”\"]+)[“”\"]? del? (?P<autor>[\w\s\.&]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return {"Referencia": True, "autor": match.group('autor').strip(), "titulo": match.group('cancion').strip()}
    
    return {"Referencia": False}

def cancion_a_tupla(cancion):
    return tuple(cancion.items())

api_key = input("Introduce tu Clave del API de Genius: ")
# genius = lg.Genius(api_key)
genius = lg.Genius(api_key, skip_non_songs=True, excluded_terms=["(Remix)", "(Live)"], remove_section_headers=True)
genius.verbose = False

client_id = input("Introduce tu id de cliente Spotify: ")
client_secret = input("Introduce tu clave secreta de cliente Spotify: ")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id,client_secret=client_secret))
   

canciones = [{"titulo":"Pura Droga Sin Cortar","autor":"Violadores del verso"},{"titulo":"#RapSinCorte L","autor":"Foyone"} ,{"titulo":"Blasfem Interludio","autor":"Ayax"},{"titulo":"Intro 97","autor":"Violadores del Verso"}]
# artistas = ["Foyone","Ayax"] #Reales
buscadas = set() #Aquí se almacenan las canciones buscadas
artistas_buscados  = set()
referencias = []

cola_canciones = [cancion_a_tupla(c) for c in canciones] # Convertir cada cancion en una tupla antes de agregarla a la cola
max_nodes = 5000
num_nodes = 0

progress_bar = tqdm(total=len(cola_canciones), desc="Procesando nodos", ncols=100)

while cola_canciones:  

    if progress_bar.total != num_nodes:
        progress_bar.total = num_nodes
        progress_bar.refresh()
    progress_bar.update(1)
    progress_bar.refresh()

    cancion_tupla = cola_canciones.pop(0)
    cancion = dict(cancion_tupla)
    # print("Canciones restantes: " + str(len(cola_canciones)))
    if cancion_tupla in buscadas:
        continue
    buscadas.add(cancion_tupla)
    
    try:
        song = genius.search_song(title=cancion["titulo"],artist=cancion["autor"])
    except requests.RequestException as e:
        print(f"Error al buscar la canción {cancion['titulo']} de {cancion['autor']}: {e}")
        continue

    if not song:
        continue
   

    request =genius.referents(song_id=song.id,per_page=50)
    annotations = [y for x in request['referents']
            for y in x['annotations']]
    
    for annotation in annotations:
        anotacion_limpia = re.sub(r'https?://www\.youtube\.com/watch\?v=\S+', '', annotation["body"]["plain"])
        anotacion_limpia = anotacion_limpia.replace('\n','')
        result = extract_song_and_artist(anotacion_limpia)

        if result["Referencia"] == True:
            
            autor_clean = unidecode(result["autor"])
            titulo_clean = unidecode(result["titulo"])
            result_limpio = {"titulo":titulo_clean,"autor":autor_clean}

            referencias.append({"origen":{"autor":song.artist,"titulo":song.title},"referencia": {"autor":autor_clean,"titulo":titulo_clean}})
            result_tupla = cancion_a_tupla(result_limpio)
            if (result_tupla not in cola_canciones) and (result_tupla not in buscadas) and num_nodes<max_nodes:
                cola_canciones.append(result_tupla)
                num_nodes=num_nodes+1

            if autor_clean in artistas_buscados or num_nodes>=max_nodes:
                continue

            try:
                new_songs = sp.search(q=autor_clean, limit=20)
                for idx, track in enumerate(new_songs['tracks']['items']):
                    new_song = {'titulo':track['name'],'autor':track['artists'][0]['name']}
                    new_song_tupla = cancion_a_tupla(new_song)
                    if (new_song_tupla not in cola_canciones) and (new_song_tupla not in buscadas) and num_nodes<max_nodes: 
                        cola_canciones.append(new_song_tupla)
                        num_nodes=num_nodes+1
                artistas_buscados.add(autor_clean)
            except:
                print("Excepcion al buscar canciones de: "+ autor_clean+" en spoty")
                continue
            
            # print(anotacion_limpia)
            
progress_bar.close()
now = datetime.now()
# Formatear a un string. Por ejemplo: '2023-09-26_14-30-59'
hora = now.strftime('%H_%M_%S')

with open('ReferenceGraphGenerator\\referencias'+hora+'.json', 'w') as f:
    json.dump(referencias, f)
