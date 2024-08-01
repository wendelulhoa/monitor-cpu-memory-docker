import sys
import os
import json
import time
from datetime import datetime, timedelta
import pytz

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Discord.SendDiscordController import sendDiscordController
from Graph.GenerateGraphController import GenerateGraphController

class MetricsController:
    def __init__(self):
        super().__init__()
        self.timezone = pytz.timezone('America/Sao_Paulo')

    def getFile(self, filepath):
        try:
            with open(filepath, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def saveFile(self, data, filepath):
        # Verifica se o diretório existe, se não, cria-o
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)

    def parse_timestamp(self, timestamp_str):
        naive_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')
        return self.timezone.localize(naive_dt)

    def filterMetricsLast2Hours(self):
        # Carrega os dados existentes    
        existing_data = self.getFile('./metrics/metrics_server.json')
        
        # Define o limite de tempo (últimas 2 horas)
        time_limit = datetime.now(self.timezone) - timedelta(hours=2)

        # Filtra os dados
        filtered_data = {}
        for container, metrics in existing_data.items():
            filtered_data[container] = {
                hour: data for hour, data in metrics.items()
                if self.parse_timestamp(data['timestamp']) >= time_limit
            }

        # Salva os dados filtrados de volta no arquivo JSON
        self.saveFile(filtered_data, './metrics/metrics_server.json')

    # Função para enviar os dados via POST
    def sendMetrics(self, cpu, memory, memoryUsed, isDocker, description='servidor', name=''):
        # Pega o tempo atual
        current_time = time.time()

        # Configurações do handler
        configs = {
            'webhook_url': 'https://discord.com/api/webhooks/1238229050690900059/hKaWqJ1dthfqVsvCFRdrFmEtW7EWM5yXLIZEHlPTWggZmjO9qy7RAPX-kkjq9LY2KibN'
        }

        # Verifica os valores de CPU e memória e envia para o discord
        if isDocker and cpu >= 90 or memory > 90 or isDocker == False and cpu > 90 or memory > 90:
            metricsServerTimestamps = self.getFile('./metrics/timestamps_metrics.json')
            
            # Organiza as métricas no dicionário auxServers
            auxServers = metricsServerTimestamps

            try:
                auxServers[name] = auxServers[name]

                # Verifica se o name foi enviado nos últimos 60 segundos
                last_send_time = auxServers[name]['time']
                if current_time - last_send_time < 60:
                    return
                
                # Atualiza o tempo de envio
                auxServers[name] = {'time': current_time}
            except Exception as e:
                auxServers[name] = {'time': current_time}
            
            # Salva os dados no arquivo JSONw
            self.saveFile(auxServers, './metrics/timestamps_metrics.json')

            # Gera o gráfico
            generateGraphController = GenerateGraphController()
            generateGraphController.generateGraph(name)

            # Envia para o discord
            discordHandler = sendDiscordController(configs)
            discordHandler.sendFile(f'{description}: CPU={cpu}%, Memória={memory}%, Memória Usada={memoryUsed}, gráfico:', f'./graph/{name}-cpu_memory_usage.png')
            
            # Retorna como sucesso
            return True