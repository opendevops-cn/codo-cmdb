/*
 Navicat MySQL Data Transfer

 Source Server         : Codo-Demo
 Source Server Type    : MySQL
 Source Server Version : 50724
 Source Schema         : cmdb

 Target Server Type    : MySQL
 Target Server Version : 50724
 File Encoding         : 65001

 Date: 04/01/2019 16:09:30
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for assets_adminuser
-- ----------------------------
DROP TABLE IF EXISTS `assets_adminuser`;
CREATE TABLE `assets_adminuser` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `private_key` longtext COLLATE utf8mb4_unicode_ci,
  `comment` longtext COLLATE utf8mb4_unicode_ci,
  `create_at` datetime(6) NOT NULL,
  `update_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_book
-- ----------------------------
DROP TABLE IF EXISTS `assets_book`;
CREATE TABLE `assets_book` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `publisher_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `assets_book_publisher_id_bccf8a29_fk_assets_publisher_id` (`publisher_id`),
  CONSTRAINT `assets_book_publisher_id_bccf8a29_fk_assets_publisher_id` FOREIGN KEY (`publisher_id`) REFERENCES `assets_publisher` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_dbserver
-- ----------------------------
DROP TABLE IF EXISTS `assets_dbserver`;
CREATE TABLE `assets_dbserver` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `host` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `port` int(11) DEFAULT NULL,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idc` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `db_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `db_version` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comment` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `role` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `host` (`host`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_dbserver_group
-- ----------------------------
DROP TABLE IF EXISTS `assets_dbserver_group`;
CREATE TABLE `assets_dbserver_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dbserver_id` int(11) NOT NULL,
  `servergroup_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assets_dbserver_group_dbserver_id_servergroup_id_8b889ea3_uniq` (`dbserver_id`,`servergroup_id`),
  KEY `assets_dbserver_grou_servergroup_id_bbfbd520_fk_assets_se` (`servergroup_id`),
  CONSTRAINT `assets_dbserver_grou_servergroup_id_bbfbd520_fk_assets_se` FOREIGN KEY (`servergroup_id`) REFERENCES `assets_servergroup` (`id`),
  CONSTRAINT `assets_dbserver_group_dbserver_id_e5b4966c_fk_assets_dbserver_id` FOREIGN KEY (`dbserver_id`) REFERENCES `assets_dbserver` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_dbserver_tag
-- ----------------------------
DROP TABLE IF EXISTS `assets_dbserver_tag`;
CREATE TABLE `assets_dbserver_tag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dbserver_id` int(11) NOT NULL,
  `tag_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assets_dbserver_tag_dbserver_id_tag_id_82952c1d_uniq` (`dbserver_id`,`tag_id`),
  KEY `assets_dbserver_tag_tag_id_9d0a001a_fk_assets_tag_id` (`tag_id`),
  CONSTRAINT `assets_dbserver_tag_dbserver_id_408a0981_fk_assets_dbserver_id` FOREIGN KEY (`dbserver_id`) REFERENCES `assets_dbserver` (`id`),
  CONSTRAINT `assets_dbserver_tag_tag_id_9d0a001a_fk_assets_tag_id` FOREIGN KEY (`tag_id`) REFERENCES `assets_tag` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_log
-- ----------------------------
DROP TABLE IF EXISTS `assets_log`;
CREATE TABLE `assets_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `host` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remote_ip` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `login_type` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `record_name` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=122 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_publisher
-- ----------------------------
DROP TABLE IF EXISTS `assets_publisher`;
CREATE TABLE `assets_publisher` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `operator_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `assets_publisher_operator_id_b7b68402_fk_auth_user_id` (`operator_id`),
  CONSTRAINT `assets_publisher_operator_id_b7b68402_fk_auth_user_id` FOREIGN KEY (`operator_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_recorderlog
-- ----------------------------
DROP TABLE IF EXISTS `assets_recorderlog`;
CREATE TABLE `assets_recorderlog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `data` longtext COLLATE utf8mb4_unicode_ci,
  `log_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `assets_recorderlog_log_id_50a42485_fk_assets_log_id` (`log_id`),
  CONSTRAINT `assets_recorderlog_log_id_50a42485_fk_assets_log_id` FOREIGN KEY (`log_id`) REFERENCES `assets_log` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_server
-- ----------------------------
DROP TABLE IF EXISTS `assets_server`;
CREATE TABLE `assets_server` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `hostname` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ip` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `port` int(11) DEFAULT NULL,
  `idc` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cpu` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `memory` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disk` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `os_platform` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `os_distribution` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `os_version` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sn` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comment` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_at` datetime(6) NOT NULL,
  `update_at` datetime(6) NOT NULL,
  `admin_user_id` int(11) DEFAULT NULL,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `public_key` tinyint(1),
  PRIMARY KEY (`id`),
  UNIQUE KEY `hostname` (`hostname`),
  KEY `assets_server_admin_user_id_a5768e2c_fk_assets_adminuser_id` (`admin_user_id`),
  CONSTRAINT `assets_server_admin_user_id_a5768e2c_fk_assets_adminuser_id` FOREIGN KEY (`admin_user_id`) REFERENCES `assets_adminuser` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_server_group
-- ----------------------------
DROP TABLE IF EXISTS `assets_server_group`;
CREATE TABLE `assets_server_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `server_id` int(11) NOT NULL,
  `servergroup_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assets_server_group_server_id_servergroup_id_fa38c6b1_uniq` (`server_id`,`servergroup_id`),
  KEY `assets_server_group_servergroup_id_361d4db5_fk_assets_se` (`servergroup_id`),
  CONSTRAINT `assets_server_group_server_id_9b0d5fe6_fk_assets_server_id` FOREIGN KEY (`server_id`) REFERENCES `assets_server` (`id`),
  CONSTRAINT `assets_server_group_servergroup_id_361d4db5_fk_assets_se` FOREIGN KEY (`servergroup_id`) REFERENCES `assets_servergroup` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_server_tag
-- ----------------------------
DROP TABLE IF EXISTS `assets_server_tag`;
CREATE TABLE `assets_server_tag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `server_id` int(11) NOT NULL,
  `tag_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assets_server_tag_server_id_tag_id_f7f134a5_uniq` (`server_id`,`tag_id`),
  KEY `assets_server_tag_tag_id_e9e21798_fk_assets_tag_id` (`tag_id`),
  CONSTRAINT `assets_server_tag_server_id_d316a370_fk_assets_server_id` FOREIGN KEY (`server_id`) REFERENCES `assets_server` (`id`),
  CONSTRAINT `assets_server_tag_tag_id_e9e21798_fk_assets_tag_id` FOREIGN KEY (`tag_id`) REFERENCES `assets_tag` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_serverauthrule
-- ----------------------------
DROP TABLE IF EXISTS `assets_serverauthrule`;
CREATE TABLE `assets_serverauthrule` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user` varchar(256) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comment` varchar(160) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_serverauthrule_server
-- ----------------------------
DROP TABLE IF EXISTS `assets_serverauthrule_server`;
CREATE TABLE `assets_serverauthrule_server` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `serverauthrule_id` int(11) NOT NULL,
  `server_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assets_serverauthrule_se_serverauthrule_id_server_009ce2c3_uniq` (`serverauthrule_id`,`server_id`),
  KEY `assets_serverauthrul_server_id_503dd3df_fk_assets_se` (`server_id`),
  CONSTRAINT `assets_serverauthrul_server_id_503dd3df_fk_assets_se` FOREIGN KEY (`server_id`) REFERENCES `assets_server` (`id`),
  CONSTRAINT `assets_serverauthrul_serverauthrule_id_76b392b3_fk_assets_se` FOREIGN KEY (`serverauthrule_id`) REFERENCES `assets_serverauthrule` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_serverauthrule_servergroup
-- ----------------------------
DROP TABLE IF EXISTS `assets_serverauthrule_servergroup`;
CREATE TABLE `assets_serverauthrule_servergroup` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `serverauthrule_id` int(11) NOT NULL,
  `servergroup_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assets_serverauthrule_se_serverauthrule_id_server_a8aabff8_uniq` (`serverauthrule_id`,`servergroup_id`),
  KEY `assets_serverauthrul_servergroup_id_45d69fa2_fk_assets_se` (`servergroup_id`),
  CONSTRAINT `assets_serverauthrul_serverauthrule_id_6d05e40e_fk_assets_se` FOREIGN KEY (`serverauthrule_id`) REFERENCES `assets_serverauthrule` (`id`),
  CONSTRAINT `assets_serverauthrul_servergroup_id_45d69fa2_fk_assets_se` FOREIGN KEY (`servergroup_id`) REFERENCES `assets_servergroup` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_servergroup
-- ----------------------------
DROP TABLE IF EXISTS `assets_servergroup`;
CREATE TABLE `assets_servergroup` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comment` varchar(160) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_tag
-- ----------------------------
DROP TABLE IF EXISTS `assets_tag`;
CREATE TABLE `assets_tag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for assets_ttylog
-- ----------------------------
DROP TABLE IF EXISTS `assets_ttylog`;
CREATE TABLE `assets_ttylog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `datetime` datetime(6) NOT NULL,
  `cmd` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `log_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `assets_ttylog_log_id_d4ae7312_fk_assets_log_id` (`log_id`),
  CONSTRAINT `assets_ttylog_log_id_d4ae7312_fk_assets_log_id` FOREIGN KEY (`log_id`) REFERENCES `assets_log` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=214 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for auth_group
-- ----------------------------
DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for auth_group_permissions
-- ----------------------------
DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE `auth_group_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for auth_permission
-- ----------------------------
DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=69 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for auth_user
-- ----------------------------
DROP TABLE IF EXISTS `auth_user`;
CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for auth_user_groups
-- ----------------------------
DROP TABLE IF EXISTS `auth_user_groups`;
CREATE TABLE `auth_user_groups` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for auth_user_user_permissions
-- ----------------------------
DROP TABLE IF EXISTS `auth_user_user_permissions`;
CREATE TABLE `auth_user_user_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for django_admin_log
-- ----------------------------
DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for django_content_type
-- ----------------------------
DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for django_migrations
-- ----------------------------
DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE `django_migrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for django_session
-- ----------------------------
DROP TABLE IF EXISTS `django_session`;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
