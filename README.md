# Anymal-Tradu-o
API de tradução do anymal
A API gira em torno de 3 arquivos:

processador_relatorio.py – Contém toda a lógica pesada e as regras para tradução. Não interage com a rede.

servidor_web.py – Gere a comunicação de rede pela porta 5050 e recebe os pedidos HTTP.

templates/index.html – Interface: Apresenta os dados ao utilizador final e fornece os botões de ação.
