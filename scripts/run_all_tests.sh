#!/bin/bash
# Script para executar todos os testes de fusão sensorial de forma SIMULTÂNEA
# Uso: ./run_all_tests.sh [duração_em_segundos]

DURATION=${1:-45}
RESULTS_DIR=$(rospack find atividade_2)/results
mkdir -p $RESULTS_DIR

echo "========================================"
echo "Iniciando testes de Fusão Sensorial SIMULTÂNEOS"
echo "Duração total do teste: ${DURATION}s"
echo "========================================"
echo "⚠️  ATENÇÃO: PILOTE O ROBÔ USANDO O TELEOP DURANTE O TESTE!"
echo "Tente fazer caminhos curvos e retas para coletar bons dados."
echo "========================================"

echo ""
echo ">>> Lançando as 3 configurações de filtro EKF ao mesmo tempo..."
roslaunch atividade_2 run_all_concurrent.launch &
LAUNCH_PID=$!

# Função para capturar o Ctrl+C e encerrar graciosamente
cleanup() {
    echo ""
    echo ">>> (Ctrl+C detectado) Encerrando testes prematuramente..."
    kill -INT $LAUNCH_PID 2>/dev/null
    wait $LAUNCH_PID 2>/dev/null
    sleep 2
    
    echo ""
    echo ">>> Gerando gráfico consolidado com os dados coletados..."
    python3 $(rospack find atividade_2)/scripts/plot_results.py
    
    echo ""
    echo "========================================"
    echo "Testes concluídos!"
    echo "Resultados em: $RESULTS_DIR"
    echo "========================================"
    exit 0
}

trap cleanup SIGINT

echo ">>> Gravando dados por ${DURATION} segundos... (Pressione Ctrl+C se quiser terminar antes)"
sleep $DURATION

echo ">>> Tempo esgotado. Encerrando os nós..."
kill -INT $LAUNCH_PID 2>/dev/null
wait $LAUNCH_PID 2>/dev/null
sleep 2

# Generate plots
echo ""
echo ">>> Gerando gráfico consolidado..."
python3 $(rospack find atividade_2)/scripts/plot_results.py

echo ""
echo "========================================"
echo "Testes concluídos!"
echo "Resultados em: $RESULTS_DIR"
echo "========================================"
