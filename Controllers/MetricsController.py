import sys
import os
import psutil
import docker
import json
import time
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Controllers.SendDiscordController import sendDiscordController
from Controllers.GenerateGraphController import GenerateGraphController

class MetricsController():
    def __init__(self):
        self.client = docker.from_env()

   # Função para obter uso de CPU e memória do sistema
    def getSystemMetrics(self):
        # Pega as informações de porcentagem da máquina
        cpuPercent = psutil.cpu_percent(interval=1)
        memoryInfo = psutil.virtual_memory()
        memoryPercent = memoryInfo.percent

        return cpuPercent, memoryPercent
    
    # Função para obter uso de CPU e memória dos contêineres Docker
    def getDockerMetrics(self):
        containers = self.client.containers.list()
        metrics = []

        for container in containers:
            stats = container.stats(stream=False)
            cpuPercent = self.calculateCpuPercent(stats)
            memoryUsage = stats['memory_stats']['usage']
            memoryLimit = stats['memory_stats']['limit']
            memoryPercent = (memoryUsage / memoryLimit) * 100

            metrics.append({
                'container_name': container.name,
                'cpu_percent': cpuPercent,
                'memory_percent': memoryPercent,
                'memory_limit': memoryLimit
            })

        return metrics

    # Função para calcular a porcentagem de uso de CPU
    def calculateCpuPercent(self, stats):
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        
        # Verifica se 'percpu_usage' existe
        if 'percpu_usage' in stats['cpu_stats']['cpu_usage']:
            number_cpus = len(stats['cpu_stats']['cpu_usage']['percpu_usage'])
        else:
            number_cpus = 1  # Assumindo 1 CPU se 'percpu_usage' não estiver presente

        if system_delta > 0.0 and cpu_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * number_cpus * 100.0
        else:
            cpu_percent = 0.0

        return cpu_percent

    # Função para enviar os dados via POST
    def sendMetrics(self, cpu, memory, description='servidor', name=''):
        # Configurações do handler
        configs = {
            'webhook_url': 'https://discord.com/api/webhooks/1238229050690900059/hKaWqJ1dthfqVsvCFRdrFmEtW7EWM5yXLIZEHlPTWggZmjO9qy7RAPX-kkjq9LY2KibN'
        }

        # Verifica os valores de CPU e memória
        if cpu > 90 or memory > 90:
            # Gera o gráfico
            generateGraphController = GenerateGraphController()
            generateGraphController.generateGraph(name)

            # Envia para o discord
            discordHandler = sendDiscordController(configs)
            discordHandler.sendToDiscord(f'{description}: CPU={cpu}%, Memória={memory}%.')


# Exemplo de uso
if __name__ == "__main__":
    while True:
        # Instância o controlador de metricas
        metricsController = MetricsController()

        # Pega o timestamp
        datetime_object = datetime.now()
        timestamp = datetime_object.strftime('%Y-%m-%d %H:%M')
        hour = datetime_object.strftime('%H:%M')

        # Lê o arquivo JSON existente
        try:
            with open('./metrics/metrics_server.json', 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # Pega os valores
        cpu, memory = metricsController.getSystemMetrics()

        # Verifica se 'servidor' existe no dicionário
        if 'servidor' not in existing_data:
            existing_data['servidor'] = {}

        # Verifica se a hora existe no dicionário do servidor
        if hour not in existing_data['servidor']:
            existing_data['servidor'][hour] = {
                'cpu_percent': round(cpu, 1),
                'memory_percent': round(memory, 1),
                'timestamp': timestamp
            }
        else:
            # Calcula a média dos valores existentes e novos
            existing_cpu_percent = existing_data['servidor'][metric['hour']]['cpu_percent']
            existing_memory_percent = existing_data['servidor'][metric['hour']]['memory_percent']
            
            new_cpu_percent = round((existing_cpu_percent + cpuPercent) / 2, 1)
            new_memory_percent = round((existing_memory_percent + memoryPercent) / 2, 1)
            
            existing_data['servidor'][metric['hour']] = {
                'container_name': 'servidor',
                'cpu_percent': new_cpu_percent,
                'memory_percent': new_memory_percent,
                'timestamp': metric['timestamp']
            }

        # Atualiza o arquivo JSON
        with open('./metrics/metrics_server.json', 'w') as f:
            json.dump(existing_data, f, indent=4)

        # Envia para o discord   
        metricsController.sendMetrics(cpu, memory, 'Servidor em alerta', 'servidor')
        
        # time.sleep(30)
        docker_metrics = metricsController.getDockerMetrics()

        # Adiciona timestamp aos dados
        for metric in docker_metrics:
            metric['timestamp'] = timestamp
            metric['hour']      = hour

        for metric in docker_metrics:
            # Pega os valores
            containerName = metric['container_name']
            cpuPercent    = round(metric['cpu_percent'], 1)
            memoryPercent = round(metric['memory_percent'], 1)

            # Verifica se o containerName existe no dicionário
            if containerName not in existing_data:
                existing_data[containerName] = {}

            # Verifica se a hora existe no dicionário do container
            if metric['hour'] not in existing_data[containerName]:
                existing_data[containerName][metric['hour']] = {
                    'container_name': containerName,
                    'cpu_percent': cpuPercent,
                    'memory_percent': memoryPercent,
                    'timestamp': metric['timestamp']
                }
            else:
                # Calcula a média dos valores existentes e novos
                existing_cpu_percent = existing_data[containerName][metric['hour']]['cpu_percent']
                existing_memory_percent = existing_data[containerName][metric['hour']]['memory_percent']
                
                new_cpu_percent = round((existing_cpu_percent + cpuPercent) / 2, 1)
                new_memory_percent = round((existing_memory_percent + memoryPercent) / 2, 1)
                
                existing_data[containerName][metric['hour']] = {
                    'container_name': containerName,
                    'cpu_percent': new_cpu_percent,
                    'memory_percent': new_memory_percent,
                    'timestamp': metric['timestamp']
                }
            
            # Salva os dados atualizados no arquivo JSON
            with open('./metrics/metrics_server.json', 'w') as f:
                json.dump(existing_data, f, indent=4)
            
            metricsController.sendMetrics(cpuPercent, memoryPercent, containerName + ' em alerta', containerName)