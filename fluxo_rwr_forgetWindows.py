import networkx as nx
from networkx import Graph
import pandas as pd
import glob
import os
import sys
import time
import logging
from models_and_save_graphs import (existing_file, users_items, users_sessions_items, 
                                    devices_users_sessions_items, devices_users_sessions_items_regions)
import math
import bisect

# variaveis 'tipo' montadas no grafo
USER = 0
ITEM = 1
SESSION = 2
REGION = 3
DEVICE = 4
USER_OFFSET = 1_000_000_000
ITEM_OFFSET = 2_000_000_000
SESSION_OFFSET = 3_000_000_000
REGION_OFFSET = 4_000_000_000
DEVICE_OFFSET = 5_000_000_000

#deixei umas config global aq, mais facil
USER_ID = USER_OFFSET + 1709
TOP_KS = [5, 10, 15, 20]
MS_DAY = 1000 * 60 * 60 * 24  # 1 dia em timestamp
TIME_WINDOW = MS_DAY * 2 # 2 dias para fazer atualizacoes
BETAS = [0.1, 0.15, 0.2, 0.25, 0.3]
TS_CUTOFF = int(pd.Timestamp('2017-10-18').timestamp() * 1000)

"""
=============================================================================================
FUNCAO DE CRIAR SUBGRAFO PELO TIMESTAMP
=============================================================================================
"""
def build_subGraph(G, edges_by_time, timestamps_only, current_time):
    lower_limit = current_time - TIME_WINDOW

    left = bisect.bisect_left(timestamps_only, lower_limit)

    right = bisect.bisect_right(timestamps_only, current_time)

    selectedEdges = [(u, v) for _, u, v in edges_by_time[left:right]]

    return G.edge_subgraph(selectedEdges)

"""
=============================================================================================
FUNCAO DAR ATUALIZAR ITENS CLICADOS
=============================================================================================
"""
def update_clicked(G: Graph, clicked):
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
    #         if G.nodes[neighbors].get('tipo') == 'item':
    #             clicked.add(neighbors)


    for neighbor in G.neighbors(USER_ID):
        if ITEM_OFFSET <= neighbor < SESSION_OFFSET:
            clicked.add(neighbor)
        elif SESSION_OFFSET <= neighbor < REGION_OFFSET:
            for candidate in G.neighbors(neighbor):
                if ITEM_OFFSET <= candidate < SESSION_OFFSET:
                    clicked.add(candidate)

"""
=============================================================================================
FUNCAO RwR
=============================================================================================
"""
def recommend_with_rwr_timeWindow(G: Graph, clicked, top_k, beta):
    if(USER_ID not in G):
        print("user not found")
        return []

    personalization_target_user = {USER_ID: 1}

    # RWR
    scores = nx.pagerank(G, alpha=1 - beta, personalization=personalization_target_user)
    
    # Filtra itens q o usuario ainda n viu
    recommendations = []
    for node, score in scores.items():
        if node not in clicked and G.nodes[node].get('tipo') == ITEM:
            recommendations.append((node, score))

    # ordena itens e retorna os top-k
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:top_k]


"""
=============================================================================================
FUNCAO PRECISION + NGCG
=============================================================================================
"""
def precision_topK(recommended, relevants):
    if not recommended or not relevants:
        return 0
    recommended_items = set(item for item, _ in recommended)
    return len(recommended_items & relevants) / len(recommended_items)

def ndcg_topK(recommended, relevants):
    if not recommended or not relevants:
        return 0
    
    dcg = 0.0
    for i, (item, _) in enumerate(recommended):
        if item in relevants:
            dcg += 1 / math.log2(i + 2)  # log2(posição + 1), posição começa em 1

    # ideal DCG — todos os acertos no topo da lista
    ideal_hits = min(len(relevants), len(recommended))
    idcg = sum(1 / (i + 2) for i in range(ideal_hits))

    return dcg / idcg if idcg > 0 else 0.0

"""
=============================================================================================
EXECUTA TUDO AS FIRULA NA ORDEM CORRETA
=============================================================================================
"""
def create_time_index(G):
    edges_by_time = sorted(
        [
            (data["timestamp"], u, v)
            for u, v, data in G.edges(data=True)
            if "timestamp" in data
        ]
    )
    # criado para fazer uma busca posteriormente onde fica mais rapido
    timestamps_only = [
        ts for ts, _, _ in edges_by_time
    ]

    return edges_by_time, timestamps_only

def execute_time_window(G, ts_begin, ts_end, edges_by_time, timestamps_only, topK, beta):
    clicked = set()
    current_time = ts_begin + TIME_WINDOW

    precisions = []
    ndcgs = []
    
    # subgrafo criado aqui, pois entao posso igualar o future_subgraph, nao precisando calcular ele 2 vezes
    inicio = time.perf_counter()
    current_sub = build_subGraph(G, edges_by_time, timestamps_only, current_time)
    fim = time.perf_counter()
    print(f"demorou {fim - inicio} segundos para montar o subgrafo")

    iteracao = 0
    # se o tempo for maior que o do ultimo click do dataset ele para
    while current_time <= ts_end:
        print(f"\nITERACAO: {iteracao}")
        iteracao+=1

        timestamp_readable = pd.to_datetime(current_time, unit='ms')
        print(f"tempo atual: {timestamp_readable}")

        print(current_sub)
        if USER_ID not in current_sub:
            current_time += TIME_WINDOW
            current_sub = build_subGraph(G, edges_by_time, timestamps_only, current_time)
            continue

        inicio = time.perf_counter()
        future_sub = build_subGraph(G, edges_by_time, timestamps_only, current_time + TIME_WINDOW)
        fim = time.perf_counter()
        print(f"Demorou {fim - inicio} segundos para montar future_subgrafo")
        print(future_sub)

        future_clicked = set()
        if USER_ID in future_sub:
            update_clicked(future_sub, future_clicked)
        
        update_clicked(current_sub, clicked)
        print(clicked)

        relevants = future_clicked - clicked

        #executa rwr
        inicio = time.perf_counter()
        recommended = recommend_with_rwr_timeWindow(current_sub, clicked, topK, beta)
        fim = time.perf_counter()

        print(f"[{timestamp_readable}] Recomendações para {USER_ID}")
        for artigo, score in recommended:
            print(f"\tArtigo {artigo} --- score: {score}")
        print(f"funcao rwr demorou {fim - inicio} segundos")

        if relevants:
            precisions.append(precision_topK(recommended, relevants))
            ndcgs.append(ndcg_topK(recommended, relevants))

        # leve otmizacao pra nao precisar ficar fazendo o future sub muitas vezes
        current_sub = future_sub
        #pula pra proxima janela de tempo
        current_time += TIME_WINDOW  #de acordo com a janela de tempo

    return precisions, ndcgs

def execute_hiperparams(G, ts_begin, ts_end):
    results = []
    total_combinations = len(BETAS) * len(TOP_KS)
    current_combination = 0
    
    edges_by_time, timestamps_only = create_time_index(G)
    
    for beta in BETAS:
        for topK in TOP_KS:
            current_combination += 1
            log.info(f"[{current_combination}/{total_combinations}] beta={beta} | top_k={topK}")
            
            precisions, ndcgs = execute_time_window(G, ts_begin, ts_end, edges_by_time, timestamps_only, topK, beta)

            mean_precision = sum(precisions) / len(precisions) if precisions else 0
            mean_ndcg = sum(ndcgs) / len(ndcgs) if ndcgs else 0

            log.info(f"\tPrecision@{topK}: {mean_precision} | nDCG{topK}: {mean_ndcg}")
            results.append((beta, topK, mean_precision, mean_ndcg))

    results.sort(key=lambda x: x[3], reverse=True)
    log.info(f"\n{'='*60}")
    log.info("RANKING DE HIPERPARÂMETROS (por nDCG):")
    print(f"{'='*60}")
    log.info(f"{'beta':<8} {'top_k':<8} {'P@K':<10} {'nDCG@K'}")
    print(f"{'-'*50}")
    for beta, top_k, p, n in results:
        log.info(f"{beta:<8} {top_k:<8} {p:<10.4f} {n:.4f}")
    best = results[0]
    log.info(f"\nMelhor configuração: beta={best[0]}, top_k={best[1]}")
    log.info(f"  Precision@K={best[2]:.4f} | nDCG@K={best[3]:.4f}")
    return best

"""
=============================================================================================
FUNCAO MAIN (FAZ O CONTROLE DE TUDO)
=============================================================================================
"""
if __name__ == "__main__":
    path_simple_graph_timeWindow = '/home/jaba/Documentos/TCC/grafos/grafo_simples_timewindow'
    path_user_sessions_items_timeWindow = '/home/jaba/Documentos/TCC/grafos/grafo_users_sessions_items_timeWindow'
    path_user_sessions_devices_items_timeWindow = '/home/jaba/Documentos/TCC/grafos/grafo_users_sessions_devices_items_timeWindow'
    path_complete_graph_timeWindow = '/home/jaba/Documentos/TCC/grafos/grafo_completo_timeWindow'
    folder = '/home/jaba/Documentos/TCC/clicks'
    files = glob.glob(os.path.join(folder, "*.csv"))

    print("1 - grafo users + items")
    print("2 - grafo users + sessions + items")
    print("3 - grafo users + sessions + devices + items")
    print("4 - grafo regions + users + sessions + devices + items")
    choice = int(input("escolha qual grafo deseja funfar\n"))

    graph_name = {1: 'foget_users_items', 2: 'foget_users_sessions_items', 3: 'foget_devices_users_sessions_items', 4: 'foget_devices_users_sessions_regions_items'}[choice]

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s — %(message)s',
        handlers=[
            logging.FileHandler(f'/home/jaba/Documentos/TCC/resultados/log_{graph_name}.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    log = logging.getLogger()

    match choice:
        case 1:
            G = existing_file(files, path_simple_graph_timeWindow, users_items)
        case 2:
            G = existing_file(files, path_user_sessions_items_timeWindow, users_sessions_items)
        case 3:
            G = existing_file(files, path_user_sessions_devices_items_timeWindow, devices_users_sessions_items)
        case 4:
            G = existing_file(files, path_complete_graph_timeWindow, devices_users_sessions_items_regions)
        case _:
            print("escolheu errado tonhao")

    # esse jeito é melhor de leitura e mais rapido
    timestamps = sorted(nx.get_edge_attributes(G, "timestamp").values())
    ts_begin = min(timestamps)
    ts_end = max(timestamps)
    current_time = ts_begin + TIME_WINDOW # já comeca com uma janela de dados
    
    execute_hiperparams(G, ts_begin, ts_end)