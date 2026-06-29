#!/usr/bin/env python3
"""
Script para geração de gráficos comparativos dos resultados de fusão sensorial.

Lê os arquivos CSV de séries temporais e métricas do diretório de resultados,
e gera gráficos de trajetória, erro de posição, erro de orientação e um
resumo em barras das métricas principais.

Este script NÃO é um nó ROS e pode ser executado diretamente com Python.
"""

import os
import glob
import csv
import sys

import matplotlib
matplotlib.use('Agg')  # Backend não-interativo para salvar figuras
import matplotlib.pyplot as plt

# Diretório de resultados (detectado automaticamente)
# Tenta usar rospkg, senão usa caminho relativo ao script
try:
    import rospkg
    _rospack = rospkg.RosPack()
    RESULTS_DIR = os.path.join(_rospack.get_path('atividade_2'), 'results')
except Exception:
    RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')

# Mapeamento de nomes de configuração para rótulos legíveis
CONFIG_LABELS = {
    'odom_only': 'Odom',
    'odom_imu': 'Odom+IMU',
    'odom_imu_gps': 'Odom+IMU+GPS',
}

# Cores exatas da imagem do usuário
CONFIG_COLORS = {
    'odom_only': 'r',
    'odom_imu': 'g',
    'odom_imu_gps': 'b',
}

def get_label(config_name):
    return CONFIG_LABELS.get(config_name, config_name)

def get_color(config_name):
    return CONFIG_COLORS.get(config_name, 'k')

def read_timeseries(filepath):
    data = {
        'timestamp': [], 'x_est': [], 'y_est': [], 'yaw_est': [],
        'x_gt': [], 'y_gt': [], 'yaw_gt': [], 'pos_error': [], 'yaw_error': []
    }
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key in data:
                    data[key].append(float(row[key]))
    except Exception as e:
        print(f"  AVISO: Erro ao ler {filepath}: {e}")
        return None
    return data

def read_metrics(filepath):
    metrics = {}
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics[row['metric']] = float(row['value'])
    except Exception as e:
        return None
    return metrics

def plot_comparativo(all_timeseries, all_metrics, configs):
    # Figura 1x2, mesmo formato da imagem do usuário
    fig = plt.figure(figsize=(16, 7))
    
    # 1. Comparativo de Trajetórias (Esquerda)
    ax1 = fig.add_subplot(121)
    
    # Ground truth (desenha apenas uma vez usando k--)
    for config_name in configs:
        data = all_timeseries[config_name]
        ax1.plot(data['x_gt'], data['y_gt'], 'k--', linewidth=2, label='Ground Truth', zorder=1)
        break
        
    for config_name in configs:
        data = all_timeseries[config_name]
        rmse = all_metrics[config_name].get('rmse', 0.0) if all_metrics and config_name in all_metrics else 0.0
        label = f"{get_label(config_name)} (RMSE: {rmse:.2f})"
        
        ax1.plot(
            data['x_est'], data['y_est'],
            color=get_color(config_name),
            linewidth=1.5,
            label=label,
            zorder=2
        )
        
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_title('Comparativo de Trajetorias')
    ax1.legend()
    ax1.grid(True)
    ax1.set_aspect('equal', adjustable='datalim')

    # 2. Erros de Posicao vs Tempo (Direita)
    ax2 = fig.add_subplot(122)
    for config_name in configs:
        data = all_timeseries[config_name]
        label = f"Erro {get_label(config_name)}"
        
        ax2.plot(
            data['timestamp'], data['pos_error'],
            color=get_color(config_name),
            linewidth=1.5,
            label=label
        )
        
    ax2.set_xlabel('Tempo (s)')
    ax2.set_ylabel('Erro de Posicao (m)')
    ax2.set_title('Erros de Posicao vs Tempo')
    ax2.legend()
    ax2.grid(True)
    
    # Salvar a imagem exatamente com o nome pedido
    filepath = os.path.join(RESULTS_DIR, 'atividade_2_comparacao_plots.png')
    fig.tight_layout(pad=3.0)
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Gráfico salvo: {filepath}")

def main():
    print("\n==================================================")
    print("  Geração de Gráficos de Fusão Sensorial")
    print("==================================================")

    if not os.path.exists(RESULTS_DIR):
        print(f"ERRO: Diretório de resultados não encontrado: {RESULTS_DIR}")
        sys.exit(1)

    # Forçar o uso de um estilo mais limpo, parecido com o da imagem
    plt.style.use('default')

    timeseries_files = sorted(glob.glob(os.path.join(RESULTS_DIR, '*_timeseries.csv')))
    if not timeseries_files:
        print("ERRO: Nenhum arquivo de série temporal encontrado.")
        sys.exit(1)

    all_timeseries = {}
    all_metrics = {}
    configs = []

    for ts_file in timeseries_files:
        config_name = os.path.basename(ts_file).replace('_timeseries.csv', '')
        ts_data = read_timeseries(ts_file)
        if not ts_data or len(ts_data['timestamp']) == 0:
            continue

        metrics_file = os.path.join(RESULTS_DIR, f'{config_name}_metrics.csv')
        m_data = read_metrics(metrics_file) if os.path.exists(metrics_file) else None

        all_timeseries[config_name] = ts_data
        if m_data:
            all_metrics[config_name] = m_data
        configs.append(config_name)

    if not configs:
        print("ERRO: Nenhuma configuração válida encontrada.")
        sys.exit(1)

    # Força a ordem correta para as cores e legendas baterem certinho
    order = ['odom_only', 'odom_imu', 'odom_imu_gps']
    configs = [c for c in order if c in configs]

    print("  Gerando gráfico único (Comparativo de Trajetorias e Erros)...")
    plot_comparativo(all_timeseries, all_metrics, configs)

    print("\n==================================================")
    print("  Gráfico gerado com sucesso!")
    print(f"  Diretório: {RESULTS_DIR}")
    print("==================================================\n")

if __name__ == '__main__':
    main()
