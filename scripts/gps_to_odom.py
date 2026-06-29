#!/usr/bin/env python3
"""
Nó ROS para conversão de coordenadas GPS (lat/lon) para odometria local (x/y).

Subscreve ao tópico /fix (sensor_msgs/NavSatFix) e converte as coordenadas
GPS para um referencial local utilizando a primeira leitura como origem.
Publica a odometria resultante no tópico /gps/odom (nav_msgs/Odometry).
"""

import math
import rospy
from sensor_msgs.msg import NavSatFix
from nav_msgs.msg import Odometry


class GpsToOdom:
    """Classe que converte dados GPS para odometria local."""

    def __init__(self):
        rospy.init_node('gps_to_odom', anonymous=False)

        # Origem GPS (primeira leitura recebida)
        self.origin_lat = None
        self.origin_lon = None
        self.origin_lat_rad = None

        self.pub = rospy.Publisher('/gps/odom', Odometry, queue_size=10)
        self.sub = rospy.Subscriber('/fix', NavSatFix, self.gps_callback)

        rospy.loginfo("Nó gps_to_odom iniciado. Aguardando dados GPS em /fix...")

    def gps_callback(self, msg):
        """Callback para processar mensagens GPS e publicar odometria local."""
        # Ignorar leituras inválidas (status < 0 indica sem fix)
        if msg.status.status < 0:
            rospy.logwarn_throttle(5.0, "GPS sem fix válido, ignorando leitura.")
            return

        lat = msg.latitude
        lon = msg.longitude

        # Armazenar a primeira leitura como origem
        if self.origin_lat is None:
            self.origin_lat = lat
            self.origin_lon = lon
            self.origin_lat_rad = math.radians(lat)
            rospy.loginfo(
                "Origem GPS definida: lat=%.7f, lon=%.7f", lat, lon
            )

        # Calcular coordenadas locais relativas à origem
        dx = (lon - self.origin_lon) * math.cos(self.origin_lat_rad) * 111320.0
        dy = (lat - self.origin_lat) * 111320.0

        # Montar mensagem de odometria
        odom = Odometry()
        odom.header.stamp = rospy.Time.now()
        odom.header.frame_id = 'map'
        odom.child_frame_id = 'base_link'

        odom.pose.pose.position.x = dx
        odom.pose.pose.position.y = dy
        odom.pose.pose.position.z = 0.0

        # Orientação neutra (quaternion identidade)
        odom.pose.pose.orientation.x = 0.0
        odom.pose.pose.orientation.y = 0.0
        odom.pose.pose.orientation.z = 0.0
        odom.pose.pose.orientation.w = 1.0

        # Covariância da pose (6x6, row-major)
        # Diagonal: [x, y, z, rot_x, rot_y, rot_z]
        odom.pose.covariance = [0.0] * 36
        odom.pose.covariance[0] = 2.0       # x
        odom.pose.covariance[7] = 2.0       # y
        odom.pose.covariance[14] = 99999.0  # z (incerteza muito alta)
        odom.pose.covariance[21] = 99999.0  # rot_x
        odom.pose.covariance[28] = 99999.0  # rot_y
        odom.pose.covariance[35] = 99999.0  # rot_z

        self.pub.publish(odom)

    def run(self):
        """Mantém o nó em execução."""
        rospy.spin()


if __name__ == '__main__':
    try:
        node = GpsToOdom()
        node.run()
    except rospy.ROSInterruptException:
        pass
