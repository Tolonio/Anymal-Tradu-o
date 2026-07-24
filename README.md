# Anymal-Tradu-o
API de tradução do anymal
A API gira em torno de 3 arquivos:

processador_relatorio.py – Contém toda a lógica pesada e as regras para tradução. Não interage com a rede.

servidor_web.py – Gere a comunicação de rede pela porta 5050 e recebe os pedidos HTTP.

templates/index.html – Interface: Apresenta os dados ao utilizador final e fornece os botões de ação.

Usamos o ambiente virtual visando não instalar nada no ambiente do robô para não prejudicar algum processo:

Para criar o ambiente virtual vamos rodar SEM DAR COMANDO SUDO:
```
python3 -m venv venv
```

Precisamos rodar o comando parar entrar no ambiente virtual para fazer a instalação das bibliotecas:

```
source venv/bin/activate
```

A instalação precisa da versão libpangoft2-1.0-0 que não vem automatica, então vamos rodar:
```
sudo apt update

sudo apt install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info
```

Utilizamos o flask para subir o html, deep-translator para tradução do xml, lxml para processar e ler o xml e o weasyprint para criarmos o pdf.
```
python3 -m pip install flask deep-translator lxml weasyprint

```

Depois rodamos o código para iniciar o servidor:
```
python3 servidor_web.py
```

Para criar o serviço para iniciar o servidor automaticamente segue o código:

```
sudo nano /etc/systemd/system/servidor_anymal.service
```

Código do nano:

```
[Unit]
Description=Servidor Web do Tradutor ANYmal
After=network.target

[Service]
Type=simple

User=integration
Group=integration

WorkingDirectory=/home/integration/servidor_anymal

Environment="PATH=/home/integration/servidor_anymal/venv/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=/home/integration/servidor_anymal/venv/bin/python3 /home/integration/servidor_anymal/servidor_web.py

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```


# 1. Recarrega os daemons do sistema para reconhecer o novo arquivo

```
sudo systemctl daemon-reload
```

# 2. Ativa o serviço para ligar automaticamente na inicialização do robô

```
sudo systemctl enable servidor_anymal.service
```


# 3. Dá a partida imediata no servidor (sem necessidade de reiniciar o robô)

```
sudo systemctl start servidor_anymal.service
```



# 4. Verifica o status do serviço e os logs de execução

```
sudo systemctl status servidor_anymal.service

```

Quando importamos o Weasyprint o python instala a biblioteca Pillow que usamos para comprimir fotos e o cffi que permite que o python converse com o c e c++. Usamos também a biblioteca Jinja2 para ler o arquivo index.html e injetar dados do robô usando sintaxes como {{ caminho_atual }} ou {% for item in itens %}.

Werkzeug: gerencia a escuta da porta 5050, roteia os links e lida com a transferência de arquivos pesados

Bibliotecas Nativas do Python:

os e pathlib: Motores de interação com o Sistema Operacional. Foram usados exaustivamente para navegar pelas pastas internas do robô


io (especificamente io.BytesIO): Biblioteca de fluxos de dados. Foi vital para a performance e segurança do projeto. Permitiu que o PDF, as imagens comprimidas e o próprio pacote ZIP fossem gerados inteiramente de forma virtual na memória RAM, em vez de gravar e apagar arquivos temporários no SSD físico do robô

zipfile: Usado para criar o pacote final para compressão com ZIP_DEFLATED e compresslevel=9

xml.etree.ElementTree (ET): O interpretador de XML padrão do Python. Trabalhou lado a lado com o lxml para abrir a estrutura de árvore do report.xml, permitindo que o nosso código encontrasse exatamente as tags <message>, <date> e <file> para podermos injetar as traduções em português e os novos nomes das fotos.
