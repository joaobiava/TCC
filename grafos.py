import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from networkx.algorithms import bipartite
import glob
import os
import sys
import time
from memory_profiler import profile

"""grafo bipartido (users + items) 
faz de um jeito meio cagado, carregando tood o csv antes, 
se o csv tivesse 10G ia cagar com tudo sem nem fazer nada do grafo em si"""
def users_items(arquivos):
    list_df = [pd.read_csv(arquivo) for arquivo in arquivos]
    df = pd.concat(list_df , ignore_index=True)
    users = df["user_id"]
    items = df["click_article_id"]

    G = nx.Graph()

    G.add_nodes_from(users)
    G.add_nodes_from(items)

    G.add_edges_from(zip(users, items))

    print(G)
    del list_df
    del df

""" 
grafo bipartido (users + items)
faz de um jeito mais fofoinho liberando a memoria do csv, nao deixando carregar tudo de uma vez
+ otimizcao de memoria utilizando dtype, q permite diminuir o tamanho da memoria padrao que o pandas utiliza
"""
def users_items_intertuples(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id'], dtype={'user_id': 'int64', 'click_article_id': 'int64'})

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
            u = row[1]
            i = row[2]
            G.add_node(u, subset=0)
            G.add_node(i, subset=1)
            G.add_edge(u, i)

        del df

    print(G)
   # aparentemente deu certo

def users_items_sessions_localizations_devices_intertuples(arquivos):
    G = nx.Graph()

    # usando dtype para diminuir o uso de memória, pq por padrão o pandas usa um valor maior
    for arquivo in arquivos:
        df = pd.read_csv(arquivo, usecols=['user_id', 'click_article_id', 'session_id', 'click_deviceGroup', 'click_region'], 
                         dtype={'user_id': 'uint64', 'click_article_id': 'uint64', 'session_id': 'uint64', 'click_deviceGroup': 'uint8', 'click_region': 'uint8'})

        #itertuples é mais rápido que interrows
        for row in df.itertuples():
            users = row[1]
            items = row[2]
            sessions = row[3]
            devices = row[4]
            regions = row[5]
            G.add_node(users, subset=0)
            G.add_node(sessions, subset=1)
            G.add_node(items, subset=2)
            G.add_node(devices, subset=3)
            G.add_node(regions, subset=4)

            G.add_edge(users, sessions)
            G.add_edge(sessions, items)
            G.add_edge(sessions, devices)
            G.add_edge(users, regions)

        del df

    print(G)
   # aparentemente deu certo

# grafo multipartido (users + sessions + items)
def users_sessions_items(df):
    users = df["user_id"]
    items = df["click_article_id"]
    sessions = df["session_id"]
    G = nx.Graph()

    G.add_nodes_from(users, subset=0)
    G.add_nodes_from(items, subset = 2)
    G.add_nodes_from(sessions, subset = 1)

    G.add_edges_from(zip(users, sessions))
    G.add_edges_from(zip(sessions, items))

    print(G)

    degrees = dict(G.degree())
    top_3_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:3]
    print("top 3 nós")
    for node, degree in top_3_nodes:
        print(f"  {node}: {degree} conexões")

    sys.exit(0)

    plt.figure(figsize=(10, 10))

    pos = nx.multipartite_layout(G, subset_key="subset", scale=10)

    nx.draw(G, pos, with_labels=True, node_size=50)

    plt.title("Grafo user -> item")
    plt.show()


# grafo multipartido (devices + users)
def devices_users(df):
    # Adiciona prefixo para diferenciar os nós
    users = ["user_" + str(u) for u in df["user_id"]]
    os_list = ["os_" + str(o) for o in df["click_os"]]

    G = nx.Graph()
    G.add_nodes_from(users, bipartite=0)
    G.add_nodes_from(os_list, bipartite=1)
    G.add_edges_from(zip(users, os_list))

    print(G)
    plt.figure(figsize=(10, 10))

    user_nodes = set(users)
    pos = nx.bipartite_layout(G, user_nodes, scale=10)
    nx.draw(G, pos, with_labels=True, node_size=50)
    plt.title("Grafo users -> OS")
    plt.show()
    # predominantemente IOs, firefox e chromecast

# grafo devices (users + os)
def users_os(df):
    users = ["user_" + str(u) for u in df["user_id"]]
    os_list = ["os_" + str(o) for o in df["click_os"]]
    G = nx.Graph()
    G.add_nodes_from(users, bipartite=0)
    G.add_nodes_from(os_list, bipartite=1)
    G.add_edges_from(zip(users, os_list))

    print(G)
    plt.figure(figsize=(10, 10))

    user_nodes = set(users)
    pos = nx.bipartite_layout(G, user_nodes, scale=10)
    nx.draw(G, pos, with_labels=True, node_size=50)
    plt.title("Grafo devices -> OS")
    plt.show()


def users_regions(df):
    users = ["user_" + str(u) for u in df["user_id"]]
    region_list = ["region_" + str(o) for o in df["click_region"]]
    G = nx.Graph()
    G.add_nodes_from(users, bipartite=0)
    G.add_nodes_from(region_list, bipartite=1)
    G.add_edges_from(zip(users, region_list))

    print(G)

    degrees = dict(G.degree())
    top_3_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:3]
    print("top 3 nós")
    for node, degree in top_3_nodes:
        print(f"  {node}: {degree} conexões")

    plt.figure(figsize=(10, 10))

    user_nodes = set(users)
    pos = nx.bipartite_layout(G, user_nodes, scale=10)
    nx.draw(G, pos, with_labels=True, node_size=50)
    plt.title("Grafo users -> regions")
    plt.show()


def session_interaction(df):
    sessions = ["session_" + str(u) for u in df["session_id"]]
    interactions = ["interaction_" + str(o) for o in df["session_size"]]
    G = nx.Graph()
    G.add_nodes_from(sessions, bipartite=0)
    G.add_nodes_from(interactions, bipartite=1)
    G.add_edges_from(zip(sessions, interactions))

    print(G)

    plt.figure(figsize=(10, 10))

    session_nodes = set(sessions)
    pos = nx.bipartite_layout(G, session_nodes, scale=10)
    nx.draw(G, pos, with_labels=True, node_size=50)
    plt.title("Grafo users -> regions")
    plt.show()



if __name__ == "__main__":
    pasta = '/home/jaba/Documentos/TCC/clicks'
    arquivos = glob.glob(os.path.join(pasta, "*.csv"))

    #execucao com o csv inteiro
    inicio = time.perf_counter()
    users_items(arquivos)
    fim = time.perf_counter()
    print(f"funcao users_items demorou {fim - inicio} segundos")

    #execucao com liberacao de memoria
    inicio = time.perf_counter()
    users_items_intertuples(arquivos)
    fim = time.perf_counter()
    print(f"funcao users_items_intertuples demorou {fim - inicio} segundos")

    inicio = time.perf_counter()
    users_items_sessions_localizations_devices_intertuples(arquivos)
    fim = time.perf_counter()
    print(f"funcao users_items_sessions_localizations_devices_intertuples demorou {fim - inicio} segundos")

    #tempo entre as duas funccoes quase igual, porem da segunda tem liberacao de memoria do df
    # importante lembrar que nao esta sendo usada uma biblioteca muito especifica para benchmark

    #users_sessions_items(df)
    #devices_users(df)
    #users_os(df)
    #users_regions(df)
    #session_interaction(df)