import requests
import json
import os
from datetime import datetime
import pytz

class sendDiscordController():
    def __init__(self, configs=None):
        super().__init__()

        # Seta as configurações do canal.
        self.configs = {**configs, **self.loadConfigsFromFile()}
    
    # Carrega as configurações do arquivo JSON
    def loadConfigsFromFile(self):
        # Função para carregar configurações do arquivo JSON
        try:
            with open('config/wu-discord-logger.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print("Arquivo de configuração não encontrado. Usando configurações padrão.")
            return {}
        except json.JSONDecodeError:
            print("Erro ao decodificar o arquivo JSON. Usando configurações padrão.")
            return {}

    def emit(self, record):
        try:
            # Formata o registro
            log_entry = self.format(record)

            # Envia para o Discord
            self.sendToDiscord(log_entry)
        except Exception as e:
            self.handleError(record)

    # Envia para o Discord
    def sendText(self, message):
        # Pega a url do webhook
        webhookUrl = self.configs.get('webhook_url')

        if webhookUrl:
            # Cria o payload
            payload = {
                'username': self.configs['from']['name'].replace(' ', ''),
                'content': "",
                'embeds': [
                    {
                        'title': self.getTitle(),
                        'description': self.getDescription(message),
                        'color': self.getColor(),
                        'attachments': None
                    }
                ]
            }

            # Envia para o Discord
            requests.post(webhookUrl, json=payload)

    def sendFile(self, message, path):
        # Envia mensagem de texto
        self.sendText(message)

        # Faz o envio do arquivo via discord
        url = self.configs.get('webhook_url')
        headers = {'Authorization': 'auth_trusted_header'}
        
        # Verifica se o arquivo existe antes de tentar abri-lo
        if os.path.exists(path):
            files = {
                'nameFile': (path, open(path, 'rb'), 'application/octet-stream')
            }

            # Envia para o Discord
            requests.post(url, headers=headers, files=files)
        else:
            print(f"File not found: {path}")
    
    # Pega o titulo
    def getTitle(self):
        levelName = 'INFO'
        brasil_tz = pytz.timezone('America/Sao_Paulo')
        currentDate = datetime.now(brasil_tz).strftime('%Y-%m-%d %H:%M:%S')
        nameApp = self.configs['from']['name'].replace(' ', '').lower()
        emoji = self.configs['emojis'].get(levelName, '')

        return f"{emoji} **``[{currentDate}] {nameApp}.{levelName}``**"

    # Pega a descrição
    def getDescription(self, message):
        return f":black_small_square: ``{message}``"

    # Pega a cor 
    def getColor(self):
        return int(self.configs['colors'].get('INFO', '4caf50'), 16)  # Exemplo de uso da cor INFO