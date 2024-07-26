import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json

class GenerateGraphController:
    def generateGraph(self, container_name):
        print('Gerando gráfico...')
         # Lê as métricas do arquivo JSON
        with open('./metrics/metrics_server.json', 'r') as f:
            metricsServer = json.load(f)

        try:
            # Organiza as métricas no dicionário auxDockers
            auxDockers = {}
            auxDockers[container_name] = metricsServer[container_name]
        except Exception as e:
            return "Container não encontrado"

        # Gera um gráfico para cada container
        for container_name, metrics in auxDockers.items():
            # Listas para armazenar os dados
            timestamps = []
            cpu_percents = []
            memory_percents = []

            for hour in metrics:
                metric = metrics[hour]
                timestamps.append(pd.to_datetime(metric['timestamp'], format='%Y-%m-%d %H:%M'))
                cpu_percents.append(metric['cpu_percent'])
                memory_percents.append(metric['memory_percent'])

            # Criando um DataFrame
            data = pd.DataFrame({
                'Time': timestamps,
                'CPU_Usage': cpu_percents,
                'Memory_Usage': memory_percents
            })

            # Configurando o gráfico
            plt.figure(figsize=(14, 7))

            # Definindo a largura das barras
            bar_width = 0.35

            # Definindo a posição das barras no eixo X
            r1 = np.arange(len(data['Time']))
            r2 = r1 + bar_width

            # Plotando barras para uso de CPU
            plt.bar(r1, data['CPU_Usage'], width=bar_width, color='blue', label='Uso de CPU (%)')

            # Plotando barras para uso de Memória
            plt.bar(r2, data['Memory_Usage'], width=bar_width, color='red', label='Uso de Memória (%)')

            # Configurando títulos e rótulos
            plt.title(f'Uso de CPU e Memória para {container_name} por Minuto')
            plt.xlabel('Tempo')
            plt.ylabel('Porcentagem de Uso')
            plt.legend()

            # Convertendo os valores do tempo para strings formatadas
            time_labels = data['Time'].dt.strftime('%H:%M')

            # Adicionando rótulos de tempo no eixo X
            plt.xticks(r1 + bar_width / 2, time_labels, rotation=90)

            # Exibindo o gráfico
            plt.tight_layout()
            plt.savefig(f'./graph/{container_name}-cpu_memory_usage.png')
            plt.close()  # Fecha a figura para liberar memória