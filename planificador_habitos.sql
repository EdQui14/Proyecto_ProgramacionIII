-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 20-07-2026 a las 19:40:45
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `planificador_habitos`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `habitos`
--

CREATE TABLE `habitos` (
  `id` int(11) NOT NULL,
  `usuario_id` int(11) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `categoria` varchar(60) NOT NULL,
  `frecuencia` varchar(60) NOT NULL,
  `completado_hoy` tinyint(1) NOT NULL DEFAULT 0,
  `fecha_registro` date NOT NULL,
  `racha` int(11) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `habitos`
--

INSERT INTO `habitos` (`id`, `usuario_id`, `nombre`, `categoria`, `frecuencia`, `completado_hoy`, `fecha_registro`, `racha`) VALUES
(2, 1, 'Tareas', 'Estudio', 'Diario', 0, '2026-07-20', 0),
(4, 1, 'Ejercicio', 'Salud', 'Diario', 0, '2026-07-20', 0);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `logros_usuario`
--

CREATE TABLE `logros_usuario` (
  `id` int(11) NOT NULL,
  `usuario_id` int(11) NOT NULL,
  `logro_codigo` varchar(60) NOT NULL,
  `fecha_desbloqueo` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `logros_usuario`
--

INSERT INTO `logros_usuario` (`id`, `usuario_id`, `logro_codigo`, `fecha_desbloqueo`) VALUES
(1, 1, 'primer_habito', '2026-07-20 11:14:49');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `subtareas`
--

CREATE TABLE `subtareas` (
  `id` int(11) NOT NULL,
  `habito_id` int(11) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `completado` tinyint(1) NOT NULL DEFAULT 0,
  `orden` int(11) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `subtareas`
--

INSERT INTO `subtareas` (`id`, `habito_id`, `nombre`, `completado`, `orden`) VALUES
(3, 2, 'tarea programacion', 0, 0),
(4, 2, 'tarea de metodologia', 0, 1),
(5, 4, 'Pierna', 0, 0),
(6, 4, 'pecho', 0, 1),
(7, 4, 'hombro', 0, 2);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `nombre` varchar(120) NOT NULL,
  `usuario` varchar(60) NOT NULL,
  `contrasena_hash` varchar(255) NOT NULL,
  `foto_perfil` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `usuarios`
--

INSERT INTO `usuarios` (`id`, `nombre`, `usuario`, `contrasena_hash`, `foto_perfil`) VALUES
(1, 'Edson Quintana', 'Ed', '$2b$12$NgDm1ALjx13tRg89TGOv3emKtW8kUz5FJFAy15P9wUgdzTu4A3yXW', 'c:\\Users\\edson\\Documents\\escuela\\programacion III\\Proyecto\\assets\\fotos\\Ed.jpg');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `habitos`
--
ALTER TABLE `habitos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `usuario_id` (`usuario_id`);

--
-- Indices de la tabla `logros_usuario`
--
ALTER TABLE `logros_usuario`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unico_logro_usuario` (`usuario_id`,`logro_codigo`);

--
-- Indices de la tabla `subtareas`
--
ALTER TABLE `subtareas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `habito_id` (`habito_id`);

--
-- Indices de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `usuario` (`usuario`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `habitos`
--
ALTER TABLE `habitos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `logros_usuario`
--
ALTER TABLE `logros_usuario`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `subtareas`
--
ALTER TABLE `subtareas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `habitos`
--
ALTER TABLE `habitos`
  ADD CONSTRAINT `habitos_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `logros_usuario`
--
ALTER TABLE `logros_usuario`
  ADD CONSTRAINT `logros_usuario_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `subtareas`
--
ALTER TABLE `subtareas`
  ADD CONSTRAINT `subtareas_ibfk_1` FOREIGN KEY (`habito_id`) REFERENCES `habitos` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
