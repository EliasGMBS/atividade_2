#!/usr/bin/env python3
"""
Nó ROS para avaliação de métricas de fusão sensorial em tempo real.

Subscreve aos tópicos /odometry/filtered (estimativa do filtro) e /gt/odom
(ground truth do Gazebo), sincroniza as mensagens e calcula erros de posição
e orientação. Ao encerrar, exibe um resumo formatado e salva os resultados
em arquivos CSV no diretório de resultados.
"""

import os
import math
import csv

import rospy
import rospkg
import message_filters
import tf.transformations as tft
from nav_msgs.msg import Odometry


class MetricsEvaluator:
    """Classe para avaliação de métricas de fusão sensorial."""

    def __init__(self):
        rospy.init_node('metrics_evaluator', anonymous=False)

        # Nome da configuração para salvar resultados
        self.config_name = rospy.get_param('~config_name', 'test')

        # Diretório de resultados (detectado automaticamente via rospkg)
        rospack = rospkg.RosPack()
        pkg_path = rospack.get_path('atividade_2')
        self.results_dir = os.path.join(pkg_path, 'results')
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            rospy.loginfo("Diretório de resultados criado: %s", self.results_dir)

        # Listas para armazenar dados da série temporal
        self.timestamps = []
        self.x_est_list = []
        self.y_est_list = []
        self.yaw_est_list = []
        self.x_gt_list = []
        self.y_gt_list = []
        self.yaw_gt_list = []
        self.pos_errors = []
        self.yaw_errors = []

        self.start_time = None

        # Subscribers sincronizados (removido a barra de /odometry/filtered para respeitar namespace)
        sub_filtered = message_filters.Subscriber('odometry/filtered', Odometry)
        sub_gt = message_filters.Subscriber('/gt/odom', Odometry)

        self.sync = message_filters.ApproximateTimeSynchronizer(
            [sub_filtered, sub_gt], queue_size=50, slop=0.1
        )
        self.sync.registerCallback(self.sync_callback)

        # Callback de encerramento
        rospy.on_shutdown(self.on_shutdown)

        rospy.loginfo(
            "Nó metrics_evaluator iniciado. Configuração: '%s'", self.config_name
        )

    @staticmethod
    def _yaw_from_quaternion(orientation):
        """Extrai o ângulo yaw de um quaternion."""
        q = [
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w,
        ]
        _, _, yaw = tft.euler_from_quaternion(q)
        return yaw

    @staticmethod
    def _normalize_angle(angle):
        """Normaliza um ângulo para o intervalo [-pi, pi]."""
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def sync_callback(self, filtered_msg, gt_msg):
        """Callback sincronizado para calcular erros entre estimativa e ground truth."""
        if self.start_time is None:
            self.start_time = rospy.Time.now()
            # Guardar o Ground Truth inicial para alinhar o referencial
            self.x_gt_init = gt_msg.pose.pose.position.x
            self.y_gt_init = gt_msg.pose.pose.position.y
            self.yaw_gt_init = self._yaw_from_quaternion(gt_msg.pose.pose.orientation)

        t = (rospy.Time.now() - self.start_time).to_sec()

        # Posições estimadas
        x_est = filtered_msg.pose.pose.position.x
        y_est = filtered_msg.pose.pose.position.y
        yaw_est = self._yaw_from_quaternion(filtered_msg.pose.pose.orientation)

        # Ground Truth Bruto
        raw_x_gt = gt_msg.pose.pose.position.x
        raw_y_gt = gt_msg.pose.pose.position.y
        raw_yaw_gt = self._yaw_from_quaternion(gt_msg.pose.pose.orientation)

        # Translação relativa ao ponto inicial
        dx = raw_x_gt - self.x_gt_init
        dy = raw_y_gt - self.y_gt_init

        # Rotação para alinhar com o frame inicial (yaw_gt_init = 0)
        cos_theta = math.cos(-self.yaw_gt_init)
        sin_theta = math.sin(-self.yaw_gt_init)
        
        x_gt = dx * cos_theta - dy * sin_theta
        y_gt = dx * sin_theta + dy * cos_theta
        yaw_gt = self._normalize_angle(raw_yaw_gt - self.yaw_gt_init)

        # Erro de posição
        pos_error = math.sqrt((x_est - x_gt) ** 2 + (y_est - y_gt) ** 2)

        # Erro de orientação (normalizado)
        yaw_error = self._normalize_angle(yaw_est - yaw_gt)

        # Armazenar dados
        self.timestamps.append(t)
        self.x_est_list.append(x_est)
        self.y_est_list.append(y_est)
        self.yaw_est_list.append(yaw_est)
        self.x_gt_list.append(x_gt)
        self.y_gt_list.append(y_gt)
        self.yaw_gt_list.append(yaw_gt)
        self.pos_errors.append(pos_error)
        self.yaw_errors.append(yaw_error)

        # Log periódico
        if len(self.pos_errors) % 100 == 0:
            rospy.loginfo(
                "[%s] Amostras: %d | Erro pos. atual: %.4f m | Erro yaw atual: %.2f°",
                self.config_name,
                len(self.pos_errors),
                pos_error,
                math.degrees(abs(yaw_error)),
            )

    def on_shutdown(self):
        """Calcula e exibe métricas finais ao encerrar o nó."""
        n = len(self.pos_errors)
        if n == 0:
            rospy.logwarn("Nenhuma amostra coletada. Não há métricas para exibir.")
            return

        # Calcular métricas
        mean_pos_error = sum(self.pos_errors) / n
        rmse = math.sqrt(sum(e ** 2 for e in self.pos_errors) / n)
        max_pos_error = max(self.pos_errors)
        final_pos_error = self.pos_errors[-1]

        abs_yaw_errors = [abs(e) for e in self.yaw_errors]
        mean_yaw_error_deg = math.degrees(sum(abs_yaw_errors) / n)
        max_yaw_error_deg = math.degrees(max(abs_yaw_errors))

        # Exibir resumo formatado
        rospy.loginfo("")
        rospy.loginfo("=" * 50)
        rospy.loginfo("  RESUMO DE MÉTRICAS - %s", self.config_name.upper())
        rospy.loginfo("=" * 50)
        rospy.loginfo("  %-30s %10.4f m", "Erro médio de posição:", mean_pos_error)
        rospy.loginfo("  %-30s %10.4f m", "RMSE de posição:", rmse)
        rospy.loginfo("  %-30s %10.4f m", "Erro máximo de posição:", max_pos_error)
        rospy.loginfo("  %-30s %10.4f m", "Erro final de posição:", final_pos_error)
        rospy.loginfo(
            "  %-30s %10.4f°", "Erro médio de orientação:", mean_yaw_error_deg
        )
        rospy.loginfo(
            "  %-30s %10.4f°", "Erro máximo de orientação:", max_yaw_error_deg
        )
        rospy.loginfo("  %-30s %10d", "Total de amostras:", n)
        rospy.loginfo("=" * 50)

        # Salvar métricas resumidas em CSV
        metrics_file = os.path.join(
            self.results_dir, '{}_metrics.csv'.format(self.config_name)
        )
        try:
            with open(metrics_file, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['metric', 'value'])
                writer.writerow(['mean_pos_error', '{:.6f}'.format(mean_pos_error)])
                writer.writerow(['rmse', '{:.6f}'.format(rmse)])
                writer.writerow(['max_pos_error', '{:.6f}'.format(max_pos_error)])
                writer.writerow(['final_pos_error', '{:.6f}'.format(final_pos_error)])
                writer.writerow(
                    ['mean_yaw_error_deg', '{:.6f}'.format(mean_yaw_error_deg)]
                )
                writer.writerow(
                    ['max_yaw_error_deg', '{:.6f}'.format(max_yaw_error_deg)]
                )
                writer.writerow(['total_samples', str(n)])
            rospy.loginfo("Métricas salvas em: %s", metrics_file)
        except IOError as e:
            rospy.logerr("Erro ao salvar métricas: %s", str(e))

        # Salvar série temporal em CSV
        timeseries_file = os.path.join(
            self.results_dir, '{}_timeseries.csv'.format(self.config_name)
        )
        try:
            with open(timeseries_file, 'w') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'x_est', 'y_est', 'yaw_est',
                    'x_gt', 'y_gt', 'yaw_gt', 'pos_error', 'yaw_error'
                ])
                for i in range(n):
                    writer.writerow([
                        '{:.6f}'.format(self.timestamps[i]),
                        '{:.6f}'.format(self.x_est_list[i]),
                        '{:.6f}'.format(self.y_est_list[i]),
                        '{:.6f}'.format(self.yaw_est_list[i]),
                        '{:.6f}'.format(self.x_gt_list[i]),
                        '{:.6f}'.format(self.y_gt_list[i]),
                        '{:.6f}'.format(self.yaw_gt_list[i]),
                        '{:.6f}'.format(self.pos_errors[i]),
                        '{:.6f}'.format(self.yaw_errors[i]),
                    ])
            rospy.loginfo("Série temporal salva em: %s", timeseries_file)
        except IOError as e:
            rospy.logerr("Erro ao salvar série temporal: %s", str(e))

    def run(self):
        """Mantém o nó em execução."""
        rospy.spin()


if __name__ == '__main__':
    try:
        node = MetricsEvaluator()
        node.run()
    except rospy.ROSInterruptException:
        pass
