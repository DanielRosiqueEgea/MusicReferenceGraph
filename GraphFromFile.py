import lyricsgenius as lg
import networkx as nx
import json
from pyvis.network import Network
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from datetime import datetime
from tqdm import tqdm

client_id = input("Introduce tu id de cliente Spotify: ")
client_secret = input("Introduce tu clave secreta de cliente Spotify: ")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id,
                                                           client_secret=client_secret))

folder_name = 'ReferenceGraphGenerator'



# try:
#     new_songs = sp.search(q="Foyone", limit=50)
#     for idx, track in enumerate(new_songs['tracks']['items']):
#         new_song = {'titulo':track['name'],'autor':track['artists'][0]['name']}
#         print(new_song)
# except:
#     print("Excepcion al buscar canciones de: foyone en spoty")
    

# Lista todos los archivos en el directorio
files_in_directory = os.listdir(folder_name)

# Filtra aquellos que comienzan con "referencias" y terminan con ".json"
filtered_files = [file for file in files_in_directory if file.startswith("referencias") and file.endswith(".json")]

referencias =[]
for file in filtered_files:
    with open(os.path.join(folder_name,file), 'r') as f:
        referencias.extend(json.load(f))

print("REFERENCIAS CARGADAS")
artistas = []
buscados = {}

def is_valid_reference(referencia):
    # Verifica si cualquier campo tiene más de 50 caracteres
    for key in referencia:
        for inner_key in referencia[key]:
            if len(referencia[key][inner_key]) > 50:
                return False
    return True

referencias = [ref for ref in referencias if is_valid_reference(ref)]

print("referencias limpias")

progress_bar = tqdm(total=len(referencias), desc="Procesando referencias", ncols=100)

G = nx.DiGraph()
for referencia in referencias:

    progress_bar.update(1)
    progress_bar.refresh()

    vertice = []
    titulo_origen = referencia['origen']['titulo']
    for clave, valor in referencia.items():
        nombre_autor = valor['autor']
        titulo = valor['titulo']
    
        if nombre_autor not in buscados:
            lista_autores = sp.search(q='artist:' + nombre_autor,type='artist')
            # print(autor)
            if len(lista_autores['artists']['items'])<=0:
                try:
                    lista_canciones = sp.search(q='song: '+titulo)
                except:
                    # print(f"Error al buscar la canción {titulo} de {nombre_autor}")
                    continue
                if len(lista_canciones['tracks']['items'])<=0:
                    continue

                autor = lista_canciones['tracks']['items'][0]['artists'][0]['name']
            else:
                autor= lista_autores['artists']['items'][0]['name']
        else:
            autor = buscados[nombre_autor]
       
       
        buscados[nombre_autor] = autor
        if autor not in artistas:
            artistas.append(autor)
        # print("Artista Encontrado= "+autor.name)
        G.add_node(autor)
        vertice.append(autor)
    if len(vertice) == 2:
        G.add_edge(vertice[0],vertice[1],title = titulo_origen)
        # print("Vertice creado= "+ vertice[0]+ " => "+ vertice[1])


progress_bar.close()
nt = Network(notebook=True)

nt.from_nx(G)

# Ajusta los tamaños de los nodos basados en el grado (número de conexiones)
degrees = dict(G.degree())
nt.set_options("""
var options = {
  "nodes": {
    "scaling": {
      "label": {
        "enabled": true,
        "min": 10,
        "max": 30
      }
    }
  }
}
""")

for node in nt.nodes:
    node["value"] = degrees[node["id"]]
    node["title"] = f"{node['id']} ({degrees[node['id']]})"  # Para mostrar el número de conexiones al pasar el mouse.

for edge in nt.edges:
    edge_data = G.get_edge_data(edge['from'], edge['to'])
    if 'title' in edge_data:
        edge['title'] = edge_data['title']

now = datetime.now()
# Formatear a un string. Por ejemplo: '2023-09-26_14-30-59'
hora = now.strftime('%H_%M_%S')
nt.show('ReferenceGraphGenerator\\graph'+hora+'.html')