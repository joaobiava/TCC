import pickle
import os
import time
import networkx as nx
import pandas as pd

TS_CUTOFF = int(pd.Timestamp('2017-10-18').timestamp() * 1000)
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

"""
=============================================================================================
Funcoes para SALVAR os GRAFOS
=============================================================================================
"""

def save_graph(G, path):
    with open(path, 'wb') as f:
        pickle.dump(G, f)
        print(f"Grafo salvo em {path}")

def load_graph(path):
    with open(path, 'rb') as f:
        G = pickle.load(f)
        print(f"Grafo carregado {G}")
        return G
    
def existing_file(files, path, function):
    #verifica se tem ou nao o grafo baixado e usa ou faz e salva
    if os.path.exists(path):
        G = load_graph(path)
    else:
        #execucao com liberacao de memoria
        inicio = time.perf_counter()
        G = function(files)
        fim = time.perf_counter()
        print(f"funcao de criar grafo demorou {fim - inicio} segundos")
        save_graph(G, path)

    return G

"""
=============================================================================================
Funcoes para CONSTRUIR os GRAFOS (se tiver algo de errado nelas, não vai fazer nada direito)
=============================================================================================
"""
def users_items(arquivos):
    G = nx.Graph()
    
    # carrega todos os arquivos e ordena por timestamp antes de inserir
    dfs = []
    for arquivo in arquivos:
        df = pd.read_csv(arquivo,
            usecols=['user_id', 'click_article_id', 'click_timestamp'])
        dfs.append(df)

    df_total = pd.concat(dfs, ignore_index=True)
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total.sort_values('click_timestamp', inplace=True)
    del dfs

    for row in df_total.itertuples():
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        ts   = row.click_timestamp

        G.add_node(user, subset=0, tipo=USER)
        G.add_node(item, subset=1, tipo=ITEM)
        G.add_edge(user, item, timestamp=ts)

    del df_total
    print(G)
    return G

def users_sessions_items(arquivos):
    G = nx.Graph()
    dfs = []

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start'])
        dfs.append(df)
        del df
    
    df_total = pd.concat(dfs, ignore_index=True)
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total.sort_values('click_timestamp', inplace=True)
    del dfs

    #itertuples é mais rápido que interrows
    for row in df_total.itertuples():
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        session = row.session_id + SESSION_OFFSET
        ts = row.click_timestamp
        ts_session_start = row.session_start

        G.add_node(user, tipo=USER)
        G.add_node(item, tipo=ITEM)
        G.add_node(session, tipo=SESSION)
        # coloca como atributo da aresta para que o timestamp seja atribuido a interação e nao ao item
        G.add_edge(user, session, timestamp=ts_session_start)
        G.add_edge(session, item, timestamp=ts)

    del df_total
    print(G)
    return G

def devices_users_sessions_items(arquivos):
    G = nx.Graph()
    dfs = []

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start', 'click_deviceGroup'])
        dfs.append(df)
        del df

    df_total = pd.concat(dfs, ignore_index=True)
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total.sort_values('click_timestamp', inplace=True)
    del dfs

    #itertuples é mais rápido que interrows
    for row in df_total.itertuples():
        device = row.click_deviceGroup + DEVICE_OFFSET
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        session = row.session_id + SESSION_OFFSET
        ts = row.click_timestamp
        ts_session_start = row.session_start

        G.add_node(device, tipo=DEVICE)
        G.add_node(user, tipo=USER)
        G.add_node(session, tipo=SESSION)
        G.add_node(item, tipo=ITEM)
        # coloca como atributo da aresta para que o timestamp seja atribuido a interação e nao ao item
        G.add_edge(session, device)
        G.add_edge(user, session, timestamp=ts_session_start)
        G.add_edge(session, item, timestamp=ts)

    del df_total
    print(G)
    return G

def devices_users_sessions_items_regions(arquivos):
    G = nx.Graph()
    dfs = []

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start', 'click_deviceGroup', 'click_region'])
        dfs.append(df)
        del df

    df_total = pd.concat(dfs, ignore_index=True)
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total.sort_values('click_timestamp', inplace=True)
    del dfs

    #itertuples é mais rápido que interrows
    for row in df_total.itertuples():
        device = row.click_deviceGroup + DEVICE_OFFSET
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        session = row.session_id + SESSION_OFFSET
        region = row.click_region + REGION_OFFSET
        ts = row.click_timestamp
        ts_session_start = row.session_start

        G.add_node(region, tipo=REGION)
        G.add_node(device, tipo=DEVICE)
        G.add_node(user, tipo=USER)
        G.add_node(session, tipo=SESSION)
        G.add_node(item, tipo=ITEM)
        # coloca como atributo da aresta para que o timestamp seja atribuido a interação e nao ao item
        G.add_edge(region, user)
        G.add_edge(session, device, timestamp=ts)
        G.add_edge(user, session, timestamp=ts_session_start)
        G.add_edge(session, item, timestamp=ts)

    del df_total
    print(G)
    return G