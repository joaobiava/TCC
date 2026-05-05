import networkx as nx
from networkx import Graph
import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import sys
import time
import pickle

def salvar_grafo(G, caminho):
    with open(caminho, 'wb') as f:
        pickle.dump(G, f)
        print(f"Grafo salvo em {caminho}")

def carregar_grafo(caminho):
    with open(caminho, 'rb') as f:
        G = pickle.load(f)
        print(f"Grafo carregado {G}")
        return G

""" 
grafo bipartido (users + items)
faz de um jeito mais fofoinho liberando a memoria do csv, nao deixando carregar tudo de uma vez
+ otimizcao de memoria utilizando dtype, q permite diminuir o tamanho da memoria padrao que o pandas utiliza
"""
def users_items_intertuples(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id'], dtype={'user_id': 'uint64', 'click_article_id': 'uint64'})

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
            # tem q fazer assim pra nao duplicar dados nessa bomba
            user = f"u_{row[1]}"
            item = f"i_{row[2]}"
            G.add_node(user, subset=0, tipo="user")
            G.add_node(item, subset=1, tipo="item")
            G.add_edge(user, item)

        del df
    print(G)
    return G
   # deu certo e com a quantidade certas de nos totais

def users_items_sessions_devices_regions_intertuples(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        df = pd.read_csv(arquivo, usecols=['user_id', 'session_id', 'click_article_id', 'click_deviceGroup', 'click_region'], 
                         dtype={'user_id': 'uint64', 'click_article_id': 'uint64', 'session_id': 'uint64', 'click_deviceGroup': 'uint8', 'click_region': 'uint8'})

        #itertuples é mais rápido que interrows
        # essa bomba deu erro pq funciona de acordo com o csv, e nao a ordem escolhida ali em cima T-T
        for row in df.itertuples():
            users = f"u_{row[1]}"
            sessions = f"s_{row[2]}"
            items = f"i_{row[3]}"
            devices = f"d_{row[4]}"
            regions = f"r_{row[5]}"
            
            G.add_node(users, subset=0, tipo="user")
            G.add_node(sessions, subset=1, tipo="session")
            G.add_node(items, subset=2, tipo="item")
            G.add_node(devices, subset=3, tipo="device")
            G.add_node(regions, subset=4, tipo="region")

            G.add_edge(users, sessions)
            G.add_edge(sessions, items)
            G.add_edge(sessions, devices)
            G.add_edge(users, regions)

        del df

    print(G)
    return G
   # aparentemente deu certo


def recomendar_com_rwr(G: Graph, user_id, top_k, nao_alpha=0.2):
    if user_id not in G:
        print(f"Usuário {user_id} não encontrado no grafo.")
        return []

    # so o user alvo recebe peso 1
    personalization_target_user = {node: 0 for node in G.nodes()}
    personalization_target_user[user_id] = 1

    # RWR
    scores = nx.pagerank(G, alpha=1 - nao_alpha, personalization=personalization_target_user, max_iter=200)

    target_user_neighbors = list(G.neighbors(user_id))
    is_session = any(G.nodes[v].get('tipo') == 'session' for v in target_user_neighbors)

    # itens que o user ja clicou
    clicked = set()
    if is_session:
        sessions = [v for v in target_user_neighbors if G.nodes[v].get('tipo') == 'session']
        for s in sessions:
            for neighbors in G.neighbors(s):
                if G.nodes[neighbors].get('tipo') == 'item':
                    clicked.add(neighbors)
    else:
        for neighbors in G.neighbors(user_id):
            if G.nodes[neighbors].get('tipo') == 'item':
                clicked.add(neighbors)

    # Filtra itens q o usuario ainda n viu
    recommendations = []
    for node, score in scores.items():
        if node not in clicked and G.nodes[node].get('tipo') == 'item':
            recommendations.append((node, score))

    # ordena itens e retorna os top-k
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:top_k]


if __name__ == "__main__":
    caminho_grafo_simples = '/home/jaba/Documentos/TCC/grafo_simples'
    caminho_grafo_completo = '/home/jaba/Documentos/TCC/grafo_completo'
    pasta = '/home/jaba/Documentos/TCC/clicks'
    arquivos = glob.glob(os.path.join(pasta, "*.csv"))

    # funfou essa parte de carregar o grafo
    # if os.path.exists(caminho_grafo_simples):
    #     G = carregar_grafo(caminho_grafo_simples)
    # else:
    #     #execucao com liberacao de memoria
    #     inicio = time.perf_counter()
    #     G = users_items_intertuples(arquivos)
    #     fim = time.perf_counter()
    #     print(f"funcao users_items_intertuples demorou {fim - inicio} segundos")
    #     salvar_grafo(G, caminho_grafo_simples)

    # #executa rwr no grafo mais simples (users + items)
    # inicio = time.perf_counter()
    # recomendacoes = recomendar_com_rwr(G, user_id="u_0", top_k=10)
    # print(f"Recomendações para usuário 0:")
    # for artigo, score in recomendacoes:
    #     print(f"\tArtigo {artigo} — score: {score}")
    # fim = time.perf_counter()
    # print(f"funcao rwr demorou {fim - inicio} segundos")

    # sys.exit(0)

    #execucao liberando memoria (campos escolhidos pro grafo final)
    if os.path.exists(caminho_grafo_completo):
        G = carregar_grafo(caminho_grafo_completo)
    else:
        #execucao com liberacao de memoria
        inicio = time.perf_counter()
        G = users_items_sessions_devices_regions_intertuples(arquivos)
        fim = time.perf_counter()
        print(f"funcao users_items_sessions_localizations_devices_intertuples demorou {fim - inicio} segundos")
        salvar_grafo(G, caminho_grafo_completo)
        
    # executa rwr no grafo mais complexo
    inicio = time.perf_counter()
    recommendations = recomendar_com_rwr(G, user_id="u_0", top_k=20)
    print(f"Recomendações para usuário u_0:")
    for artigo, score in recommendations:
        print(f"\tArtigo {artigo} — score: {score}")
    fim = time.perf_counter()
    print(f"funcao rwr no grafo grande demorou {fim - inicio} segundos")

    #tempo entre as duas funccoes quase igual, porem da segunda tem liberacao de memoria do df
    # importante lembrar que nao esta sendo usada uma biblioteca muito especifica de tempo para o benchmark
