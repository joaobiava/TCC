import igraph as ig
import pandas as pd
import glob
import os
import sys
import time
import logging
from model_iGraph import (existing_file, users_items, users_sessions_items, 
                                    devices_users_sessions_items, devices_users_sessions_items_regions, 
                                    USER, USER_OFFSET, ITEM, ITEM_OFFSET, SESSION, SESSION_OFFSET, 
                                    DEVICE, DEVICE_OFFSET, REGION, REGION_OFFSET, TS_CUTOFF)
import math
import bisect
import random

# Configurações globais
TOP_KS = 20
MS_DAY = 1000 * 60 * 60 * 24  # 1 dia em timestamp
TIME_WINDOW = MS_DAY * 2 # 2 dias para fazer atualizacoes
BETAS = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
NUM_PASSEIOS = 5000
tempoMaximo = 500

def build_subGraph(G: ig.Graph, edges_by_time, timestamps_only, current_time):
    lower_limit = current_time - TIME_WINDOW

    left = bisect.bisect_left(timestamps_only, lower_limit)
    right = bisect.bisect(timestamps_only, current_time)

    selected_edges_index = [edge_index for _, edge_index in edges_by_time[left:right]]

    return G.subgraph_edges(selected_edges_index, delete_vertices=False)

def update_clicked(G, clicked, user_idx):
    # No iGraph, navegamos usando índices internos diretamente
    for neighbor in G.neighbors(user_idx):
        tipo = G.vs[neighbor]['tipo']

        if tipo == ITEM:
            clicked.add(neighbor)
        elif tipo == SESSION:
            for candidate in G.neighbors(neighbor):
                if G.vs[candidate]['tipo'] == ITEM:
                    clicked.add(candidate)

def recommend_with_rwr(G, clicked, user_index, beta):
    if G.degree(user_index) == 0:
        return []
    
    # Dicionário para contabilizar as visitas a cada vértice
    contagem_visitas = {}

    inicio = time.perf_counter()
    for _ in range(NUM_PASSEIOS):
        no_atual = user_index

        while random.random() > beta:
            vizinhos = G.neighbors(no_atual)

            if not vizinhos:
                no_atual = user_index
                continue
            
            # Sorteia um vizinho aleatoriamente
            no_atual = random.choice(vizinhos)

            # CORREÇÃO: Garante que APENAS itens entram no dicionário
            if G.vs[no_atual]['tipo'] == ITEM:
                # Se não existir, inicia com 0 e soma 1. Se existir, soma 1.
                contagem_visitas[no_atual] = contagem_visitas.get(no_atual, 0) + 1

        tempoDecorrido = (time.perf_counter() - inicio) * 1000
        if tempoDecorrido > tempoMaximo:
            break

    recommendations = []
    
    # CORREÇÃO: Usa no_idx no lugar de no_atual
    for no_idx, visitas in contagem_visitas.items():
        if visitas > 0:
            if no_idx not in clicked:
                recommendations.append((no_idx, visitas))

    if not recommendations:
        return []

    # Ordena os itens mais visitados e retorna os top-k
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:TOP_KS]

"""
=============================================================================================
FUNCAO PRECISION + nDCG (Sem alterações na lógica matemática)
=============================================================================================
"""
def precision_topK(recommended, relevants):
    if not recommended or not relevants:
        return 0
    recommended_items = set(item for item, _ in recommended)
    return len(recommended_items & relevants) / len(relevants)

def ndcg_topK(recommended, relevants):
    if not recommended or not relevants:
        return 0
    
    dcg = 0.0
    for i, (item, _) in enumerate(recommended):
        if item in relevants:
            dcg += 1 / math.log2(i + 2)

    return dcg / len(relevants)

def execute_timeWindow(G, all_users, ts_begin, ts_end, edges_by_time, timestamps_only, beta):
    all_precisions = []
    all_ndcgs = []

    current_time = ts_begin + TIME_WINDOW

    clicked_per_user = {
        user_index: set()
        for user_index in all_users
    }

    current_sub = build_subGraph(G, edges_by_time, timestamps_only, current_time)

    while current_time <= ts_end:
        future_sub = build_subGraph(G, edges_by_time, timestamps_only, current_time + TIME_WINDOW)

        timestamp_readable = pd.to_datetime(current_time, unit='ms')
        log.info("="*60)
        log.info(f"JANELA: {timestamp_readable}")
        log.info("="*60)

        current_users = {u for u in all_users if current_sub.degree(u) > 0}
        future_users = {u for u in all_users if future_sub.degree(u) > 0}
        valid_users = current_users & future_users

        for user in current_users:
            clicked = clicked_per_user[user]
            update_clicked(current_sub, clicked, user)

        for user_index in valid_users:
            clicked = clicked_per_user[user_index]
            future_clicked = set()

            update_clicked(future_sub, future_clicked, user_index)

            relevants = future_clicked - clicked

            if not relevants:
                continue

            # inicio = time.perf_counter()
            recommended = recommend_with_rwr(current_sub, clicked, user_index, beta)
            # fim = time.perf_counter()

            # user_name = G.vs[user_index]['name']
            # print(f"[USER] {user_name} tempo decorrido do RwR: {fim-inicio}")

            p = precision_topK(recommended, relevants)
            n = ndcg_topK(recommended, relevants)

            # print(f"precision={p} | nDCG={n}")

            all_precisions.append(p)
            all_ndcgs.append(n)

        current_time += TIME_WINDOW
        current_sub = future_sub

        log.info("Interrompendo após a primeira janela para fins de teste.")
        break

    return all_precisions, all_ndcgs


"""
=============================================================================================
EXECUTA TUDO NA ORDEM CORRETA
=============================================================================================
"""
def create_time_index(G: ig.Graph):
    # Mapeamos o timestamp diretamente para o índice interno da aresta (.index)
    edges_by_time = []
    for edge in G.es:
        ts = edge['timestamp']
        if ts is not None:
            edges_by_time.append((ts, edge.index))
            
    edges_by_time.sort(key=lambda x: x[0])
    timestamps_only = [ts for ts, _ in edges_by_time]

    return edges_by_time, timestamps_only


def execute_hiperparams(G, ts_begin, ts_end, all_users):
    results = []
    
    # Gera o índice de tempo uma única vez (Perfeito!)
    edges_by_time, timestamps_only = create_time_index(G)
    
    for beta in BETAS:
        log.info(f"Iniciando simulação para beta={beta}")

        # Executa a janela de tempo. 
        precisions, ndcgs = execute_timeWindow(G, all_users, ts_begin, ts_end, edges_by_time, timestamps_only, beta)

        # Calcula a média direto das listas retornadas (Sem redundância)
        mean_precision = sum(precisions) / len(precisions) if precisions else 0
        mean_ndcg = sum(ndcgs) / len(ndcgs) if ndcgs else 0

        results.append((beta, TOP_KS, mean_precision, mean_ndcg))
        log.info(f"Resultado parcial: beta={beta} | P@K={mean_precision:.4f} | nDCG={mean_ndcg:.4f}")

    # Ordena o ranking final pelo nDCG (índice 3 do tuplo)
    results.sort(key=lambda x: x[3], reverse=True)
    
    # --- Print do Log e Ranking ---
    print("\n" + "="*60)
    log.info("RANKING DE HIPERPARÂMETROS (por nDCG):")
    print("="*60)
    log.info(f"{'beta':<8} {'top_k':<8} {'P@K':<10} {'nDCG@K'}")
    print(f"{'-'*50}")
    for beta, top_k, p, n in results:
        log.info(f"{beta:<8} {top_k:<8} {p:<10.4f} {n:.4f}")
        
    best = results[0]
    print(f"\n" + "="*60)
    log.info(f"Melhor configuração: beta={best[0]}, top_k={best[1]}")
    log.info(f"  Precision@K={best[2]:.4f} | nDCG@K={best[3]:.4f}")
    print("="*60)
    
    return best


"""
=============================================================================================
FUNCAO MAIN
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

    # Coleta de timestamps a partir da sequência de arestas do iGraph (.es)
    timestamps = sorted([ts for ts in G.es['timestamp'] if ts is not None])
    ts_begin = min(timestamps)
    ts_end = max(timestamps)

    # Coletamos a lista de índices internos dos usuários
    all_users = [
        v.index for v in G.vs
        if v['tipo'] == USER
    ]
    
    execute_hiperparams(G, ts_begin, ts_end, all_users)