-- MySQL dump 10.13  Distrib 9.5.0, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: toplabel_pendientes_prod
-- ------------------------------------------------------
-- Server version	9.5.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `bitacora_tareas`
--

DROP TABLE IF EXISTS `bitacora_tareas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bitacora_tareas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tarea_id` int NOT NULL,
  `usuario_id` int NOT NULL,
  `comentario` text NOT NULL,
  `tipo` enum('AVANCE','BLOQUEO','CAMBIO_ESTATUS','NOTA_REUNION') DEFAULT 'AVANCE',
  `fecha_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `tarea_id` (`tarea_id`),
  KEY `usuario_id` (`usuario_id`),
  CONSTRAINT `bitacora_tareas_ibfk_1` FOREIGN KEY (`tarea_id`) REFERENCES `tareas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `bitacora_tareas_ibfk_2` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bitacora_tareas`
--

LOCK TABLES `bitacora_tareas` WRITE;
/*!40000 ALTER TABLE `bitacora_tareas` DISABLE KEYS */;
/*!40000 ALTER TABLE `bitacora_tareas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pilares`
--

DROP TABLE IF EXISTS `pilares`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pilares` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  `descripcion` varchar(150) DEFAULT NULL,
  `color_identificador` varchar(7) DEFAULT '#2563eb',
  `responsable_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`),
  KEY `fk_pilar_responsable` (`responsable_id`),
  CONSTRAINT `fk_pilar_responsable` FOREIGN KEY (`responsable_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pilares`
--

LOCK TABLES `pilares` WRITE;
/*!40000 ALTER TABLE `pilares` DISABLE KEYS */;
INSERT INTO `pilares` VALUES (1,'Calidad','Aseguramiento, inspección y pruebas de producto terminado','#059669',4),(2,'Diseño','Pre-prensa, diseño gráfico y preparación de originales','#8b5cf6',8),(3,'Procesos','Estandarización, matriz de habilidades y optimización de flujos','#4b5563',NULL),(4,'Producción','Área de prensas, impresión Flexo y Textil','#e11d48',5),(5,'Recursos Humanos','Atracción de talento, capacitación y desarrollo organizacional','#d97706',3),(6,'SAC','Servicio y Atención a Clientes, seguimiento a O.P.s y pedidos','#0891b2',6),(7,'Sistemas','Infraestructura TI, software de planta y redes','#2563eb',7),(8,'Mantenimiento','Mantenimiento preventivo y correctivo de maquinaria de planta','#ea580c',5),(9,'Dirección','','#000000',2);
/*!40000 ALTER TABLE `pilares` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tareas`
--

DROP TABLE IF EXISTS `tareas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tareas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo_folio` varchar(20) DEFAULT NULL,
  `titulo` varchar(200) NOT NULL,
  `descripcion` text,
  `pilar_id` int NOT NULL,
  `responsable_id` int NOT NULL,
  `creado_por_id` int NOT NULL,
  `prioridad` enum('P0_CRITICA','P1_ALTA','P2_MEDIA','P3_BAJA') DEFAULT 'P2_MEDIA',
  `estatus` enum('PENDIENTE','EN_PROCESO','BLOQUEADO','COMPLETADO','CANCELADO') DEFAULT 'PENDIENTE',
  `fecha_inicio` date NOT NULL,
  `fecha_compromiso` date NOT NULL,
  `fecha_cierre` date DEFAULT NULL,
  `fuente` varchar(30) DEFAULT 'DIRECCION',
  `pilar_dependencia_id` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo_folio` (`codigo_folio`),
  KEY `pilar_id` (`pilar_id`),
  KEY `responsable_id` (`responsable_id`),
  KEY `creado_por_id` (`creado_por_id`),
  KEY `pilar_dependencia_id` (`pilar_dependencia_id`),
  CONSTRAINT `tareas_ibfk_1` FOREIGN KEY (`pilar_id`) REFERENCES `pilares` (`id`),
  CONSTRAINT `tareas_ibfk_2` FOREIGN KEY (`responsable_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `tareas_ibfk_3` FOREIGN KEY (`creado_por_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `tareas_ibfk_4` FOREIGN KEY (`pilar_dependencia_id`) REFERENCES `pilares` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tareas`
--

LOCK TABLES `tareas` WRITE;
/*!40000 ALTER TABLE `tareas` DISABLE KEYS */;
INSERT INTO `tareas` VALUES (1,'TL-MANT-001','Sellar base de dren de agua en zona Flexo','Eliminar cualquier suciedad a sello de la base para sustituirlo por un silicon adecuado',8,11,1,'P2_MEDIA','PENDIENTE','2026-09-14','2026-09-15',NULL,'DIRECCION',NULL,'2026-09-15 04:22:05','2026-09-15 04:22:05'),(2,'TL-PROC-001','Proceso nivel 3 del area de pegado maquina Rolan','Se realizaran todos los procedimientos necesarios nivel 3 de todos los integrantes y procesos del area de pegado maquina Rolan. Notificar avances diarios',3,10,1,'P1_ALTA','PENDIENTE','2026-09-14','2026-09-30',NULL,'DIRECCION',NULL,'2026-09-15 04:28:16','2026-09-15 04:28:16'),(3,'TL-SIST-001','Colocar un sensor de apertura en puerta lateral Nave 35','Colocar un sensor de puerta abierta y un panel con clave, para que la puerta peatonal lateral de la nave 35 se mantenga siempre cerrada y solo personas con clave puedan abrirla.',7,7,1,'P2_MEDIA','PENDIENTE','2026-09-14','2026-10-09',NULL,'DIRECCION',8,'2026-09-15 06:02:47','2026-09-15 06:02:47');
/*!40000 ALTER TABLE `tareas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre_completo` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `rol` varchar(20) DEFAULT 'COLABORADOR',
  `es_responsable` tinyint(1) DEFAULT '0',
  `pilar_id` int DEFAULT NULL,
  `activo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `pilar_id` (`pilar_id`),
  CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`pilar_id`) REFERENCES `pilares` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,'Administrador Principal','admin_pilares',NULL,'scrypt:32768:8:1$aBfaqpOluTTEe6YX$d38d39d1c5b63492184d25a8822ec4887811cfada990e356d4d517e7240a5475972f2bd0ec706da8eb68a4e0ea80f3254dcad6e1fac7a594f78b9be4e849b4e4','DIRECCION',0,NULL,1),(2,'Leonardo Tamez','leonardota','leonardotamez@toplabel.com.mx','scrypt:32768:8:1$mCGycJdS0rwETMS8$565904103c4f5f853b1a7094a1f6c1a3002325da29fc0118dc13b3f00e0cd627cc86846816dbb52cc38c41856f0d3e184d325d1b8a795809a0169c4dcb0d1687','DIRECCION',1,9,1),(3,'Claudia Flores','claudiafr767','recursoshumanos@toplabel.com.mx','scrypt:32768:8:1$39riyX8AYyNBs54q$be677e454fa6f25052ffffefd1441c551bcf5a113aa3f6ac3b278d686c091442c3729afa711f70c36c9104924e99c84a8a2031c1aba4ab0438c9255c24b9336a','LIDER_PILAR',1,5,1),(4,'Alexis Uriarte','alexisfu','calidad2@toplabel.com.mx','scrypt:32768:8:1$G6gudhPHerws7tpF$fdf94231d93457ef1432e346a1958fcc7e2ae9c1437fd8ae3f703766df03d7eb0f6c24e4e29eef825fcab2d42610563925feac069ea37ff06fe2961ecd543569','LIDER_PILAR',1,1,1),(5,'Juan Muñoz','juanmf2507','juanmunoz@toplabel.com.mx','scrypt:32768:8:1$vLqmP31C4YsCXp3y$b5debb52ee1a63bb2a9c22f41ccb4960a2d05db799cad7900ad0ba10860d9aa2ca4f10e257c03712d4e6851f71d449af81da4616ca6c2c389926004dd0381651','LIDER_PILAR',1,8,1),(6,'Maria Hernandez (Lu)','mariahe365','mariahernandez@toplabel.com.mx','scrypt:32768:8:1$dS9xbJ36a72fBwEX$1a8068e56a564f9a0a4c16cf30a4a115340a466f35a8af9b4ce1325c10c3d6cca467c18b093c007e1c9edc467f6550dff2ae18d24a39d3bd33cc00f268a2a0e9','LIDER_PILAR',1,6,1),(7,'Tadeo Mejia','tadeomn879','ti@toplabel.com.mx','scrypt:32768:8:1$wJo24SWwa5yJSL5u$90fcc442b3986cdf68e2a3d340d08951d8651382384217da45d124c731258c5a36db198b7171dc9d8aaeb16cb753f051c51c10cafdd28de75262b47ef40aa4b5','LIDER_PILAR',1,7,1),(8,'Emmanel Zepeda (Mane)','emmanuelsz78','producciondigital@toplabel.com.mx','scrypt:32768:8:1$jFSVYh4ubZjUBpY3$dd0a104aa53feab2373ddb317fb628190bc74bfecabdc155d8103c8ccda8b04887cd7adb3df00b587dc2a63a80a069c7fdd9daa4eaae4d16c8c7a7c986d6ba09','LIDER_PILAR',1,2,1),(9,'Pamela Peña','pamelapm','procesos01@toplabel.com.mx','scrypt:32768:8:1$jGJfeMZmNv3xcA39$d94bd2dddcf8abdda61ec6c0f91cc6d6d603067b5badaac36681168900d3dd308361dbfc71bb2ad70728429cc0dcbacab9dc3f039f871c1d9c0ff1629a290158','COLABORADOR',0,3,1),(10,'Braulio Santiago','brauliosr954','procesos02@toplabel.com.mx','scrypt:32768:8:1$og2soCn67lXoFSCF$3da6ff633df3bf5a403f05b5ae5f48e2189a9ab3592131e1356609d1382eabdb09f2b39aba6f263d47cab0da02883f1e23b455f240b2e8c21d318e4c8f34b124','COLABORADOR',0,3,1),(11,'Cristal Valdez','cristalvl664','comprasqro@toplabel.com.mx','scrypt:32768:8:1$PY7kzh4TJ2apAaTl$4c5be7fc65238a001d37faa73d2f4bfc0479554a7f993d1d02f443a1865224d1bfa56f584d5cc7ddef64823569f667c283844b1ea439941c25a444be8ff3ee2a','COLABORADOR',0,NULL,1),(12,'Elizabeth de Jesus','elizabethjr521','seguridad@toplabel.com.mx','scrypt:32768:8:1$sj8effcX3htTzyuF$b6db33697b1ddd2d6268aabb8c48e9bfa288761fdbd77b898b94508a78839d320bc363ce6eef6bcba6f4e758ccdc718a545bc279acd8f094204f46b853dc6e48','COLABORADOR',0,NULL,1),(13,'Gustavo Hernandez','gustavohdz','gustavohdz@toplabel.com.mx','scrypt:32768:8:1$nJNc8MnLeuFEUq3a$e3fe9a04412cb8bfa3223e010b0b7e10592a0c4eb70647b8aa0333de14f46c5c998ef574f81de344aca50c89f40fc0bee1ab8b6c9dae973a9a0ea184c2a8751e','COLABORADOR',0,NULL,1),(14,'Angel Riveroll','angelrm884','desarrolloemp@toplabel.com.mx','scrypt:32768:8:1$18U393gP5cK6Bok6$cb710cb3f54ec2f6c193eec0544cd201be90abad8abdaecbe410d1b51d1c005c7113ef8d81e9516e045d5b370829c2b96ab573f28712f8b5a5dff5924768b933','COLABORADOR',0,NULL,1),(15,'Abraham Cabrera','abrahamcc936',NULL,'scrypt:32768:8:1$cF4eAy4EGMqyLtZh$20d7d9b2d5588692b8a1c99979c7d0663c854782c7a0865c64dd746d5fd9cead03637fa67123072ae8debd7395a299c07abf69657ef5601cb570fb870ac767d5','COLABORADOR',0,NULL,1),(16,'Fernando Flores','fernandofg',NULL,'scrypt:32768:8:1$mbuDH59qFSGtR6S8$cb47298cdf6b9b29815df011df0e0db14732ae5716641dfd7d169e7835ef390681b66ae8fb0dc73b0555f6e1fb41195ba4e69759159abdc97357101a85904a69','COLABORADOR',0,7,1),(17,'Tania Hernandez','taniahm42','facturacionqro@toplabel.com.mx','scrypt:32768:8:1$y3DQVyV92a1u8ZqU$fb58a48a53eb896a40b8a8b6e49ab9bb2da230f17a2e51f09c306b4f608dc939f668d8522a464f918501bad0770f2e578000a595f3333d3a24f40282d5b84f29','COLABORADOR',0,NULL,1),(18,'Ana Cardiel','anacc975',NULL,'scrypt:32768:8:1$jr9sY9wqI3hJ2j4E$f0cb4a3628ca04b1bca36f3ca1be5c98d521d5fa074bda17240b4529533979b6d9b89898af355d55801dae537d330f9ae1c59483cc3c0e01804a1795a5471dcf','COLABORADOR',0,NULL,1),(19,'Gloriela Jasso','glorielajm4','cobranza@toplabel.com.mx','scrypt:32768:8:1$2LeTgaC42yQudQVn$f146d34d6d086b9085a0b8a495b76cb1114bc7568b3b4ccd16c167bbbde4d93cb3ed9b97c0baced22e39d000f7a369abf1230ebd1208e98ea744bcef17e84ec2','COLABORADOR',0,NULL,1);
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'toplabel_pendientes_prod'
--

--
-- Dumping routines for database 'toplabel_pendientes_prod'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-14 18:35:17
