import requests
import json
from datetime import datetime

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
    def sendToDiscord(self, message):
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
            response = requests.post(webhookUrl, json=payload)

            # Verifica se deu tudo certo
            if response.status_code != 204:
                print(f"Failed to send log to Discord: {response.status_code}, {response.text}")
    
    # Pega o titulo
    def getTitle(self):
        levelName = 'INFO'
        currentDate = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        nameApp = self.configs['from']['name'].replace(' ', '').lower()
        emoji = self.configs['emojis'].get(levelName, '')

        return f"{emoji} **``[{currentDate}] {nameApp}.{levelName}``**"

    # Pega a descrição
    def getDescription(self, message):
        return f":black_small_square: ``{message}``"

    # Pega a cor 
    def getColor(self):
        return int(self.configs['colors'].get('INFO', '4caf50'), 16)  # Exemplo de uso da cor INFO