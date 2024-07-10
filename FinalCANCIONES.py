import lyricsgenius as lg
import os
import json
import sys
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from unidecode import unidecode
import requests
from datetime import datetime
import re
from tqdm import tqdm
import pandas as pd


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

client_id_Spoty = None
client_secret_spoty = None
api_key_genius  = None

directorio = ".\ReferenceGraphGenerator\\references"


def load_api_keys():

# Intentar importar las claves desde el módulo Api_keys
    try:
        from Api_keys import client_id_Spoty, client_secret_spoty, api_key_genius
        print("Claves cargadas desde Api_keys")
        
    except ImportError:
        print("Módulo Api_keys no encontrado, comprobando argumentos del script")
        
        # Comprobar el número de argumentos del script
        total_args = len(sys.argv)
        print(sys.argv)
        
        if total_args == 4:
            # Cargar las claves desde los argumentos del script
            print("Cargando claves desde argumentos del script")
            api_key_genius = sys.argv[1]
            client_id_Spoty = sys.argv[2]
            client_secret_spoty = sys.argv[3]
            print("Claves cargadas desde argumentos del script")
        else:
            # Solicitar al usuario que ingrese las claves
            print("No se proporcionaron suficientes argumentos. Solicitando claves al usuario.")
            api_key_genius = input("Introduce tu Clave del API de Genius: ")
            client_id_Spoty = input("Introduce tu id de cliente Spotify: ")
            client_secret_spoty = input("Introduce tu clave secreta de cliente Spotify: ")
    return client_id_Spoty, client_secret_spoty, api_key_genius

client_id_Spoty, client_secret_spoty, api_key_genius = load_api_keys()
genius = lg.Genius(api_key_genius, skip_non_songs=True, excluded_terms=["(Remix)", "(Live)"], remove_section_headers=True)
genius.verbose = False

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id_Spoty,client_secret=client_secret_spoty))
   

canciones = [{"titulo":"Pura Droga Sin Cortar","autor":"Violadores del verso"},{"titulo":"#RapSinCorte L","autor":"Foyone"} ,{"titulo":"Blasfem Interludio","autor":"Ayax"},{"titulo":"Intro 97","autor":"Violadores del Verso"}]
# artistas = ["Foyone","Ayax"] #Reales
buscadas = set() #Aquí se almacenan las canciones buscadas
artistas_buscados  = set()
referencias = []

cola_canciones = [cancion_a_tupla(c) for c in canciones] # Convertir cada cancion en una tupla antes de agregarla a la cola
max_nodes = 1000
num_nodes = 0

progress_bar = tqdm(total=len(cola_canciones), desc="Procesando nodos", ncols=100)


# Inicializar un DataFrame vacío
database_as_df = pd.DataFrame(columns=['anotacion', 'autor_orig', 'titulo_orig', 'autor_ref', 'titulo_ref'])

# Iterar sobre los archivos en el directorio
for archivo in os.listdir(directorio):
    if archivo.endswith(".xlsx"):
        # Cargar el archivo Excel en un DataFrame y concatenarlo al DataFrame principal
        path_archivo = os.path.join(directorio, archivo)
        df_temp = pd.read_excel(path_archivo)
        database_as_df = pd.concat([database_as_df, df_temp], ignore_index=True)


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
   
    if song.title in database_as_df['titulo_orig'].values:
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

            referencias.append({"anotacion":anotacion_limpia,"autor_orig":song.artist,"titulo_orig":song.title,"autor_ref":autor_clean,"titulo_ref":titulo_clean})
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
        else:
            referencias.append({"anotacion":anotacion_limpia,"autor_orig":song.artist,"titulo_orig":song.title,"autor_ref":None,"titulo_ref":None})
            
progress_bar.close()
now = datetime.now()
# Formatear a un string. Por ejemplo: '2023-09-26_14-30-59'
hora = now.strftime('%H_%M_%S')

df = pd.DataFrame(referencias)
nombre_excel=f'{directorio}\\referencias_{hora}.xlsx'
df.to_excel(nombre_excel,index=False)

with open(f'{directorio}\\referencias'+hora+'.json', 'w') as f:
    json.dump(referencias, f)
