import sys
import os
import psutil
import json
import time
from datetime import datetime, timedelta
import pytz

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Metrics.MetricsController import MetricsController

class MetricsServerController(MetricsController):
    def __init__(self):
        super().__init__()
        self.serverName = self.getFile('./config/servername.json')['name']

    # Função para obter uso de CPU e memória do sistema
    def getSystemMetrics(self):
        # Pega as informações de porcentagem da máquina
        cpuPercent = psutil.cpu_percent(interval=1)
        memoryInfo = psutil.virtual_memory()
        memoryPercent = memoryInfo.percent
        memoryUsed = (memoryInfo.used / (1024 * 1024 * 1024))

        # Faz o cálculo para megabit
        if memoryUsed < 1:
            memoryUsed = (memoryInfo.used / (1024 * 1024))
            memoryUsed =  f"{memoryUsed:.2f} MiB"
        else:
            memoryUsed =  f"{memoryUsed:.2f} GiB"

        return cpuPercent, memoryPercent, memoryUsed
    
    # Pega o nome do servidor
    def getNameServer(self):
        return self.serverName
    
    # Seta as métricas do servidor
    def setMetricsServer(self):
        # Nome do servidor
        serverName = self.getNameServer()

        # Pega o timestamp
        timezone = pytz.timezone('America/Sao_Paulo')
        datetime_object = datetime.now(timezone)
        timestamp = datetime_object.strftime('%Y-%m-%d %H:%M')
        hour = datetime_object.strftime('%H:%M')

        # Lê o arquivo JSON existente
        existing_data = self.getFile('./metrics/metrics_server.json')

        # Pega os valores
        cpu, memory, memoryUsed = self.getSystemMetrics()

        # Verifica se 'servidor' existe no dicionário
        if serverName not in existing_data:
            existing_data[serverName] = {}

        # Verifica se a hora existe no dicionário do servidor
        if hour not in existing_data[serverName]:
            existing_data[serverName][hour] = {
                'cpu_percent': round(cpu, 1),
                'memory_percent': round(memory, 1),
                'timestamp': timestamp
            }
        else:
            # Calcula a média dos valores existentes e novos
            existing_cpu_percent = existing_data[serverName][hour]['cpu_percent']
            existing_memory_percent = existing_data[serverName][hour]['memory_percent']
            
            new_cpu_percent = round((existing_cpu_percent + cpu) / 2, 2)
            new_memory_percent = round((existing_memory_percent + memory) / 2, 2)
            
            existing_data[serverName][hour] = {
                'container_name': serverName,
                'cpu_percent': new_cpu_percent,
                'memory_percent': new_memory_percent,
                'timestamp': timestamp
            }

        # Salva os dados atualizados no arquivo JSON
        self.saveFile(existing_data, './metrics/metrics_server.json')

        # Envia para o discord   
        self.sendMetrics(cpu, memory, memoryUsed, 'Servidor em alerta', serverName)
    
# Exemplo de uso
if __name__ == "__main__":
    while True:
        # Instância o controlador de metricas
        metricsServerController = MetricsServerController()
        metricsServerController.filterMetricsLast2Hours()

        print('alertando')

        # Começa o processo de coleta de métricas
        metricsServerController.setMetricsServer()