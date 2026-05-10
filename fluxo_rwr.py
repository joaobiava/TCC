import networkx as nx
from networkx import Graph
import pandas as pd
import glob
import os
import sys
import time
import pickle

def save_graph(G, path):
    with open(path, 'wb') as f:
        pickle.dump(G, f)
        print(f"Grafo salvo em {path}")

def load_graph(path):
    with open(path, 'rb') as f:
        G = pickle.load(f)
        print(f"Grafo carregado {G}")
        return G

def users_items_itertuples(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp'], dtype={'user_id': 'uint64', 'click_article_id': 'uint64'})

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
            # tem q fazer assim pra nao duplicar dados nessa bomba
            user = f"u_{row.user_id}"
            item = f"i_{row.click_article_id}"
            ts = row.click_timestamp

            G.add_node(user, subset=0, tipo="user")
            G.add_node(item, subset=1, tipo="item")
            # coloca como atributo da aresta para que o timestamp seja atribuido a interação e nao ao item
            G.add_edge(user, item, timestamp=ts)

        del df
    print(G)
    return G

"""pelo o que eu vi, esse é o melhor jeito de se fazer pq ocupa menos espaco e eh mais rapido
tinha feito um jeito antes que criava um grafo novo, mas ficava mais demorado e tals"""
def build_subGraph(G: Graph, current_time, time_window):
    lower_limit = current_time - time_window


    selectedEdges = [(u, v) for u, v, data in G.edges(data=True)
                     if lower_limit <= data.get('timestamp', 0) <= current_time]
    
    sub_graph = G.edge_subgraph(selectedEdges).copy()

    return sub_graph

"""pelo o que eu vi, esse é o melhor jeito de se fazer pq ocupa menos espaco e eh mais rapido
o jeito comentado criava um grafo novo, o que demora mais tempo"""
def update_clicked(G, clicked, user_id, current_time):
    # pra agora isso aqui nao vai servir, só pra depois talvez
    # target_user_neighbors = list(G.neighbors(user_id))
    # is_session = any(G.nodes[v].get('tipo') == 'session' for v in target_user_neighbors)

    # if is_session:
    #     sessions = [v for v in target_user_neighbors if G.nodes[v].get('tipo') == 'session']
    #     for s in sessions:
    #         for neighbors in G.neighbors(s):
    #             if G.nodes[neighbors].get('tipo') == 'item':
    #                 clicked.add(neighbors)
    # else:
    #     for neighbors in G.neighbors(user_id):
    #         if G.nodes[neighbors].get('tipo') == 'item' and G.edges[neighbors].get('timestamp') <= current_time:
    #             clicked.add(neighbors)
    for neighbors in G.neighbors(user_id):  
            if G.nodes[neighbors].get('tipo') == 'item':
                clicked.add(neighbors)


def recommend_with_rwr_timeWindow(G: Graph, clicked, user_id, top_k, beta):
    if(user_id not in G):
        print("user not found")
        return []

    personalization_target_user = {user_id: 1}

    # RWR
    scores = nx.pagerank(G, alpha=1 - beta, personalization=personalization_target_user)
    
    # Filtra itens q o usuario ainda n viu
    recommendations = []
    for node, score in scores.items():
        if node not in clicked and G.nodes[node].get('tipo') == 'item':
            recommendations.append((node, score))

    # ordena itens e retorna os top-k
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:top_k]


if __name__ == "__main__":
    path_simple_graph_timeWindow = '/home/jaba/Documentos/TCC/grafo_simples_timewindow'
    path_complete_graph_timeWindow = '/home/jaba/Documentos/TCC/grafo_completo_timeWindow'
    folder = '/home/jaba/Documentos/TCC/clicks'
    files = glob.glob(os.path.join(folder, "*.csv"))

    #deixei umas config global aq, mais facil
    USER_ID = "u_0"
    TOP_K = 10
    MS_DAY = 1000 * 60 * 60 * 24  # 1 dia em timestamp
    time_window = MS_DAY # 24 horas para fazer atualizacoes
    BETA = 0.2
    clicked = set()

    #verifica se tem ou nao o grafo baixado e usa ou faz e salva
    if os.path.exists(path_simple_graph_timeWindow):
        G = load_graph(path_simple_graph_timeWindow)
    else:
        #execucao com liberacao de memoria
        inicio = time.perf_counter()
        G = users_items_itertuples(files)
        fim = time.perf_counter()
        print(f"funcao users_items_itertuples demorou {fim - inicio} segundos")
        save_graph(G, path_simple_graph_timeWindow)

    # esse jeito é melhor de leitura e mais rapido
    timestamps = sorted(nx.get_edge_attributes(G, "timestamp").values())
    
    ts_begin = min(timestamps)
    ts_end = max(timestamps)
    current_time = ts_begin + time_window # já comeca com uma janela de dados
    
    iteracao = 0
    # se o tempo for maior que o do ultimo click do dataset ele para
    while current_time <= ts_end:
        print(f"\nITERACAO: {iteracao}")
        iteracao+=1
        print(f"tempo atual: {pd.to_datetime(current_time, unit='ms')}")

        # constroi o subgrafo mesmo se o user-alvo nao estiver nele
        inicio = time.perf_counter()
        sub = build_subGraph(G, current_time, time_window)
        fim = time.perf_counter()
        print(f"Demorou {fim - inicio} segundos para montar o subgrafo")

        # se o user n tiver no subgrafo, da erro, caso queira alocar recomendacoes pra ele mesmo nao estando em sessao, obrigar a colcaor user no subgrafo
        if(USER_ID not in sub):
            current_time += time_window
            continue
        
        # tempo para dar atualizar os clicks (quase o mesmo tempo de montar o subgrafo (erra por milesimos))
        incio = time.perf_counter()
        update_clicked(sub, clicked, USER_ID, current_time)
        fim = time.perf_counter()
        print(f"demorou {fim - inicio} segundos para atualizar clicked")
        print(clicked)

        #executa rwr
        inicio = time.perf_counter()
        recomendacoes = recommend_with_rwr_timeWindow(sub, clicked, USER_ID, TOP_K, BETA)
        fim = time.perf_counter()

        timestamp_readable = pd.to_datetime(current_time, unit='ms')
        print(f"[{timestamp_readable}] Recomendações para {USER_ID}")
        for artigo, score in recomendacoes:
            print(f"\tArtigo {artigo} --- score: {score}")
        print(f"funcao rwr demorou {fim - inicio} segundos")

        #pula pra proxima janela de tempo
        current_time += time_window  #de acordo com a janela de tempo
