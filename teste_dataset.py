import pandas as pd
import glob
import os

"""
conclusões:
nao tem sessions_clicks de tamanho 1 apenas >= 2;
nao tem nenhum valor nulo
"""

#df = pd.read_csv("./clicks/clicks_hour_000.csv")
pasta = '/home/jaba/Documentos/TCC/clicks'
arquivos = glob.glob(os.path.join(pasta, "*.csv"))

list_df = [pd.read_csv(arquivo) for arquivo in arquivos]
df_final = pd.concat(list_df , ignore_index=True)

# Quantidade de usuários únicos
num_usuarios = df_final['user_id'].nunique()
print(f"Quantidade de usuários: {num_usuarios}")

# Quantidade de itens (artigos) diferentes
num_itens = df_final['click_article_id'].nunique()
print(f"Quantidade de itens: {num_itens}")

#quantidade de sessões
qntd_sessoes = df_final['session_id'].nunique()
print(f"quantidade de sessões: {qntd_sessoes}")

# Média de sessões por usuário
media_sessoes = df_final.groupby('user_id')['session_id'].nunique().mean()
print(f"Média de sessões por usuário: {media_sessoes}")

#mediana de sessões
mediana_sessoes = df_final.groupby('user_id')['session_id'].nunique().median()
print(f"mediana de sessões: {mediana_sessoes}")

# maximo de sessoes de um unico usuário
media_sessoes = df_final.groupby('user_id')['session_id'].nunique().max()
print(f"máximo de sessões de um usuário: {media_sessoes}")

media_iteracoes_sessoes = df_final.groupby('session_id')['session_size'].first().mean()
print(f"media de iterações por sessao: {media_iteracoes_sessoes}")

mediana_iteracoes_sessoes = df_final.groupby('session_id')['session_size'].first().median()
print(f"mediana de iterações por sessao: {mediana_iteracoes_sessoes}")

# só pra ordenar o dataset pelo timestamp das sessões (incrédulo com a quantidade de iterações em tão pouco tempo)
df_final['session_start'] = pd.to_datetime(df_final['session_start'], unit='ms')
df_final = df_final.sort_values(by='session_start')
# 2017-10-01 02:37:03 (primeira sessão do dataset)
# 2017-10-17 03:36:19 (ultima sessão do dataset)


print(df_final)