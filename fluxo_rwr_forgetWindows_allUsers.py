import networkx as nx
from networkx import Graph
import pandas as pd
import glob
import os
import sys
import time
import logging
from models_and_save_graphs import (existing_file, users_items, users_sessions_items, 
                                    devices_users_sessions_items, devices_users_sessions_items_regions, 
                                    USER, USER_OFFSET, ITEM, ITEM_OFFSET, SESSION, SESSION_OFFSET, 
                                    DEVICE, DEVICE_OFFSET, REGION, REGION_OFFSET, TS_CUTOFF)
import math
import bisect

#deixei umas config global aq, mais facil
TOP_KS = 20
MS_DAY = 1000 * 60 * 60 * 24  # 1 dia em timestamp
TIME_WINDOW = MS_DAY * 2 # 2 dias para fazer atualizacoes
BETAS = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]

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
def update_clicked(G: Graph, clicked, user_id):
    for neighbor in G.neighbors(user_id):
        tipo = G.nodes[neighbor].get('tipo')

        if tipo == ITEM:
            clicked.add(neighbor)
        elif tipo == SESSION:
            for candidate in G.neighbors(neighbor):
                if G.nodes[candidate].get('tipo') == ITEM:
                    clicked.add(candidate)

"""
=============================================================================================
FUNCAO RwR
=============================================================================================
"""
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
        if node not in clicked and G.nodes[node].get('tipo') == ITEM:
            recommendations.append((node, score))

    # ordena itens e retorna os top-k
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:top_k]


"""
=============================================================================================
FUNCAO PRECISION + nDCG
=============================================================================================
"""
def precision_topK(recommended, relevants):
    if not recommended or not relevants:
        return 0
    recommended_items = set(item for item, _ in recommended)
    return len(recommended_items & relevants) / TOP_KS #

def ndcg_topK(recommended, relevants):
    if not recommended or not relevants:
        return 0
    
    dcg = 0.0
    for i, (item, _) in enumerate(recommended):
        if item in relevants:
            dcg += 1 / math.log2(i + 2)  # log2(posição + 1), posição começa em 1

    # ideal DCG — todos os acertos no topo da lista
    #ideal_hits = min(len(relevants), len(recommended))
    #idcg = sum(1 / (i + 2) for i in range(ideal_hits))

    return dcg / len(relevants) #idcg if idcg > 0 else 0.0

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

def execute_time_window(G, users, ts_begin, ts_end, edges_by_time, timestamps_only, topK, beta):

    all_precisions = []
    all_ndcgs = []
    
    current_time = ts_begin + TIME_WINDOW

    clicked_per_user = {
        user_id: set()
        for user_id in users
    }

    while current_time <= ts_end:
        current_sub = build_subGraph(G, edges_by_time, timestamps_only, current_time)
        future_sub = build_subGraph(G, edges_by_time, timestamps_only, current_time + TIME_WINDOW)

        timestamp_readable = pd.to_datetime(current_time, unit='ms')
        # print("\n" + "="*60)
        # print(f"JANELA: {timestamp_readable}")
        # print("="*60)

        valid_users = {
            node
            for node in set(current_sub.nodes()) & set(future_sub.nodes())
            if G.nodes[node].get("tipo") == USER
        }

        for user_id in valid_users:
            clicked = clicked_per_user[user_id]
            future_clicked = set()

            update_clicked(current_sub, clicked, user_id)
            # print(f"itens clicados: {clicked}")

            # if user_id in future_sub:
            update_clicked(future_sub, future_clicked, user_id)
            # print(f"itens clicados no futuro: {future_clicked}")

            relevants = future_clicked - clicked
            # print(f"itens relevantes: {relevants}")

            if not relevants:
                continue

            # inicio = time.perf_counter()
            recommended = recommend_with_rwr_timeWindow(current_sub, clicked, user_id, topK, beta)
            # fim = time.perf_counter()
            # print(f"[USER] {user_id} tempo decorrido do RwR: {fim-inicio}")
            # print(f"top-{topK} recomendacoes:")
            # for artigo, score in recommended:
            #     print(
            #         f"\tItem {artigo} | "
            #         f"score={score:.6f}"
            #     )

            p = precision_topK(recommended, relevants)
            n = ndcg_topK(recommended, relevants)

            # print(
            #     f"Precision={p} | "
            #     f"nDCG={n}"
            # )

            all_precisions.append(p)
            all_ndcgs.append(n)

        current_time += TIME_WINDOW

    return all_precisions, all_ndcgs

def execute_hiperparams(G, ts_begin, ts_end, all_users):
    results = []
    
    edges_by_time, timestamps_only = create_time_index(G)
    
    for beta in BETAS:

        all_precisions = []
        all_ndcgs = []

        log.info(f"beta={beta}")

        precisions, ndcgs = execute_time_window(G, all_users, ts_begin, ts_end, edges_by_time, timestamps_only, TOP_KS, beta)

        all_precisions.extend(precisions)
        all_ndcgs.extend(ndcgs)

        mean_precision = (sum(all_precisions) / len(all_precisions) if all_precisions else 0)

        mean_ndcg = (sum(all_ndcgs) / len(all_ndcgs) if all_ndcgs else 0)

        results.append((beta, TOP_KS, mean_precision, mean_ndcg))

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

    graph_name = {1: 'foget_users_items_allUsers', 2: 'foget_users_sessions_items_allUsers', 3: 'foget_devices_users_sessions_items_allUsers', 4: 'foget_devices_users_sessions_regions_items_allUsers'}[choice]

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

    all_users = [
        node for node, data in G.nodes(data=True)
        if data.get("tipo") == USER
    ]
    
    execute_hiperparams(G, ts_begin, ts_end, all_users)