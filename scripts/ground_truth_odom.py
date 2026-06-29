#!/usr/bin/env python3
"""
Nó ROS para publicação da odometria de referência (ground truth) do Gazebo.

Subscreve ao tópico /gazebo/model_states e extrai a pose do modelo 'husky',
publicando-a como nav_msgs/Odometry no tópico /gt/odom a ~50Hz.
"""

import rospy
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry


class GroundTruthOdom:
    """Classe que publica a pose do modelo Husky como ground truth."""

    def __init__(self):
        rospy.init_node('ground_truth_odom', anonymous=False)

        self.model_name = 'husky'
        self.current_pose = None
        self.current_twist = None
        self.model_found = False

        self.pub = rospy.Publisher('/gt/odom', Odometry, queue_size=10)
        self.sub = rospy.Subscriber(
            '/gazebo/model_states', ModelStates, self.model_states_callback
        )

        # Timer para publicar a ~50Hz
        publish_rate = 50.0  # Hz
        self.timer = rospy.Timer(
            rospy.Duration(1.0 / publish_rate), self.publish_callback
        )

        rospy.loginfo(
            "Nó ground_truth_odom iniciado. Procurando modelo '%s' no Gazebo...",
            self.model_name,
        )

    def model_states_callback(self, msg):
        """Callback para capturar a pose do modelo Husky do Gazebo."""
        try:
            idx = msg.name.index(self.model_name)
        except ValueError:
            if not self.model_found:
                rospy.logwarn_throttle(
                    5.0,
                    "Modelo '%s' ainda não encontrado no Gazebo.",
                    self.model_name,
                )
            return

        if not self.model_found:
            self.model_found = True
            rospy.loginfo("Modelo '%s' encontrado no Gazebo.", self.model_name)

        self.current_pose = msg.pose[idx]
        self.current_twist = msg.twist[idx]

    def publish_callback(self, event):
        """Timer callback para publicar a odometria de ground truth."""
        if self.current_pose is None:
            return

        odom = Odometry()
        odom.header.stamp = rospy.Time.now()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'

        odom.pose.pose = self.current_pose
        odom.twist.twist = self.current_twist

        self.pub.publish(odom)

    def run(self):
        """Mantém o nó em execução."""
        rospy.spin()


if __name__ == '__main__':
    try:
        node = GroundTruthOdom()
        node.run()
    except rospy.ROSInterruptException:
        pass
