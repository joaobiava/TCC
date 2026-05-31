import pickle
import os
import time
import igraph as ig
import pandas as pd

TS_CUTOFF = int(pd.Timestamp('2017-10-17').timestamp() * 1000)
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
    G.write_pickle(path)
    print(f"Grafo salvo na memoria no caminho: {path}")

def load_graph(path):
    G = ig.Graph.Read_Pickle(path)
    print(f"Grafo carregado: {G.summary()}")
    return G
    
def existing_file(files, path, function):
    if os.path.exists(path):
        G = load_graph(path)
    else:
        inicio = time.perf_counter()
        G = function(files)
        fim = time.perf_counter()
        print(f"funcao de criar grafo demorou {fim - inicio} segundos")
        save_graph(G, path)

    return G

"""
=============================================================================================
Funcoes para CONSTRUIR os GRAFOS
=============================================================================================
"""
def users_items(arquivos):
    G = ig.Graph()
    
    dfs = []
    for arquivo in arquivos:
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp'])
        dfs.append(df)
        del df

    df_total = pd.concat(dfs, ignore_index=True)
    del dfs
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total = df_total.sort_values(by='click_timestamp').reset_index(drop=True)

    # Listas para acumular os dados e inseri-los em lote (MUITO mais rápido no iGraph)
    nos_dict = {}
    arestas = []
    timestamps = []

    for row in df_total.itertuples():
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        ts   = row.click_timestamp

        # No iGraph, controlamos a duplicidade antes de inserir ou usamos strings no 'name'
        if user not in nos_dict:
            nos_dict[user] = USER
        if item not in nos_dict:
            nos_dict[item] = ITEM
            
        arestas.append((user, item))
        timestamps.append(ts)

    # Inserindo em lote (Bulk insert) - Desempenho máximo
    # Passamos os IDs gigantes como string no atributo 'name' para o iGraph indexar automaticamente
    G.add_vertices([str(k) for k in nos_dict.keys()])
    G.vs['tipo'] = list(nos_dict.values())
    
    # Adiciona as arestas referenciando o 'name' (que definimos como string)
    G.add_edges([(str(u), str(i)) for u, i in arestas])
    G.es['timestamp'] = timestamps

    del df_total, nos_dict, arestas, timestamps
    print(G.summary())
    return G

def users_sessions_items(arquivos):
    G = ig.Graph()
    dfs = []

    for arquivo in arquivos:
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start'])
        dfs.append(df)
        del df
    
    df_total = pd.concat(dfs, ignore_index=True)
    del dfs
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total = df_total.sort_values(by='click_timestamp').reset_index(drop=True)

    nos_dict = {}
    arestas = []
    timestamps = []

    for row in df_total.itertuples():
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        session = row.session_id + SESSION_OFFSET
        ts = row.click_timestamp
        ts_session_start = row.session_start

        if user not in nos_dict: 
            nos_dict[user] = USER
        if item not in nos_dict: 
            nos_dict[item] = ITEM
        if session not in nos_dict: 
            nos_dict[session] = SESSION

        arestas.append((user, session))
        timestamps.append(ts_session_start)
        
        arestas.append((session, item))
        timestamps.append(ts)

    G.add_vertices([str(k) for k in nos_dict.keys()])
    G.vs['tipo'] = list(nos_dict.values())
    
    G.add_edges([(str(u), str(v)) for u, v in arestas])
    G.es['timestamp'] = timestamps

    del df_total, nos_dict, arestas, timestamps
    print(G.summary())
    return G

def regions_users_sessions_items(arquivos):
    G = ig.Graph()
    dfs = []

    for arquivo in arquivos:
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start', 'click_region'])
        dfs.append(df)
        del df

    df_total = pd.concat(dfs, ignore_index=True)
    del dfs
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total = df_total.sort_values(by='click_timestamp').reset_index(drop=True)

    nos_dict = {}
    arestas = []
    timestamps = []

    for row in df_total.itertuples():
        region = row.click_region + REGION_OFFSET
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        session = row.session_id + SESSION_OFFSET
        ts = row.click_timestamp
        ts_session_start = row.session_start

        if region not in nos_dict: nos_dict[region] = REGION
        if user not in nos_dict: nos_dict[user] = USER
        if session not in nos_dict: nos_dict[session] = SESSION
        if item not in nos_dict: nos_dict[item] = ITEM

        # Aresta session -> device (sem timestamp no seu original, usamos None ou 0)
        arestas.append((user, region))
        timestamps.append(None) 
        
        # Aresta user -> session
        arestas.append((user, session))
        timestamps.append(ts_session_start)
        
        # Aresta session -> item
        arestas.append((session, item))
        timestamps.append(ts)

    G.add_vertices([str(k) for k in nos_dict.keys()])
    G.vs['tipo'] = list(nos_dict.values())
    
    G.add_edges([(str(u), str(v)) for u, v in arestas])
    G.es['timestamp'] = timestamps

    del df_total, nos_dict, arestas, timestamps
    print(G.summary())
    return G

def devices_users_sessions_items_regions(arquivos):
    G = ig.Graph()
    dfs = []

    for arquivo in arquivos:
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start', 'click_deviceGroup', 'click_region'])
        dfs.append(df)
        del df

    df_total = pd.concat(dfs, ignore_index=True)
    del dfs
    df_total = df_total[df_total['click_timestamp'] < TS_CUTOFF]
    df_total = df_total.sort_values(by='click_timestamp').reset_index(drop=True)

    nos_dict = {}
    arestas = []
    timestamps = []

    for row in df_total.itertuples():
        device = row.click_deviceGroup + DEVICE_OFFSET
        user = row.user_id + USER_OFFSET
        item = row.click_article_id + ITEM_OFFSET
        session = row.session_id + SESSION_OFFSET
        region = row.click_region + REGION_OFFSET
        ts = row.click_timestamp
        ts_session_start = row.session_start

        if region not in nos_dict: nos_dict[region] = REGION
        if device not in nos_dict: nos_dict[device] = DEVICE
        if user not in nos_dict: nos_dict[user] = USER
        if session not in nos_dict: nos_dict[session] = SESSION
        if item not in nos_dict: nos_dict[item] = ITEM

        # region -> user
        arestas.append((region, user))
        timestamps.append(None)
        
        # session -> device
        arestas.append((session, device))
        timestamps.append(ts)
        
        # user -> session
        arestas.append((user, session))
        timestamps.append(ts_session_start)
        
        # session -> item
        arestas.append((session, item))
        timestamps.append(ts)

    G.add_vertices([str(k) for k in nos_dict.keys()])
    G.vs['tipo'] = list(nos_dict.values())
    
    G.add_edges([(str(u), str(v)) for u, v in arestas])
    G.es['timestamp'] = timestamps

    del df_total, nos_dict, arestas, timestamps
    print(G.summary())
    return G