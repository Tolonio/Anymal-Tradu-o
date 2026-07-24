# Anymal-Tradu-o
API de tradução do anymal
A API gira em torno de 3 arquivos:

processador_relatorio.py – Contém toda a lógica pesada e as regras para tradução. Não interage com a rede.

servidor_web.py – Gere a comunicação de rede pela porta 5050 e recebe os pedidos HTTP.

templates/index.html – Interface: Apresenta os dados ao utilizador final e fornece os botões de ação.

Usamos o ambiente virtual visando não instalar nada no ambiente do robô para não prejudicar algum processo:

Utilizamos o flask para subir o html, deep-translator para tradução do xml, lxml para processar e ler o xml e o weasyprint para criarmos o pdf.

python3 -m pip install flask deep-translator lxml weasyprint

Quando importamos o Weasyprint o python instala a biblioteca Pillow que usamos para comprimir fotos e o cffi que permite que o python converse com o c e c++. Usamos também a biblioteca Jinja2 para ler o arquivo index.html e injetar dados do robô usando sintaxes como {{ caminho_atual }} ou {% for item in itens %}.
