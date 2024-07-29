import sys
import os
import psutil
import docker
import json
import time
from datetime import datetime, timedelta, timezone
import pytz

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Controllers.SendDiscordController import sendDiscordController
from Controllers.GenerateGraphController import GenerateGraphController

class MetricsController():
    def __init__(self):
        self.client = docker.from_env()
        
    def filterMetricsLast2Hours(self):
        # Carrega os dados existentes
        self.getDockerMetrics()

        # Carrega os dados existentes    
        existing_data = self.getFile('./metrics/metrics_server.json')
        
        # Define o fuso horário do Brasil
        brasil_tz = pytz.timezone('America/Sao_Paulo')
        
        # Define o limite de tempo (últimas 2 horas) no fuso horário do Brasil
        time_limit = datetime.now(brasil_tz) - timedelta(hours=2)

        # Função auxiliar para converter string de timestamp para objeto datetime
        def parse_timestamp(timestamp_str):
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')

        # Filtra os dados
        filtered_data = {}
        for container, metrics in existing_data.items():
            filtered_data[container] = {
                hour: data for hour, data in metrics.items()
                if parse_timestamp(data['timestamp']) >= time_limit
            }

        # Salva os dados filtrados de volta no arquivo JSON
        self.saveFile(filtered_data, './metrics/metrics_server.json')

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
            try:
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
            except KeyError as e:
                # Opcional: Registrar o erro para depuração
                print(f"Erro ao processar o contêiner {container.name}: {e}")
            except Exception as e:
                # Capturar outras exceções
                print(f"Erro inesperado ao processar o contêiner {container.name}: {e}")

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
        # Pega o tempo atual
        current_time = time.time()

        # Configurações do handler
        configs = {
            'webhook_url': 'https://discord.com/api/webhooks/1238229050690900059/hKaWqJ1dthfqVsvCFRdrFmEtW7EWM5yXLIZEHlPTWggZmjO9qy7RAPX-kkjq9LY2KibN'
        }

        # Verifica os valores de CPU e memória e envia para o discord
        if cpu > 90 or memory > 90:
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
            discordHandler.sendFile(f'{description}: CPU={cpu}%, Memória={memory}%, gráfico:', f'./graph/{name}-cpu_memory_usage.png')
            
            # Retorna como sucesso
            return True
    
    def saveFile(self, content, path):
        # Criar o diretório se não existir
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Salva os dados atualizados no arquivo JSON
        with open(path, 'w') as f:
            json.dump(content, f, indent=4) 
    
    def getFile(self,path):
        # Lê o arquivo JSON existente
        try:
            with open(path, 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}
        
        return existing_data

# Exemplo de uso
if __name__ == "__main__":
    while True:
        # Instância o controlador de metricas
        metricsController = MetricsController()
        metricsController.filterMetricsLast2Hours()

        # Pega o timestamp
        # Define o fuso horário do Brasil
        brasil_tz = pytz.timezone('America/Sao_Paulo')
        datetime_object = datetime.now(brasil_tz)
        timestamp = datetime_object.strftime('%Y-%m-%d %H:%M')
        hour = datetime_object.strftime('%H:%M')

        # Lê o arquivo JSON existente
        existing_data = metricsController.getFile('./metrics/metrics_server.json')

        # Pega os valores
        cpu, memory = metricsController.getSystemMetrics()

        print(f"CPU: {cpu}%, Memória: {memory}%")

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
            existing_cpu_percent = existing_data['servidor'][hour]['cpu_percent']
            existing_memory_percent = existing_data['servidor'][hour]['memory_percent']
            
            new_cpu_percent = round((existing_cpu_percent + cpu) / 2, 2)
            new_memory_percent = round((existing_memory_percent + memory) / 2, 2)
            
            existing_data['servidor'][hour] = {
                'container_name': 'servidor',
                'cpu_percent': new_cpu_percent,
                'memory_percent': new_memory_percent,
                'timestamp': timestamp
            }

        # Salva os dados atualizados no arquivo JSON
        metricsController.saveFile(existing_data, './metrics/metrics_server.json')

        # Envia para o discord   
        metricsController.sendMetrics(cpu, memory, 'Servidor em alerta', 'servidor')
        
        # time.sleep(30)
        docker_metrics = metricsController.getDockerMetrics()

        for metric in docker_metrics:
            # Adiciona timestamp aos dados
            metric['timestamp'] = timestamp
            metric['hour']      = hour

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
                
                new_cpu_percent = round((existing_cpu_percent + cpuPercent) / 2, 2)
                new_memory_percent = round((existing_memory_percent + memoryPercent) / 2, 2)

                # Atualiza com a média
                cpuPercent = new_cpu_percent
                memoryPercent = new_memory_percent
                
                existing_data[containerName][metric['hour']] = {
                    'container_name': containerName,
                    'cpu_percent': new_cpu_percent,
                    'memory_percent': new_memory_percent,
                    'timestamp': metric['timestamp']
                }
            
            # Salva os dados atualizados no arquivo JSON
            metricsController.saveFile(existing_data, './metrics/metrics_server.json')
            
            # Envia para o discord
            metricsController.sendMetrics(cpuPercent, memoryPercent, containerName + ' em alerta', containerName)