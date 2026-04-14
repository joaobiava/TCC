import pandas as pd
import glob
import os

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
print(f"Quantidade de itens diferentes: {num_itens}")

# Média de sessões por usuário
media_sessoes = df_final.groupby('user_id')['session_id'].nunique().mean()
print(f"Média de sessões por usuário: {media_sessoes}")

#mediana de sessões
media_sessoes = df_final.groupby('user_id')['session_id'].nunique().median()
print(f"mediana de sessões: {media_sessoes}")

# maximo de seesoes de um unico usuário
media_sessoes = df_final.groupby('user_id')['session_id'].nunique().max()
print(f"máximo de sessões de um usuário: {media_sessoes}")

#print(df_final)

"""
se tivesse valores uns seria útil, mas n tem, ent talvez altere para valores menores que 5 talvez
df_final = df_final[df_final['session_size'] >= 2]
nao temos dados nulos tbm
print(df_final.isna().sum())
 conclusões:
nao tem sessions_clicks de tamanho 1 apenas >= 2;
nao tem nenhum valor nulo
"""