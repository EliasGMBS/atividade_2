cmake_minimum_required(VERSION 3.0.2)
project(atividade_2)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  nav_msgs
  sensor_msgs
  geometry_msgs
  tf
  robot_localization
  message_filters
  gazebo_msgs
)

catkin_package(
  CATKIN_DEPENDS
    rospy
    std_msgs
    nav_msgs
    sensor_msgs
    geometry_msgs
    tf
    robot_localization
    message_filters
    gazebo_msgs
)

catkin_install_python(PROGRAMS
  scripts/metrics_evaluator.py
  scripts/gps_to_odom.py
  scripts/ground_truth_odom.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
