import sys
import os
import docker
from datetime import datetime, timedelta
import pytz

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Metrics.MetricsController import MetricsController
from Metrics.MetricsServerController import MetricsServerController

class MetricsDockerController(MetricsController):
    def __init__(self):
        super().__init__()
        self.client = docker.from_env()
        self.serverName = self.getFile('./config/servername.json')['name']
    
    # Função para obter uso de CPU e memória dos contêineres Docker
    def getDockerMetrics(self):
        containers = self.client.containers.list()
        metrics = []

        for container in containers:
            try:
                stats_generator = container.stats(decode=True, stream=True)
                stats = next(stats_generator)  # Pega o primeiro item do gerador

                cpuPercent = 0
                memoryUsage = stats['memory_stats']['usage']
                memoryLimit = stats['memory_stats']['limit']
                memoryPercent = (memoryUsage / memoryLimit) * 100
                memoryUsed = (memoryUsage / (1024 * 1024 * 1024)) # Converte bytes para GiB

                # Faz o cálculo para megabit
                if memoryUsed < 1:
                    memoryUsed = (memoryUsage / (1024 * 1024))
                    memoryUsed =  f"{memoryUsed:.2f} MiB"
                else:
                    memoryUsed =  f"{memoryUsed:.2f} GiB"

                metrics.append({
                    'container_name': container.name,
                    'cpu_percent': cpuPercent,
                    'memory_percent': memoryPercent,
                    'memory_limit': memoryLimit,
                    'memory_used': memoryUsed
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
    
    # Ajusta o limite de memória de um contêiner
    def adjustMemoryContainer(self, container_name, memory_limit_mb, increment_mb):
        container = self.client.containers.get(container_name)
        stats = container.stats(stream=False)
        memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)  # Convertendo para MB

        print(f'Memória do contêiner {container_name}: {memory_usage} MB, Limite de Memória: {memory_limit_mb} MB')

        new_memory_limit = memory_limit_mb + increment_mb
        new_memoryswap_limit = new_memory_limit * 2  # Ajuste conforme necessário

        container.update(mem_limit=f'{new_memory_limit}m', memswap_limit=f'{new_memoryswap_limit}m')
        print(f'Memória do contêiner {container_name} aumentada para {new_memory_limit} MB e memória swap para {new_memoryswap_limit} MB')

    def setMetricsDocker(self):
        # Pega o timestamp
        timezone = pytz.timezone('America/Sao_Paulo')
        datetime_object = datetime.now(timezone)
        timestamp = datetime_object.strftime('%Y-%m-%d %H:%M')
        hour = datetime_object.strftime('%H:%M')

        # Lê o arquivo JSON existente
        existing_data = self.getFile('./metrics/metrics_server.json')
        
        # time.sleep(30)
        docker_metrics = metricsDockerController.getDockerMetrics()

        for metric in docker_metrics:
            # Adiciona timestamp aos dados
            metric['timestamp'] = timestamp
            metric['hour']      = hour

            # Pega o valor em mb
            memoryUsed = metric['memory_used']

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
            metricsDockerController.saveFile(existing_data, './metrics/metrics_server.json')
            
            print(f"Container: {containerName}, CPU: {cpuPercent}%, Memória: {memoryPercent}%, Memória Usada: {memoryUsed}")

            # Envia para o discord
            metricsDockerController.sendMetrics(cpuPercent, memoryPercent, memoryUsed, containerName + ' em alerta', containerName)
# Exemplo de uso
if __name__ == "__main__":
    while True:
        # Instância o controlador de metricas
        metricsDockerController = MetricsDockerController()
        metricsDockerController.filterMetricsLast2Hours()
        metricsDockerController.setMetricsDocker()

        # Instancia o controlador de servidor 
        metricsServerController = MetricsServerController()
        metricsServerController.setMetricsServer()