import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from networkx.algorithms import bipartite

#grafo bipartido (users + items)
def users_items(df):
    users = df["user_id"]
    items = df["click_article_id"]
    G = nx.Graph()

    G.add_nodes_from(users)
    G.add_nodes_from(items)

    G.add_edges_from(zip(users, items))

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

    plt.title("Grafo user -> Item")
    plt.show()


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
    df = pd.read_csv("clicks_hour_000.csv")
    #users_items(df)
    #users_sessions_items(df)
    #devices_users(df)
    users_os(df)
    #users_regions(df)
    session_interaction(df)