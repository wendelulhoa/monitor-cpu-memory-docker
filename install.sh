#!/bin/bash

# Verificar se o script está sendo executado como root
if [ "$EUID" -ne 0 ]; then
  echo "Por favor, execute como root"
  exit 1
fi

# Atualizar lista de pacotes e instalar dependências do sistema
echo "Atualizando lista de pacotes..."
sudo apt-get update

echo "Instalando dependências do sistema..."
sudo apt-get install -y python3 python3-pip libssl-dev libffi-dev

# Verificar se o arquivo requirements.txt existe
if [ ! -f requirements.txt ]; then
  echo "Arquivo requirements.txt não encontrado!"
  exit 1
fi

# Instalar dependências do Python
echo "Instalando dependências do Python..."
pip3 install -r requirements.txt

# Definir SCRIPT_PATH como o diretório onde o script está localizado
SCRIPT_PATH=$(dirname "$(readlink -f "$0")")

# Definir WORKING_DIR como o diretório de trabalho atual
WORKING_DIR=$(pwd)

echo "SCRIPT_PATH: $SCRIPT_PATH"
echo "WORKING_DIR: $WORKING_DIR"

# Criar o arquivo de serviço systemd
SERVICE_FILE=/etc/systemd/system/monitor-cpu-python.service

echo "Criando o arquivo de serviço systemd em $SERVICE_FILE= $SCRIPT_PATH..."

cat <<EOL | sudo tee $SERVICE_FILE
[Unit]
Description=monitor-cpu-python
After=network.target

[Service]
ExecStart=/usr/bin/python3 "$SCRIPT_PATH/Controllers/MetricsController.py"
WorkingDirectory=$WORKING_DIR
Restart=always
User=$(whoami)
Group=$(whoami)
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

# Habilitar e iniciar o serviço
echo "Habilitando e iniciando o serviço..."
sudo systemctl daemon-reload
sudo systemctl enable monitor-cpu-python.service
sudo systemctl start monitor-cpu-python.service

# Verificar o status do serviço
sudo systemctl status monitor-cpu-python.service