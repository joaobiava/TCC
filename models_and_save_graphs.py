import pickle
import os
import time
import networkx as nx
import pandas as pd

TS_CUTOFF = int(pd.Timestamp('2017-10-18').timestamp() * 1000)

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

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp'], dtype={'user_id': 'uint64', 'click_article_id': 'uint64'})

        df = df[df['click_timestamp'] < TS_CUTOFF]

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
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

def users_sessions_items(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start'])

        df = df[df['click_timestamp'] < TS_CUTOFF]

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
            user = f"u_{row.user_id}"
            item = f"i_{row.click_article_id}"
            session = f"s_{row.session_id}"
            ts = row.click_timestamp
            ts_session_start = row.session_start

            G.add_node(user, tipo="user")
            G.add_node(item, tipo="item")
            G.add_node(session, tipo="session")
            # coloca como atributo da aresta para que o timestamp seja atribuido a interação e nao ao item
            G.add_edge(user, session, timestamp=ts_session_start)
            G.add_edge(session, item, timestamp=ts)

        del df
    print(G)
    return G

def devices_users_sessions_items(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start', 'click_deviceGroup'])

        df = df[df['click_timestamp'] < TS_CUTOFF]

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
            device = f"d_{row.click_deviceGroup}"
            user = f"u_{row.user_id}"
            item = f"i_{row.click_article_id}"
            session = f"s_{row.session_id}"
            ts = row.click_timestamp
            ts_session_start = row.session_start

            G.add_node(device, tipo="device")
            G.add_node(user, tipo="user")
            G.add_node(session, tipo="session")
            G.add_node(item, tipo="item")
            # coloca como atributo da aresta para que o timestamp seja atribuido a interação e nao ao item
            G.add_edge(session, device)
            G.add_edge(user, session, timestamp=ts_session_start)
            G.add_edge(session, item, timestamp=ts)

        del df
    print(G)
    return G

def devices_users_sessions_items_regions(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        # talvez mudar o tipo da variavel para ocupar menos espaco n seja interessante nesse metodo, pq eh apagado a cada evz
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'click_timestamp', 'session_id', 'session_start', 'click_deviceGroup', 'click_region'])

        df = df[df['click_timestamp'] < TS_CUTOFF]

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
            device = f"d_{row.click_deviceGroup}"
            user = f"u_{row.user_id}"
            item = f"i_{row.click_article_id}"
            session = f"s_{row.session_id}"
            region = f"r_{row.click_region}"
            ts = row.click_timestamp
            ts_session_start = row.session_start

            G.add_node(region, tipo="region")
            G.add_node(device, tipo="device")
            G.add_node(user, tipo="user")
            G.add_node(session, tipo="session")
            G.add_node(item, tipo="item")
            # coloca como atributo da aresta para que o timestamp seja atribuido a interação e nao ao item
            G.add_edge(region, user)
            G.add_edge(session, device)
            G.add_edge(user, session, timestamp=ts_session_start)
            G.add_edge(session, item, timestamp=ts)

        del df
    print(G)
    return G