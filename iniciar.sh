#!/bin/bash
#Marcar el fichero como ejecutable con->   chmod +x iniciar.sh

PORTS=(5000,6000)
for port in "${PORTS[@]}"; do
	PID=$(sudo lsof -t -i :$port)
	if [ -n "$PID" ]; then
		echo "Puerto $port en uso. Cerrando proceso $PID..."
		sudo kill -9 $PID
	else
		echo "Puerto $port no esta en uso"
	fi
done

echo "Iniciando Contador de Huevos......"
cd ./utils
python ./egg-counter.py
