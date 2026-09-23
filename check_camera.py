"""
================================================================================
КАЛЬКУЛЯТОР ПОДБОРА КАМЕРЫ И ОСВЕЩЕНИЯ ДЛЯ ПРОМЫШЛЕННОГО КОМПЬЮТЕРНОГО ЗРЕНИЯ
================================================================================

ВОЗМОЖНОСТИ:
    - Подбор камеры по разрешению, затвору, FPS, интерфейсу, бюджету
    - Подбор объектива с проверкой совместимости (крепление, покрытие сенсора)
    - Расчёт угла обзора (HFOV, VFOV, DFOV)
    - Расчёт угла наклона камеры (tilt angle) и компенсации перспективы
    - Проверка FOV на всём поле (центр + края) с учётом перспективы
    - Расчёт глубины резкости (DOF)
    - Расчёт требуемой мощности освещения
    - Подбор конкретной модели освещения из расширенной базы
    - Проверка бюджета
    - Сравнение нескольких конфигураций (预设 / JSON-файл / JSON-строка)
    - Визуализация (FOV, DOF, бюджет, угол наклона) через matplotlib
    - Экспорт в PDF (с встроенными PNG) и CSV
    - GUI на Gradio
    - CLI через argparse с подробной справкой

УСТАНОВКА:
    pip install fpdf2 gradio matplotlib

ЗАПУСК:
    python check_camera.py                  # подробная справка
    python check_camera.py --help           # краткая справка argparse
    python check_camera.py [ОПЦИИ]          # одиночный расчёт
    python check_camera.py --gui            # веб-интерфейс
    python check_camera.py --compare        #预设 конфигурации
    python check_camera.py --compare-file configs.json
    python check_camera.py --compare-json '[...]'

АВТОР: Вадим Дорошенко
================================================================================
"""

import math
import csv
import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

# Для экспорта в PDF
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("ВНИМАНИЕ: fpdf2 не установлена. PDF не будет создан.")
    print("Установите: pip install fpdf2")

# Для GUI
try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

# Для визуализации
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ==============================================================================
# РАЗДЕЛ 1: СПРАВОЧНИКИ
# ==============================================================================

# ------------------------------------------------------------------------------
# 1.1 СТАНДАРТНЫЕ РАЗРЕШЕНИЯ СЕНСОРОВ
# ------------------------------------------------------------------------------
STANDARD_RESOLUTIONS = [
    (640, 480), (800, 600), (1280, 720), (1280, 1024),
    (1920, 1080), (2048, 1536), (2448, 2048), (2592, 1944),
    (3840, 2160), (4096, 3000), (5120, 5120), (5472, 3648), (8192, 5460),
]

# ------------------------------------------------------------------------------
# 1.2 РАЗМЕРЫ СЕНСОРОВ (физическая ширина в мм)
# ------------------------------------------------------------------------------
SENSOR_WIDTH_MM = {
    '1/4"': 3.2, '1/3"': 4.8, '1/2"': 6.4, '1/1.8"': 7.2,
    '2/3"': 8.8, '1"': 12.8, '1.1"': 14.1, '4/3"': 17.3,
    'APS-C': 23.6, 'Full Frame': 36.0, 'Medium Format': 53.7,
}
SENSOR_HEIGHT_RATIO = 0.75

# ------------------------------------------------------------------------------
# 1.3 УРОВНИ ВНЕШНЕГО ОСВЕЩЕНИЯ В ЦЕХУ (люкс)
# ------------------------------------------------------------------------------
AMBIENT_LIGHT_LUX = {
    'яркий цех (окна, солнце)': 1000,
    'обычный цех': 300,
    'тусклый цех': 100,
    'темнота (кожух)': 10,
}

# ------------------------------------------------------------------------------
# 1.4 КОЭФФИЦИЕНТЫ ОТРАЖЕНИЯ МАТЕРИАЛОВ
# ------------------------------------------------------------------------------
REFLECTIVITY_COEFFICIENT = {
    'матовая (резина, ткань)': 0.2,
    'полуматовая (пластик, краска)': 0.4,
    'глянцевая (металл, стекло)': 0.6,
    'зеркальная (полировка, хром)': 0.9,
}

# ------------------------------------------------------------------------------
# 1.5 ЧУВСТВИТЕЛЬНОСТЬ СЕНСОРА
# ------------------------------------------------------------------------------
SENSOR_SENSITIVITY = {
    'Global Shutter CMOS': 2.0,
    'Rolling Shutter CMOS': 3.0,
}

# ------------------------------------------------------------------------------
# 1.6 БАЗА ДАННЫХ КАМЕР
# ------------------------------------------------------------------------------
CAMERA_DATABASE = [
    # Basler
    {'model': 'acA640-750um', 'vendor': 'Basler', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 750,
     'interface': 'USB3', 'price_usd': 400},
    {'model': 'acA800-510um', 'vendor': 'Basler', 'resolution': (800, 600),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 510,
     'interface': 'USB3', 'price_usd': 450},
    {'model': 'acA1300-200um', 'vendor': 'Basler', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 200,
     'interface': 'USB3', 'price_usd': 600},
    {'model': 'acA1920-155um', 'vendor': 'Basler', 'resolution': (1920, 1080),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 155,
     'interface': 'USB3', 'price_usd': 800},
    {'model': 'acA2040-90um', 'vendor': 'Basler', 'resolution': (2048, 1536),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 90,
     'interface': 'USB3', 'price_usd': 1000},
    {'model': 'acA2440-75um', 'vendor': 'Basler', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 75,
     'interface': 'GigE', 'price_usd': 1200},
    {'model': 'acA2592-14um', 'vendor': 'Basler', 'resolution': (2592, 1944),
     'sensor_format': '1/2.5"', 'shutter': 'Rolling', 'max_fps': 14,
     'interface': 'GigE', 'price_usd': 700},
    {'model': 'acA4096-30um', 'vendor': 'Basler', 'resolution': (4096, 3000),
     'sensor_format': '1"', 'shutter': 'Global', 'max_fps': 30,
     'interface': '10GigE', 'price_usd': 3500},
    {'model': 'acA5472-17um', 'vendor': 'Basler', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 17,
     'interface': '10GigE', 'price_usd': 2800},
    {'model': 'boost boA5320-150cm', 'vendor': 'Basler', 'resolution': (5320, 4600),
     'sensor_format': '4/3"', 'shutter': 'Global', 'max_fps': 150,
     'interface': 'CoaXPress', 'price_usd': 8500},

    # FLIR
    {'model': 'BFS-U3-04S2M', 'vendor': 'FLIR', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 522,
     'interface': 'USB3', 'price_usd': 350},
    {'model': 'BFS-U3-13Y3M', 'vendor': 'FLIR', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 240,
     'interface': 'USB3', 'price_usd': 550},
    {'model': 'BFS-U3-20S4M', 'vendor': 'FLIR', 'resolution': (1920, 1080),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 163,
     'interface': 'USB3', 'price_usd': 750},
    {'model': 'BFS-PGE-31S4M', 'vendor': 'FLIR', 'resolution': (2048, 1536),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 51,
     'interface': 'GigE', 'price_usd': 1100},
    {'model': 'BFS-U3-51S5M', 'vendor': 'FLIR', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 75,
     'interface': 'USB3', 'price_usd': 1300},
    {'model': 'BFS-PGE-50S5M', 'vendor': 'FLIR', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 22,
     'interface': 'GigE', 'price_usd': 1050},
    {'model': 'BFS-U3-63S4M', 'vendor': 'FLIR', 'resolution': (3072, 2048),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 60,
     'interface': 'USB3', 'price_usd': 1600},
    {'model': 'BFS-U3-88S6M', 'vendor': 'FLIR', 'resolution': (4096, 3000),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 32,
     'interface': 'USB3', 'price_usd': 2200},
    {'model': 'BFS-PGE-120S6M', 'vendor': 'FLIR', 'resolution': (4096, 3000),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 9,
     'interface': 'GigE', 'price_usd': 1800},

    # Cognex
    {'model': 'In-Sight 2000', 'vendor': 'Cognex', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'price_usd': 1500},
    {'model': 'In-Sight 7000', 'vendor': 'Cognex', 'resolution': (1920, 1080),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'price_usd': 2500},
    {'model': 'In-Sight 8000', 'vendor': 'Cognex', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 30,
     'interface': 'GigE', 'price_usd': 3500},
    {'model': 'In-Sight 9000', 'vendor': 'Cognex', 'resolution': (4096, 3000),
     'sensor_format': '1"', 'shutter': 'Global', 'max_fps': 20,
     'interface': '10GigE', 'price_usd': 5500},

    # IDS
    {'model': 'UI-3060CP-M-GL', 'vendor': 'IDS', 'resolution': (1936, 1216),
     'sensor_format': '1/1.2"', 'shutter': 'Global', 'max_fps': 152,
     'interface': 'USB3', 'price_usd': 500},
    {'model': 'UI-3140CP-M-GL', 'vendor': 'IDS', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 198,
     'interface': 'USB3', 'price_usd': 400},
    {'model': 'UI-3280CP-M-GL', 'vendor': 'IDS', 'resolution': (1936, 1216),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 98,
     'interface': 'USB3', 'price_usd': 550},
    {'model': 'UI-3880CP-M-GL', 'vendor': 'IDS', 'resolution': (3088, 2076),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'USB3', 'price_usd': 900},

    # Hikrobot
    {'model': 'MV-CA003-20GM', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 200,
     'interface': 'GigE', 'price_usd': 200},
    {'model': 'MV-CA013-20GM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'price_usd': 280},
    {'model': 'MV-CA050-10GM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'price_usd': 550},
    {'model': 'MV-CA050-20UM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'USB3', 'price_usd': 500},
    {'model': 'MV-CA060-10GM', 'vendor': 'Hikrobot', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Rolling', 'max_fps': 30,
     'interface': 'GigE', 'price_usd': 600},
    {'model': 'MV-CA120-10GM', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'GigE', 'price_usd': 900},

    # Balluff
    {'model': 'BVS CA-GX0-004', 'vendor': 'Balluff', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 300,
     'interface': 'GigE', 'price_usd': 600},
    {'model': 'BVS CA-GX0-013', 'vendor': 'Balluff', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 100,
     'interface': 'GigE', 'price_usd': 900},
    {'model': 'BVS CA-GX0-050', 'vendor': 'Balluff', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 30,
     'interface': 'GigE', 'price_usd': 1500},

    # Teledyne DALSA
    {'model': 'Genie Nano C2020', 'vendor': 'Teledyne DALSA', 'resolution': (2048, 1536),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 100,
     'interface': 'GigE', 'price_usd': 1400},
    {'model': 'Genie Nano C4096', 'vendor': 'Teledyne DALSA', 'resolution': (4096, 3000),
     'sensor_format': '1"', 'shutter': 'Global', 'max_fps': 30,
     'interface': '10GigE', 'price_usd': 3800},
    {'model': 'Genie Nano C5100', 'vendor': 'Teledyne DALSA', 'resolution': (5120, 5120),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 15,
     'interface': 'CoaXPress', 'price_usd': 6500},
]

# ------------------------------------------------------------------------------
# 1.7 БАЗА ДАННЫХ ОБЪЕКТИВОВ
# ------------------------------------------------------------------------------
LENS_DATABASE = [
    {'model': 'Computar M0814-MP2', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 150},
    {'model': 'Computar M1214-MP2', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 160},
    {'model': 'Computar M1614-MP2', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 170},
    {'model': 'Computar M2514-MP2', 'focal_length_mm': 25, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 180},
    {'model': 'Computar M3514-MP2', 'focal_length_mm': 35, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 200},
    {'model': 'Computar M5028-MP2', 'focal_length_mm': 50, 'max_aperture': 2.8,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 220},
    {'model': 'Computar M7528-MP2', 'focal_length_mm': 75, 'max_aperture': 2.8,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 280},
    {'model': 'Kowa LM8HC', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 300},
    {'model': 'Kowa LM12HC', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 320},
    {'model': 'Kowa LM16HC', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 340},
    {'model': 'Kowa LM25HC', 'focal_length_mm': 25, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 360},
    {'model': 'Kowa LM35HC', 'focal_length_mm': 35, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 380},
    {'model': 'Kowa LM50HC', 'focal_length_mm': 50, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 420},
    {'model': 'Kowa LM75HC', 'focal_length_mm': 75, 'max_aperture': 1.8,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 480},
    {'model': 'Fujinon HF8XA-5M', 'focal_length_mm': 8, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 350},
    {'model': 'Fujinon HF12XA-5M', 'focal_length_mm': 12, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 380},
    {'model': 'Fujinon HF16XA-5M', 'focal_length_mm': 16, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 400},
    {'model': 'Fujinon HF25XA-5M', 'focal_length_mm': 25, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 450},
    {'model': 'Fujinon HF35XA-5M', 'focal_length_mm': 35, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 500},
    {'model': 'Schneider Xenon-Diamond 8mm', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 800},
    {'model': 'Schneider Xenon-Diamond 12mm', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 850},
    {'model': 'Schneider Xenon-Diamond 16mm', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 900},
    {'model': 'Schneider Xenon-Diamond 25mm', 'focal_length_mm': 25, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 950},
    {'model': 'Schneider Xenon-Diamond 35mm', 'focal_length_mm': 35, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 1000},
    {'model': 'Computar T0814CS', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 80},
    {'model': 'Computar T1214CS', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 90},
    {'model': 'Computar T1614CS', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 100},
]

# ------------------------------------------------------------------------------
# 1.8 РАСШИРЕННАЯ БАЗА ДАННЫХ ОСВЕЩЕНИЯ (50+ моделей)
# ------------------------------------------------------------------------------
LIGHTING_DATABASE = [
    # CCS — кольцевые
    {'model': 'LDR2-74-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 3.6, 'color': 'White', 'voltage_v': 24, 'price_usd': 250},
    {'model': 'LDR2-100-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 5.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 320},
    {'model': 'LDR2-120-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 7.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 400},
    {'model': 'LDR2-150-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 9.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 500},
    {'model': 'LDR2-170-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 12.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 620},
    {'model': 'LDR2-200-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 15.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 750},
    # CCS — купол
    {'model': 'DRL-100-W', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 8.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 600},
    {'model': 'DRL-150-W', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 12.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 850},
    {'model': 'DRL-200-W', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 18.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 1100},
    {'model': 'DRL-250-W', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 25.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 1500},
    # CCS — тёмное поле
    {'model': 'LFL-100-W', 'vendor': 'CCS', 'lighting_type': 'Тёмное поле (низкоугловое)',
     'power_w': 6.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 450},
    {'model': 'LFL-150-W', 'vendor': 'CCS', 'lighting_type': 'Тёмное поле (низкоугловое)',
     'power_w': 9.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 600},
    {'model': 'LFL-200-W', 'vendor': 'CCS', 'lighting_type': 'Тёмное поле (низкоугловое)',
     'power_w': 14.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 800},
    # CCS — контровое
    {'model': 'BLP-100-W', 'vendor': 'CCS', 'lighting_type': 'Контровое (backlight)',
     'power_w': 10.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 550},
    {'model': 'BLP-200-W', 'vendor': 'CCS', 'lighting_type': 'Контровое (backlight)',
     'power_w': 18.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 900},
    {'model': 'BLP-300-W', 'vendor': 'CCS', 'lighting_type': 'Контровое (backlight)',
     'power_w': 28.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 1400},
    {'model': 'BLP-400-W', 'vendor': 'CCS', 'lighting_type': 'Контровое (backlight)',
     'power_w': 40.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 2000},
    # CCS — коаксиальное
    {'model': 'CXL-100-W', 'vendor': 'CCS', 'lighting_type': 'Коаксиальное или диффузный купол',
     'power_w': 5.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 500},
    {'model': 'CXL-150-W', 'vendor': 'CCS', 'lighting_type': 'Коаксиальное или диффузный купол',
     'power_w': 8.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 750},
    {'model': 'CXL-200-W', 'vendor': 'CCS', 'lighting_type': 'Коаксиальное или диффузный купол',
     'power_w': 12.0, 'color': 'White', 'voltage_v': 24, 'price_usd': 1000},
    # CCS — цветные
    {'model': 'CCS LDR2-100-R', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 5.0, 'color': 'Red', 'voltage_v': 24, 'price_usd': 350},
    {'model': 'CCS LDR2-100-B', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 5.0, 'color': 'Blue', 'voltage_v': 24, 'price_usd': 350},
    {'model': 'CCS LDR2-100-IR', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 5.0, 'color': 'IR', 'voltage_v': 24, 'price_usd': 400},
    {'model': 'CCS LDR2-100-UV', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 5.0, 'color': 'UV', 'voltage_v': 24, 'price_usd': 550},
    {'model': 'CCS DRL-150-R', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 12.0, 'color': 'Red', 'voltage_v': 24, 'price_usd': 900},
    {'model': 'CCS DRL-150-B', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 12.0, 'color': 'Blue', 'voltage_v': 24, 'price_usd': 900},
    {'model': 'CCS BLP-200-IR', 'vendor': 'CCS', 'lighting_type': 'Контровое (backlight)',
     'power_w': 18.0, 'color': 'IR', 'voltage_v': 24, 'price_usd': 1100},

    # Advanced Illumination
    {'model': 'RL-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Кольцевое белое', 'power_w': 6.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 280},
    {'model': 'RL-150', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Кольцевое белое', 'power_w': 9.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 380},
    {'model': 'RL-200', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Кольцевое белое', 'power_w': 14.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 520},
    {'model': 'DL-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Диффузный купол', 'power_w': 10.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 700},
    {'model': 'DL-150', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Диффузный купол', 'power_w': 15.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 950},
    {'model': 'LF-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Тёмное поле (низкоугловое)', 'power_w': 7.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 500},
    {'model': 'LF-150', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Тёмное поле (низкоугловое)', 'power_w': 11.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 680},
    {'model': 'BL-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Контровое (backlight)', 'power_w': 12.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 650},
    {'model': 'BL-200', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Контровое (backlight)', 'power_w': 20.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 980},
    {'model': 'CX-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Коаксиальное или диффузный купол', 'power_w': 6.0,
     'color': 'White', 'voltage_v': 24, 'price_usd': 580},

    # Metaphase
    {'model': 'MRL-100-W', 'vendor': 'Metaphase',
     'lighting_type': 'Кольцевое белое', 'power_w': 5.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 260},
    {'model': 'MRL-150-W', 'vendor': 'Metaphase',
     'lighting_type': 'Кольцевое белое', 'power_w': 8.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 360},
    {'model': 'MDL-100-W', 'vendor': 'Metaphase',
     'lighting_type': 'Диффузный купол', 'power_w': 9.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 650},
    {'model': 'MDL-150-W', 'vendor': 'Metaphase',
     'lighting_type': 'Диффузный купол', 'power_w': 13.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 880},
    {'model': 'MLF-100-W', 'vendor': 'Metaphase',
     'lighting_type': 'Тёмное поле (низкоугловое)', 'power_w': 6.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 480},
    {'model': 'MBL-100-W', 'vendor': 'Metaphase',
     'lighting_type': 'Контровое (backlight)', 'power_w': 11.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 600},

    # Effilux
    {'model': 'EFFI-RL-100', 'vendor': 'Effilux',
     'lighting_type': 'Кольцевое белое', 'power_w': 5.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 240},
    {'model': 'EFFI-RL-150', 'vendor': 'Effilux',
     'lighting_type': 'Кольцевое белое', 'power_w': 8.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 340},
    {'model': 'EFFI-DL-100', 'vendor': 'Effilux',
     'lighting_type': 'Диффузный купол', 'power_w': 9.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 680},
    {'model': 'EFFI-LF-100', 'vendor': 'Effilux',
     'lighting_type': 'Тёмное поле (низкоугловое)', 'power_w': 6.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 460},
    {'model': 'EFFI-BL-100', 'vendor': 'Effilux',
     'lighting_type': 'Контровое (backlight)', 'power_w': 10.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 580},

    # Smart Vision Lights
    {'model': 'SVL-RL-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Кольцевое белое', 'power_w': 4.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 180},
    {'model': 'SVL-RL-150', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Кольцевое белое', 'power_w': 7.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 260},
    {'model': 'SVL-DL-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Диффузный купол', 'power_w': 8.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 500},
    {'model': 'SVL-LF-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Тёмное поле (низкоугловое)', 'power_w': 5.5, 'color': 'White',
     'voltage_v': 24, 'price_usd': 380},
    {'model': 'SVL-BL-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Контровое (backlight)', 'power_w': 9.0, 'color': 'White',
     'voltage_v': 24, 'price_usd': 450},
    {'model': 'SVL-CX-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Коаксиальное или диффузный купол', 'power_w': 5.0,
     'color': 'White', 'voltage_v': 24, 'price_usd': 420},
]


# ==============================================================================
# РАЗДЕЛ 2: ПЕРЕЧИСЛЕНИЯ
# ==============================================================================

class DefectType(str, Enum):
    SCRATCH = "царапина"
    CHIP = "скол"
    DISPLACEMENT = "смещение"
    MISSING = "отсутствие"
    COLOR = "цвет"
    CRACK = "трещина"


class Material(str, Enum):
    METAL = "металл"
    PLASTIC = "пластик"
    GLASS = "стекло"
    FABRIC = "ткань"
    CERAMIC = "керамика"


class Reflectivity(str, Enum):
    MATTE = "матовая (резина, ткань)"
    SEMI_MATTE = "полуматовая (пластик, краска)"
    GLOSSY = "глянцевая (металл, стекло)"
    MIRROR = "зеркальная (полировка, хром)"


class Contrast(str, Enum):
    DARK_ON_LIGHT = "тёмный на светлом"
    LIGHT_ON_DARK = "светлый на тёмном"
    COLOR = "цветной"


class BudgetLevel(str, Enum):
    LOW = "низкий"
    MEDIUM = "средний"
    HIGH = "высокий"


class LensMount(str, Enum):
    C = "C"
    CS = "CS"
    M12 = "M12"
    M42 = "M42"
    F = "F"


# ==============================================================================
# РАЗДЕЛ 3: СТРУКТУРЫ ДАННЫХ
# ==============================================================================

@dataclass
class CustomerRequirements:
    defect_size_mm: float
    defect_type: DefectType
    material: Material
    reflectivity: Reflectivity
    contrast: Contrast
    fov_width_mm: float
    fov_height_mm: float
    working_distance_mm: float
    line_speed_mm_s: float
    part_spacing_mm: float
    images_per_part: int
    is_moving: bool
    min_pixels_per_defect: int = 4
    ambient_light: str = "обычный цех"
    budget: BudgetLevel = BudgetLevel.MEDIUM
    num_cameras: int = 1
    preferred_mount: LensMount = LensMount.C
    camera_tilt_deg: float = 0.0


@dataclass
class CameraRecommendation:
    resolution: tuple
    sensor_format: str
    shutter_type: str
    fps_required: float
    max_exposure_time_ms: float
    interface: str
    camera_model: str
    camera_price_usd: float

    focal_length_mm: float
    aperture: float
    depth_of_field_mm: float
    lens_model: str
    lens_price_usd: float
    lens_mount: str
    lens_sensor_coverage: str

    hfov_deg: float
    vfov_deg: float
    dfov_deg: float

    camera_tilt_deg: float
    fov_center_mm: float
    fov_edge_near_mm: float
    fov_edge_far_mm: float
    perspective_distortion_pct: float

    lighting_type: str
    lighting_notes: str
    lighting_model: str
    lighting_price_usd: float
    required_illuminance_lux: float
    lighting_power_w: float

    total_price_usd: float
    budget_ok: bool
    budget_notes: str

    compatibility_notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


# ==============================================================================
# РАЗДЕЛ 4: ФУНКЦИИ РАСЧЁТА
# ==============================================================================

def calculate_required_resolution(fov_width_mm, fov_height_mm,
                                   defect_size_mm, min_pixels_per_defect):
    pixels_per_mm = min_pixels_per_defect / defect_size_mm
    required_width_px = math.ceil(fov_width_mm * pixels_per_mm)
    required_height_px = math.ceil(fov_height_mm * pixels_per_mm)
    chosen = None
    for res_w, res_h in STANDARD_RESOLUTIONS:
        if res_w >= required_width_px and res_h >= required_height_px:
            chosen = (res_w, res_h)
            break
    if chosen is None:
        chosen = STANDARD_RESOLUTIONS[-1]
    return (required_width_px, required_height_px), chosen


def calculate_max_exposure_time(line_speed_mm_s, fov_width_mm,
                                 sensor_width_px, max_blur_pixels=1.0):
    if line_speed_mm_s <= 0:
        return 1.0
    mm_per_pixel = fov_width_mm / sensor_width_px
    return (max_blur_pixels * mm_per_pixel) / line_speed_mm_s


def calculate_required_fps(line_speed_mm_s, part_spacing_mm,
                            images_per_part, is_moving):
    if not is_moving or part_spacing_mm <= 0:
        return 10.0
    return (line_speed_mm_s / part_spacing_mm) * images_per_part


def calculate_focal_length(sensor_width_mm, working_distance_mm, fov_width_mm):
    return (sensor_width_mm * working_distance_mm) / fov_width_mm


def calculate_field_of_view_angles(sensor_width_mm, sensor_height_mm, focal_length_mm):
    hfov_rad = 2 * math.atan(sensor_width_mm / (2 * focal_length_mm))
    vfov_rad = 2 * math.atan(sensor_height_mm / (2 * focal_length_mm))
    diagonal_mm = math.sqrt(sensor_width_mm ** 2 + sensor_height_mm ** 2)
    dfov_rad = 2 * math.atan(diagonal_mm / (2 * focal_length_mm))
    return (math.degrees(hfov_rad), math.degrees(vfov_rad), math.degrees(dfov_rad))


def calculate_tilt_and_perspective(working_distance_mm, fov_width_mm,
                                    camera_tilt_deg, hfov_deg):
    tilt_rad = math.radians(camera_tilt_deg)
    half_fov = fov_width_mm / 2.0
    depth_shift = half_fov * math.tan(tilt_rad)
    dist_near = working_distance_mm - depth_shift
    dist_far = working_distance_mm + depth_shift
    if dist_near > 0:
        fov_near = fov_width_mm * (dist_near / working_distance_mm)
    else:
        fov_near = 0.0
    fov_far = fov_width_mm * (dist_far / working_distance_mm)
    if fov_near > 0:
        perspective_pct = ((fov_far - fov_near) / fov_width_mm) * 100.0
    else:
        perspective_pct = 100.0
    return (fov_width_mm, fov_near, fov_far, perspective_pct)


def calculate_depth_of_field(focal_length_mm, aperture,
                              working_distance_mm, circle_of_confusion_mm=0.005):
    f = focal_length_mm
    N = aperture
    c = circle_of_confusion_mm
    s = working_distance_mm
    hyperfocal_mm = (f ** 2) / (N * c) + f
    near_mm = (hyperfocal_mm * s) / (hyperfocal_mm + (s - f))
    far_mm = (hyperfocal_mm * s) / (hyperfocal_mm - (s - f))
    return abs(far_mm - near_mm)


def calculate_required_illuminance(ambient_lux, reflectivity_coefficient,
                                    sensor_sensitivity, max_exposure_time_s, aperture):
    base_lux = (sensor_sensitivity * (aperture ** 2)) / max(max_exposure_time_s, 1e-6)
    reflection_compensation = 1.0 / max(reflectivity_coefficient, 0.1)
    ambient_compensation = 1.0 + (ambient_lux / 500.0)
    return base_lux * reflection_compensation * ambient_compensation


def calculate_lighting_power(required_lux, working_distance_mm, coverage_area_m2):
    lumens = required_lux * coverage_area_m2
    power_w = lumens / 100.0
    distance_factor = (working_distance_mm / 1000.0) ** 2
    return power_w * distance_factor


# ==============================================================================
# РАЗДЕЛ 5: ВЫБОР ОБОРУДОВАНИЯ
# ==============================================================================

def select_camera_from_database(required_resolution, shutter_type,
                                 fps_required, budget_usd):
    candidates = []
    for cam in CAMERA_DATABASE:
        res_w, res_h = cam['resolution']
        req_w, req_h = required_resolution
        if res_w < req_w or res_h < req_h:
            continue
        if shutter_type == 'Global' and cam['shutter'] != 'Global':
            continue
        if cam['max_fps'] < fps_required:
            continue
        if cam['price_usd'] > budget_usd:
            continue
        candidates.append(cam)
    if not candidates:
        return None
    candidates.sort(key=lambda x: x['price_usd'])
    return candidates[0]


def check_camera_lens_compatibility(camera: dict, lens: dict) -> list:
    notes = []
    camera_mount = camera.get('mount', 'C')
    lens_mount = lens.get('mount', 'C')
    if camera_mount != lens_mount:
        if camera_mount == 'CS' and lens_mount == 'C':
            notes.append(
                f"Крепление: объектив {lens_mount}-mount на камеру {camera_mount}-mount. "
                f"Требуется адаптер C→CS (5 мм)."
            )
        elif camera_mount == 'C' and lens_mount == 'CS':
            notes.append(
                f"Крепление: объектив {lens_mount}-mount на камеру {camera_mount}-mount. "
                f"НЕСОВМЕСТИМО без адаптера."
            )
        else:
            notes.append(
                f"Крепление: объектив {lens_mount}-mount, камера {camera_mount}-mount. "
                f"Требуется переходник."
            )
    camera_sensor = camera.get('sensor_format', '1/2"')
    lens_coverage = lens.get('sensor_coverage', '2/3"')
    camera_sensor_width = SENSOR_WIDTH_MM.get(camera_sensor, 6.4)
    lens_coverage_width = SENSOR_WIDTH_MM.get(lens_coverage, 8.8)
    if lens_coverage_width < camera_sensor_width:
        notes.append(
            f"Покрытие сенсора: объектив покрывает {lens_coverage} "
            f"({lens_coverage_width} мм), камера имеет {camera_sensor} "
            f"({camera_sensor_width} мм). Возможно виньетирование по краям."
        )
    return notes


def select_lens_from_database(focal_length_mm, budget_usd,
                               preferred_mount='C', sensor_format='1/2"'):
    sensor_width = SENSOR_WIDTH_MM.get(sensor_format, 6.4)
    candidates = []
    for lens in LENS_DATABASE:
        if preferred_mount and lens['mount'] != preferred_mount:
            continue
        lens_coverage = SENSOR_WIDTH_MM.get(lens['sensor_coverage'], 0)
        if lens_coverage < sensor_width:
            continue
        if lens['price_usd'] > budget_usd:
            continue
        candidates.append(lens)
    if not candidates:
        for lens in LENS_DATABASE:
            lens_coverage = SENSOR_WIDTH_MM.get(lens['sensor_coverage'], 0)
            if lens_coverage < sensor_width:
                continue
            if lens['price_usd'] > budget_usd:
                continue
            candidates.append(lens)
    if not candidates:
        return None
    candidates.sort(key=lambda x: abs(x['focal_length_mm'] - focal_length_mm))
    return candidates[0]


def select_lighting_from_database(lighting_type: str, required_power_w: float,
                                    budget_usd: float) -> Optional[dict]:
    candidates = []
    for light in LIGHTING_DATABASE:
        if light['lighting_type'] != lighting_type:
            continue
        if light['power_w'] < required_power_w:
            continue
        if light['price_usd'] > budget_usd:
            continue
        candidates.append(light)
    if not candidates:
        for light in LIGHTING_DATABASE:
            if light['power_w'] < required_power_w:
                continue
            if light['price_usd'] > budget_usd:
                continue
            candidates.append(light)
    if not candidates:
        return None
    candidates.sort(key=lambda x: x['power_w'])
    return candidates[0]


def select_lighting_type(req):
    if req.reflectivity == Reflectivity.MIRROR:
        return ("Коаксиальное или диффузный купол",
                "Зеркальная поверхность: избегать прямых бликов.")
    if req.defect_type in (DefectType.SCRATCH, DefectType.CHIP, DefectType.CRACK):
        return ("Тёмное поле (низкоугловое)",
                "Низкоугловое скользящее освещение подчёркивает неровности.")
    if req.defect_type in (DefectType.MISSING, DefectType.DISPLACEMENT):
        if req.contrast == Contrast.DARK_ON_LIGHT:
            return ("Контровое (backlight)", "Обратная подсветка даёт силуэт.")
        return ("Диффузный купол", "Равномерное освещение без теней.")
    if req.defect_type == DefectType.COLOR:
        return ("Кольцевое белое", "Белый свет для точной цветопередачи.")
    return ("Диффузный купол", "Стандартный вариант.")


# ==============================================================================
# РАЗДЕЛ 6: ГЛАВНАЯ ФУНКЦИЯ
# ==============================================================================

def select_camera_system(req: CustomerRequirements) -> CameraRecommendation:
    warnings = []
    compatibility_notes = []

    # Шаг 1: Разрешение
    (req_w, req_h), chosen_res = calculate_required_resolution(
        req.fov_width_mm, req.fov_height_mm,
        req.defect_size_mm, req.min_pixels_per_defect
    )
    if chosen_res == STANDARD_RESOLUTIONS[-1] and (req_w > chosen_res[0] or req_h > chosen_res[1]):
        warnings.append(f"Требуемое разрешение ({req_w}×{req_h}) превышает стандартные.")

    # Шаг 2: Выдержка
    max_exposure_s = calculate_max_exposure_time(
        req.line_speed_mm_s, req.fov_width_mm, chosen_res[0]
    )
    max_exposure_ms = max_exposure_s * 1000
    if max_exposure_ms < 0.1:
        warnings.append(f"Очень короткая выдержка: {max_exposure_ms:.3f} мс.")

    # Шаг 3: FPS
    fps_required = calculate_required_fps(
        req.line_speed_mm_s, req.part_spacing_mm,
        req.images_per_part, req.is_moving
    )
    if fps_required > 100:
        warnings.append(f"Высокая частота кадров: {fps_required:.1f} FPS.")

    # Шаг 4: Затвор
    if req.is_moving and req.line_speed_mm_s > 0:
        shutter_type = 'Global'
        shutter_text = "Global Shutter (обязательно)"
    else:
        shutter_type = 'Rolling'
        shutter_text = "Rolling Shutter (допустим)"

    # Шаг 5: Освещение (тип)
    lighting_type, lighting_notes = select_lighting_type(req)

    # Шаг 6: Интерфейс
    bit_depth = 8
    bandwidth_mbps = chosen_res[0] * chosen_res[1] * bit_depth * fps_required / 1e6
    if bandwidth_mbps < 1000:
        interface = "GigE Vision"
    elif bandwidth_mbps < 5000:
        interface = "USB3 Vision"
    else:
        interface = "10GigE / CoaXPress"
        warnings.append(f"Высокая пропускная способность: {bandwidth_mbps:.0f} Мбит/с.")

    # Шаг 7: Бюджет и выбор камеры
    budget_limits = {
        BudgetLevel.LOW: 3000,
        BudgetLevel.MEDIUM: 10000,
        BudgetLevel.HIGH: 100000,
    }
    total_budget = budget_limits[req.budget] * req.num_cameras

    camera = select_camera_from_database(
        chosen_res, shutter_type, fps_required, total_budget * 0.6
    )

    if camera is None:
        warnings.append("Не найдено камеры под требования и бюджет.")
        camera_model = "Не найдено"
        camera_price = 0
        sensor_format = '1/2"'
    else:
        camera_model = f"{camera['vendor']} {camera['model']}"
        camera_price = camera['price_usd']
        sensor_format = camera['sensor_format']

    # Шаг 8: Объектив
    sensor_width_mm = SENSOR_WIDTH_MM.get(sensor_format, 6.4)
    sensor_height_mm = sensor_width_mm * SENSOR_HEIGHT_RATIO
    focal_length = calculate_focal_length(
        sensor_width_mm, req.working_distance_mm, req.fov_width_mm
    )

    lens = select_lens_from_database(
        focal_length, total_budget * 0.2,
        preferred_mount=req.preferred_mount.value,
        sensor_format=sensor_format
    )

    if lens is None:
        warnings.append("Не найдено объектива под требования и бюджет.")
        lens_model = "Не найдено"
        lens_price = 0
        focal_length = round(focal_length, 1)
        aperture = 1.4
        lens_mount = "?"
        lens_sensor_coverage = "?"
    else:
        lens_model = f"{lens['model']} ({lens['focal_length_mm']} мм, f/{lens['max_aperture']})"
        lens_price = lens['price_usd']
        focal_length = lens['focal_length_mm']
        aperture = lens['max_aperture']
        lens_mount = lens['mount']
        lens_sensor_coverage = lens['sensor_coverage']

    # Шаг 9: Проверка совместимости
    if camera and lens:
        compatibility_notes = check_camera_lens_compatibility(camera, lens)
        if compatibility_notes:
            warnings.extend(compatibility_notes)

    # Шаг 10: Угол обзора
    hfov, vfov, dfov = calculate_field_of_view_angles(
        sensor_width_mm, sensor_height_mm, focal_length
    )

    # Шаг 11: Угол наклона и перспектива
    fov_center, fov_near, fov_far, perspective_pct = calculate_tilt_and_perspective(
        req.working_distance_mm, req.fov_width_mm,
        req.camera_tilt_deg, hfov
    )

    if req.camera_tilt_deg > 5.0:
        warnings.append(
            f"Угол наклона камеры {req.camera_tilt_deg}°. "
            f"Перспективные искажения: {perspective_pct:.1f}%. "
            f"Ближний край FOV: {fov_near:.1f} мм, дальний: {fov_far:.1f} мм."
        )
    if perspective_pct > 20.0:
        warnings.append(
            f"Сильные перспективные искажения: {perspective_pct:.1f}%. "
            f"Рекомендуется уменьшить угол наклона или использовать telecentric-объектив."
        )

    # Шаг 12: DOF
    dof_mm = calculate_depth_of_field(focal_length, aperture, req.working_distance_mm)
    if dof_mm < 5:
        warnings.append(f"Малая глубина резкости: {dof_mm:.1f} мм.")

    # Шаг 13: Мощность освещения
    ambient_lux = AMBIENT_LIGHT_LUX.get(req.ambient_light, 300)
    reflectivity_coef = REFLECTIVITY_COEFFICIENT.get(req.reflectivity.value, 0.4)
    sensor_sens = SENSOR_SENSITIVITY.get(
        'Global Shutter CMOS' if shutter_type == 'Global' else 'Rolling Shutter CMOS', 2.0
    )
    required_lux = calculate_required_illuminance(
        ambient_lux, reflectivity_coef, sensor_sens, max_exposure_s, aperture
    )
    coverage_area_m2 = (req.fov_width_mm / 1000) * (req.fov_height_mm / 1000)
    lighting_power_w = calculate_lighting_power(
        required_lux, req.working_distance_mm, coverage_area_m2
    )

    # Шаг 14: Выбор модели освещения
    light = select_lighting_from_database(
        lighting_type, lighting_power_w, total_budget * 0.2
    )

    if light is None:
        warnings.append("Не найдено освещения под требования и бюджет.")
        lighting_model = "Не найдено"
        lighting_price = 0
    else:
        lighting_model = f"{light['vendor']} {light['model']} ({light['power_w']} Вт)"
        lighting_price = light['price_usd']

    # Шаг 15: Бюджет
    total_price = (camera_price + lens_price + lighting_price) * req.num_cameras
    budget_ok = total_price <= total_budget

    if budget_ok:
        budget_notes = f"В рамках бюджета. Остаток: ${total_budget - total_price:.0f}"
    else:
        budget_notes = (
            f"Превышение бюджета на ${total_price - total_budget:.0f}. "
            f"Рассмотрите более дешёвые компоненты."
        )

    return CameraRecommendation(
        resolution=chosen_res,
        sensor_format=sensor_format,
        shutter_type=shutter_text,
        fps_required=round(fps_required, 1),
        max_exposure_time_ms=round(max_exposure_ms, 3),
        interface=interface,
        camera_model=camera_model,
        camera_price_usd=camera_price,
        focal_length_mm=round(focal_length, 1),
        aperture=aperture,
        depth_of_field_mm=round(dof_mm, 1),
        lens_model=lens_model,
        lens_price_usd=lens_price,
        lens_mount=lens_mount,
        lens_sensor_coverage=lens_sensor_coverage,
        hfov_deg=round(hfov, 1),
        vfov_deg=round(vfov, 1),
        dfov_deg=round(dfov, 1),
        camera_tilt_deg=req.camera_tilt_deg,
        fov_center_mm=round(fov_center, 1),
        fov_edge_near_mm=round(fov_near, 1),
        fov_edge_far_mm=round(fov_far, 1),
        perspective_distortion_pct=round(perspective_pct, 1),
        lighting_type=lighting_type,
        lighting_notes=lighting_notes,
        lighting_model=lighting_model,
        lighting_price_usd=lighting_price,
        required_illuminance_lux=round(required_lux, 0),
        lighting_power_w=round(lighting_power_w, 1),
        total_price_usd=round(total_price, 0),
        budget_ok=budget_ok,
        budget_notes=budget_notes,
        compatibility_notes=compatibility_notes,
        warnings=warnings,
    )


# ==============================================================================
# РАЗДЕЛ 7: ВИЗУАЛИЗАЦИЯ
# ==============================================================================

def visualize_recommendation(rec, req, filename="recommendation_plots.png"):
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib не установлена. Визуализация пропущена.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # --- График 1: Углы обзора ---
    ax1 = axes[0, 0]
    angles = ['HFOV', 'VFOV', 'DFOV']
    values = [rec.hfov_deg, rec.vfov_deg, rec.dfov_deg]
    colors = ['#4C72B0', '#55A868', '#C44E52']
    bars = ax1.bar(angles, values, color=colors)
    ax1.set_ylabel('Угол обзора (градусы)')
    ax1.set_title('Углы обзора объектива')
    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{val:.1f}°', ha='center', fontsize=10)

    # --- График 2: DOF vs рабочая дистанция ---
    ax2 = axes[0, 1]
    distances = np.linspace(req.working_distance_mm * 0.5,
                            req.working_distance_mm * 2.0, 50)
    dofs = [calculate_depth_of_field(rec.focal_length_mm, rec.aperture, d)
            for d in distances]
    ax2.plot(distances, dofs, color='#4C72B0', linewidth=2)
    ax2.axvline(req.working_distance_mm, color='red', linestyle='--',
                label=f'Рабочая дистанция: {req.working_distance_mm} мм')
    ax2.axhline(rec.depth_of_field_mm, color='green', linestyle=':',
                label=f'DOF: {rec.depth_of_field_mm} мм')
    ax2.set_xlabel('Рабочая дистанция (мм)')
    ax2.set_ylabel('Глубина резкости (мм)')
    ax2.set_title('DOF vs рабочая дистанция')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # --- График 3: Распределение бюджета ---
    ax3 = axes[1, 0]
    labels = ['Камера', 'Объектив', 'Освещение']
    sizes = [rec.camera_price_usd, rec.lens_price_usd, rec.lighting_price_usd]
    colors_pie = ['#4C72B0', '#55A868', '#C44E52']
    if sum(sizes) == 0:
        ax3.text(0.5, 0.5, 'Нет данных', ha='center', va='center')
    else:
        wedges, texts, autotexts = ax3.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            colors=colors_pie, startangle=90
        )
        ax3.set_title(f'Бюджет: ${rec.total_price_usd:.0f}')

    # --- График 4: Схема наклона камеры ---
    ax4 = axes[1, 1]
    ax4.set_xlim(-req.fov_width_mm, req.fov_width_mm)
    ax4.set_ylim(0, req.working_distance_mm * 1.2)
    ax4.axhline(y=0, color='black', linewidth=2, label='Объект')
    tilt_rad = math.radians(rec.camera_tilt_deg)
    cam_x = req.working_distance_mm * math.tan(tilt_rad)
    cam_y = req.working_distance_mm
    ax4.plot(cam_x, cam_y, 'ro', markersize=12, label='Камера')
    ax4.plot(0, 0, 'go', markersize=8, label='Центр FOV')
    ax4.plot([cam_x, -rec.fov_edge_near_mm / 2], [cam_y, 0],
             'b--', alpha=0.5, label='Ближний край')
    ax4.plot([cam_x, rec.fov_edge_far_mm / 2], [cam_y, 0],
             'r--', alpha=0.5, label='Дальний край')
    ax4.annotate(f'Наклон: {rec.camera_tilt_deg}°',
                 xy=(cam_x, cam_y), xytext=(cam_x + 50, cam_y + 50),
                 fontsize=9, arrowprops=dict(arrowstyle='->'))
    ax4.annotate(f'Ближний: {rec.fov_edge_near_mm:.0f} мм',
                 xy=(-rec.fov_edge_near_mm / 2, 0),
                 xytext=(-rec.fov_edge_near_mm, -100),
                 fontsize=8, color='blue')
    ax4.annotate(f'Дальний: {rec.fov_edge_far_mm:.0f} мм',
                 xy=(rec.fov_edge_far_mm / 2, 0),
                 xytext=(rec.fov_edge_far_mm / 2, -100),
                 fontsize=8, color='red')
    ax4.set_xlabel('Ширина (мм)')
    ax4.set_ylabel('Дистанция (мм)')
    ax4.set_title(f'Наклон камеры и FOV (искажения: {rec.perspective_distortion_pct:.1f}%)')
    ax4.legend(fontsize=7, loc='upper right')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"Графики сохранены: {filename}")


# ==============================================================================
# РАЗДЕЛ 8: СРАВНЕНИЕ КОНФИГУРАЦИЙ
# ==============================================================================

def compare_configurations(configs: List[CameraRecommendation],
                            names: List[str]) -> str:
    if not configs:
        return "Нет конфигураций для сравнения."

    lines = []
    lines.append("=" * 110)
    lines.append("СРАВНЕНИЕ КОНФИГУРАЦИЙ")
    lines.append("=" * 110)

    header = f"{'Параметр':<28}"
    for name in names:
        header += f"{name:<25}"
    lines.append(header)
    lines.append("-" * 110)

    rows = [
        ("Камера", [c.camera_model[:22] for c in configs]),
        ("Разрешение", [f"{c.resolution[0]}x{c.resolution[1]}" for c in configs]),
        ("Затвор", [c.shutter_type[:22] for c in configs]),
        ("FPS", [str(c.fps_required) for c in configs]),
        ("Интерфейс", [c.interface for c in configs]),
        ("Объектив", [c.lens_model[:22] for c in configs]),
        ("Фокусное", [f"{c.focal_length_mm} мм" for c in configs]),
        ("HFOV", [f"{c.hfov_deg}°" for c in configs]),
        ("DOF", [f"{c.depth_of_field_mm} мм" for c in configs]),
        ("Наклон", [f"{c.camera_tilt_deg}°" for c in configs]),
        ("Искажения", [f"{c.perspective_distortion_pct}%" for c in configs]),
        ("Освещение", [c.lighting_model[:22] for c in configs]),
        ("Мощность света", [f"{c.lighting_power_w} Вт" for c in configs]),
        ("Итого", [f"${c.total_price_usd:.0f}" for c in configs]),
        ("Бюджет", ["OK" if c.budget_ok else "ПРЕВЫШЕН" for c in configs]),
    ]

    for label, values in rows:
        line = f"{label:<28}"
        for val in values:
            line += f"{val:<25}"
        lines.append(line)

    lines.append("=" * 110)
    return "\n".join(lines)


def export_comparison_to_csv(configs: List[CameraRecommendation],
                              names: List[str],
                              filename: str = "comparison.csv"):
    if not configs:
        return

    headers = ["Параметр"] + names
    rows = [
        ["Камера"] + [c.camera_model for c in configs],
        ["Разрешение"] + [f"{c.resolution[0]}x{c.resolution[1]}" for c in configs],
        ["Затвор"] + [c.shutter_type for c in configs],
        ["FPS"] + [str(c.fps_required) for c in configs],
        ["Интерфейс"] + [c.interface for c in configs],
        ["Объектив"] + [c.lens_model for c in configs],
        ["Фокусное расстояние"] + [f"{c.focal_length_mm} мм" for c in configs],
        ["HFOV"] + [f"{c.hfov_deg}°" for c in configs],
        ["VFOV"] + [f"{c.vfov_deg}°" for c in configs],
        ["DFOV"] + [f"{c.dfov_deg}°" for c in configs],
        ["DOF"] + [f"{c.depth_of_field_mm} мм" for c in configs],
        ["Угол наклона"] + [f"{c.camera_tilt_deg}°" for c in configs],
        ["Перспективные искажения"] + [f"{c.perspective_distortion_pct}%" for c in configs],
        ["Освещение"] + [c.lighting_model for c in configs],
        ["Мощность света"] + [f"{c.lighting_power_w} Вт" for c in configs],
        ["Итого"] + [f"${c.total_price_usd:.0f}" for c in configs],
        ["Бюджет"] + ["OK" if c.budget_ok else "ПРЕВЫШЕН" for c in configs],
    ]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Сравнение сохранено: {filename}")


# ==============================================================================
# РАЗДЕЛ 9: ВЫВОД
# ==============================================================================

def format_recommendation_text(rec, req) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("РЕКОМЕНДАЦИЯ ПО КАМЕРЕ, ОБЪЕКТИВУ И ОСВЕЩЕНИЮ")
    lines.append("=" * 70)

    lines.append(f"\nВХОДНЫЕ ТРЕБОВАНИЯ:")
    lines.append(f"  Дефект: {req.defect_size_mm} мм, {req.defect_type.value}")
    lines.append(f"  Материал: {req.material.value}, {req.reflectivity.value}")
    lines.append(f"  FOV: {req.fov_width_mm}×{req.fov_height_mm} мм")
    lines.append(f"  Рабочая дистанция: {req.working_distance_mm} мм")
    lines.append(f"  Скорость линии: {req.line_speed_mm_s} мм/с")
    lines.append(f"  Движение: {'да' if req.is_moving else 'нет'}")
    lines.append(f"  Бюджет: {req.budget.value}")
    lines.append(f"  Камер: {req.num_cameras}")
    lines.append(f"  Угол наклона камеры: {req.camera_tilt_deg}°")

    lines.append(f"\n--- КАМЕРА ---")
    lines.append(f"  Модель: {rec.camera_model}")
    lines.append(f"  Разрешение: {rec.resolution[0]}×{rec.resolution[1]} px")
    lines.append(f"  Формат сенсора: {rec.sensor_format}")
    lines.append(f"  Затвор: {rec.shutter_type}")
    lines.append(f"  Частота кадров: {rec.fps_required} FPS")
    lines.append(f"  Макс. выдержка: {rec.max_exposure_time_ms} мс")
    lines.append(f"  Интерфейс: {rec.interface}")
    lines.append(f"  Цена: ${rec.camera_price_usd:.0f}")

    lines.append(f"\n--- ОБЪЕКТИВ ---")
    lines.append(f"  Модель: {rec.lens_model}")
    lines.append(f"  Фокусное расстояние: {rec.focal_length_mm} мм")
    lines.append(f"  Диафрагма: f/{rec.aperture}")
    lines.append(f"  Крепление: {rec.lens_mount}")
    lines.append(f"  Покрытие сенсора: {rec.lens_sensor_coverage}")
    lines.append(f"  Глубина резкости: {rec.depth_of_field_mm} мм")
    lines.append(f"  Цена: ${rec.lens_price_usd:.0f}")

    lines.append(f"\n--- УГОЛ ОБЗОРА ---")
    lines.append(f"  Горизонтальный (HFOV): {rec.hfov_deg}°")
    lines.append(f"  Вертикальный (VFOV): {rec.vfov_deg}°")
    lines.append(f"  Диагональный (DFOV): {rec.dfov_deg}°")

    lines.append(f"\n--- НАКЛОН И ПЕРСПЕКТИВА ---")
    lines.append(f"  Угол наклона камеры: {rec.camera_tilt_deg}°")
    lines.append(f"  FOV в центре: {rec.fov_center_mm} мм")
    lines.append(f"  FOV на ближнем краю: {rec.fov_edge_near_mm} мм")
    lines.append(f"  FOV на дальнем краю: {rec.fov_edge_far_mm} мм")
    lines.append(f"  Перспективные искажения: {rec.perspective_distortion_pct}%")

    lines.append(f"\n--- ОСВЕЩЕНИЕ ---")
    lines.append(f"  Тип: {rec.lighting_type}")
    lines.append(f"  Модель: {rec.lighting_model}")
    lines.append(f"  Примечание: {rec.lighting_notes}")
    lines.append(f"  Требуемая освещённость: {rec.required_illuminance_lux} лк")
    lines.append(f"  Оценка мощности: {rec.lighting_power_w} Вт")
    lines.append(f"  Цена: ${rec.lighting_price_usd:.0f}")

    lines.append(f"\n--- СОВМЕСТИМОСТЬ ---")
    if rec.compatibility_notes:
        for note in rec.compatibility_notes:
            lines.append(f"  ⚠ {note}")
    else:
        lines.append(f"  ✓ Камера и объектив совместимы.")

    lines.append(f"\n--- БЮДЖЕТ ---")
    lines.append(f"  Итого: ${rec.total_price_usd:.0f}")
    lines.append(f"  Статус: {rec.budget_notes}")

    if rec.warnings:
        lines.append(f"\n--- ПРЕДУПРЕЖДЕНИЯ ---")
        for w in rec.warnings:
            lines.append(f"  ⚠ {w}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def print_recommendation(rec, req):
    print(format_recommendation_text(rec, req))


# ==============================================================================
# РАЗДЕЛ 10: ЭКСПОРТ PDF
# ==============================================================================

def export_to_pdf(rec, req, filename="camera_recommendation.pdf",
                   plot_filename="recommendation_plots.png"):
    if not PDF_AVAILABLE:
        print("PDF не создан: fpdf2 не установлена.")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Camera & Lighting Recommendation", ln=True, align="C")
    pdf.ln(5)

    def section(title, items):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Arial", "", 10)
        for item in items:
            safe_item = item.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 6, safe_item, ln=True)
        pdf.ln(3)

    section("Customer Requirements", [
        f"Defect: {req.defect_size_mm} mm, {req.defect_type.value}",
        f"Material: {req.material.value}, {req.reflectivity.value}",
        f"FOV: {req.fov_width_mm}x{req.fov_height_mm} mm",
        f"Working distance: {req.working_distance_mm} mm",
        f"Line speed: {req.line_speed_mm_s} mm/s",
        f"Camera tilt: {req.camera_tilt_deg} deg",
    ])

    section("Camera", [
        f"Model: {rec.camera_model}",
        f"Resolution: {rec.resolution[0]}x{rec.resolution[1]} px",
        f"Sensor: {rec.sensor_format}",
        f"Shutter: {rec.shutter_type}",
        f"FPS: {rec.fps_required}",
        f"Interface: {rec.interface}",
        f"Price: ${rec.camera_price_usd:.0f}",
    ])

    section("Lens", [
        f"Model: {rec.lens_model}",
        f"Focal length: {rec.focal_length_mm} mm",
        f"Aperture: f/{rec.aperture}",
        f"Mount: {rec.lens_mount}",
        f"Sensor coverage: {rec.lens_sensor_coverage}",
        f"DOF: {rec.depth_of_field_mm} mm",
        f"Price: ${rec.lens_price_usd:.0f}",
    ])

    section("Field of View", [
        f"HFOV: {rec.hfov_deg} deg",
        f"VFOV: {rec.vfov_deg} deg",
        f"DFOV: {rec.dfov_deg} deg",
    ])

    section("Tilt & Perspective", [
        f"Camera tilt: {rec.camera_tilt_deg} deg",
        f"FOV center: {rec.fov_center_mm} mm",
        f"FOV near edge: {rec.fov_edge_near_mm} mm",
        f"FOV far edge: {rec.fov_edge_far_mm} mm",
        f"Perspective distortion: {rec.perspective_distortion_pct}%",
    ])

    section("Lighting", [
        f"Type: {rec.lighting_type}",
        f"Model: {rec.lighting_model}",
        f"Required illuminance: {rec.required_illuminance_lux} lux",
        f"Estimated power: {rec.lighting_power_w} W",
        f"Price: ${rec.lighting_price_usd:.0f}",
    ])

    if rec.compatibility_notes:
        section("Compatibility Notes", [f"- {n}" for n in rec.compatibility_notes])

    section("Budget", [
        f"Total: ${rec.total_price_usd:.0f}",
        f"Status: {rec.budget_notes}",
    ])

    if rec.warnings:
        section("Warnings", [f"- {w}" for w in rec.warnings])

    # Вставка PNG с графиками
    if plot_filename and os.path.exists(plot_filename):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Visualization", ln=True)
        pdf.ln(5)
        pdf.image(plot_filename, x=10, y=30, w=190)
        print(f"Графики встроены в PDF: {plot_filename}")
    elif plot_filename:
        print(f"PNG не найден: {plot_filename}. Графики не встроены.")

    pdf.output(filename)
    print(f"\nPDF сохранён: {filename}")


# ==============================================================================
# РАЗДЕЛ 11: ЭКСПОРТ CSV
# ==============================================================================

def export_to_csv(rec, req, filename="camera_recommendation.csv"):
    rows = [
        ["Параметр", "Значение", "Единица"],
        ["--- ТРЕБОВАНИЯ ---", "", ""],
        ["Размер дефекта", req.defect_size_mm, "мм"],
        ["Тип дефекта", req.defect_type.value, ""],
        ["Материал", req.material.value, ""],
        ["Отражающая способность", req.reflectivity.value, ""],
        ["Ширина FOV", req.fov_width_mm, "мм"],
        ["Высота FOV", req.fov_height_mm, "мм"],
        ["Рабочая дистанция", req.working_distance_mm, "мм"],
        ["Скорость линии", req.line_speed_mm_s, "мм/с"],
        ["Движение", "да" if req.is_moving else "нет", ""],
        ["Бюджет", req.budget.value, ""],
        ["Количество камер", req.num_cameras, "шт"],
        ["Угол наклона камеры", req.camera_tilt_deg, "град"],
        ["--- КАМЕРА ---", "", ""],
        ["Модель камеры", rec.camera_model, ""],
        ["Разрешение", f"{rec.resolution[0]}x{rec.resolution[1]}", "px"],
        ["Формат сенсора", rec.sensor_format, ""],
        ["Затвор", rec.shutter_type, ""],
        ["FPS", rec.fps_required, "кадр/с"],
        ["Макс. выдержка", rec.max_exposure_time_ms, "мс"],
        ["Интерфейс", rec.interface, ""],
        ["Цена камеры", rec.camera_price_usd, "USD"],
        ["--- ОБЪЕКТИВ ---", "", ""],
        ["Модель объектива", rec.lens_model, ""],
        ["Фокусное расстояние", rec.focal_length_mm, "мм"],
        ["Диафрагма", f"f/{rec.aperture}", ""],
        ["Крепление", rec.lens_mount, ""],
        ["Покрытие сенсора", rec.lens_sensor_coverage, ""],
        ["Глубина резкости", rec.depth_of_field_mm, "мм"],
        ["Цена объектива", rec.lens_price_usd, "USD"],
        ["--- УГОЛ ОБЗОРА ---", "", ""],
        ["HFOV", rec.hfov_deg, "град"],
        ["VFOV", rec.vfov_deg, "град"],
        ["DFOV", rec.dfov_deg, "град"],
        ["--- НАКЛОН И ПЕРСПЕКТИВА ---", "", ""],
        ["Угол наклона камеры", rec.camera_tilt_deg, "град"],
        ["FOV в центре", rec.fov_center_mm, "мм"],
        ["FOV на ближнем краю", rec.fov_edge_near_mm, "мм"],
        ["FOV на дальнем краю", rec.fov_edge_far_mm, "мм"],
        ["Перспективные искажения", rec.perspective_distortion_pct, "%"],
        ["--- ОСВЕЩЕНИЕ ---", "", ""],
        ["Тип освещения", rec.lighting_type, ""],
        ["Модель освещения", rec.lighting_model, ""],
        ["Требуемая освещённость", rec.required_illuminance_lux, "лк"],
        ["Мощность", rec.lighting_power_w, "Вт"],
        ["Цена освещения", rec.lighting_price_usd, "USD"],
        ["--- БЮДЖЕТ ---", "", ""],
        ["Итого", rec.total_price_usd, "USD"],
        ["Статус", rec.budget_notes, ""],
    ]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerows(rows)

    print(f"CSV сохранён: {filename}")


# ==============================================================================
# РАЗДЕЛ 12: GUI НА GRADIO
# ==============================================================================

def build_gradio_interface():
    if not GRADIO_AVAILABLE:
        print("Gradio не установлен. Установите: pip install gradio")
        return None

    def calculate_ui(
        defect_size_mm, defect_type, material, reflectivity, contrast,
        fov_width_mm, fov_height_mm, working_distance_mm,
        line_speed_mm_s, part_spacing_mm, images_per_part, is_moving,
        min_pixels_per_defect, ambient_light, budget, num_cameras,
        preferred_mount, camera_tilt_deg
    ):
        try:
            req = CustomerRequirements(
                defect_size_mm=float(defect_size_mm),
                defect_type=DefectType(defect_type),
                material=Material(material),
                reflectivity=Reflectivity(reflectivity),
                contrast=Contrast(contrast),
                fov_width_mm=float(fov_width_mm),
                fov_height_mm=float(fov_height_mm),
                working_distance_mm=float(working_distance_mm),
                line_speed_mm_s=float(line_speed_mm_s),
                part_spacing_mm=float(part_spacing_mm),
                images_per_part=int(images_per_part),
                is_moving=bool(is_moving),
                min_pixels_per_defect=int(min_pixels_per_defect),
                ambient_light=ambient_light,
                budget=BudgetLevel(budget),
                num_cameras=int(num_cameras),
                preferred_mount=LensMount(preferred_mount),
                camera_tilt_deg=float(camera_tilt_deg),
            )
            rec = select_camera_system(req)
            text = format_recommendation_text(rec, req)
            return text
        except Exception as e:
            return f"ОШИБКА: {e}"

    with gr.Blocks(title="Camera & Lighting Selector") as interface:
        gr.Markdown("# Подбор камеры и освещения для промышленного CV")
        gr.Markdown("Заполните требования заказчика и нажмите **Рассчитать**.")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Объект и дефект")
                defect_size = gr.Number(label="Размер дефекта (мм)", value=0.5)
                defect_type = gr.Dropdown(
                    choices=[d.value for d in DefectType],
                    label="Тип дефекта", value=DefectType.DISPLACEMENT.value)
                material = gr.Dropdown(
                    choices=[m.value for m in Material],
                    label="Материал", value=Material.METAL.value)
                reflectivity = gr.Dropdown(
                    choices=[r.value for r in Reflectivity],
                    label="Отражающая способность", value=Reflectivity.SEMI_MATTE.value)
                contrast = gr.Dropdown(
                    choices=[c.value for c in Contrast],
                    label="Контраст", value=Contrast.DARK_ON_LIGHT.value)

            with gr.Column():
                gr.Markdown("### Геометрия и движение")
                fov_w = gr.Number(label="Ширина FOV (мм)", value=500)
                fov_h = gr.Number(label="Высота FOV (мм)", value=300)
                working_dist = gr.Number(label="Рабочая дистанция (мм)", value=800)
                line_speed = gr.Number(label="Скорость линии (мм/с)", value=1000)
                part_spacing = gr.Number(label="Расстояние между деталями (мм)", value=200)
                images_per_part = gr.Number(label="Изображений на деталь", value=1)
                is_moving = gr.Checkbox(label="Объект движется", value=True)

            with gr.Column():
                gr.Markdown("### Требования")
                min_px = gr.Number(label="Мин. пикселей на дефект", value=4)
                ambient = gr.Dropdown(
                    choices=list(AMBIENT_LIGHT_LUX.keys()),
                    label="Освещение в цеху", value="обычный цех")
                budget = gr.Dropdown(
                    choices=[b.value for b in BudgetLevel],
                    label="Бюджет", value=BudgetLevel.MEDIUM.value)
                num_cam = gr.Number(label="Количество камер", value=1)
                preferred_mount = gr.Dropdown(
                    choices=[m.value for m in LensMount],
                    label="Крепление объектива", value=LensMount.C.value)
                tilt = gr.Number(label="Угол наклона камеры (град)", value=0.0)

        btn = gr.Button("Рассчитать", variant="primary")
        output = gr.Textbox(label="Результат", lines=45)

        btn.click(
            fn=calculate_ui,
            inputs=[
                defect_size, defect_type, material, reflectivity, contrast,
                fov_w, fov_h, working_dist,
                line_speed, part_spacing, images_per_part, is_moving,
                min_px, ambient, budget, num_cam, preferred_mount, tilt,
            ],
            outputs=output,
        )

    return interface


# ==============================================================================
# РАЗДЕЛ 13: CLI ЧЕРЕЗ ARGPARSE
# ==============================================================================

EXTENDED_HELP = """
================================================================================
 КАЛЬКУЛЯТОР ПОДБОРА КАМЕРЫ, ОБЪЕКТИВА И ОСВЕЩЕНИЯ
 для промышленного компьютерного зрения
================================================================================

ИСПОЛЬЗОВАНИЕ:
    python check_camera.py [ОПЦИИ]

    Без аргументов — вывод этой справки.
    С аргументами — расчёт и отчёт.

--------------------------------------------------------------------------------
 ОБЪЕКТ И ДЕФЕКТ
--------------------------------------------------------------------------------

  --defect-size FLOAT      Минимальный размер дефекта.
                           Единица: мм.
                           По умолчанию: 0.5
                           Пример: --defect-size 0.5

  --defect-type {scratch,chip,displacement,missing,color,crack}
                           Тип дефекта:
                             scratch        — царапина
                             chip           — скол
                             displacement   — смещение
                             missing        — отсутствие
                             color          — цвет
                             crack          — трещина
                           По умолчанию: displacement
                           Пример: --defect-type displacement

  --material {metal,plastic,glass,fabric,ceramic}
                           Материал поверхности:
                             metal    — металл
                             plastic  — пластик
                             glass    — стекло
                             fabric   — ткань
                             ceramic  — керамика
                           По умолчанию: metal
                           Пример: --material metal

  --reflectivity {matte,semi_matte,glossy,mirror}
                           Отражающая способность:
                             matte       — матовая (резина, ткань)
                             semi_matte  — полуматовая (пластик, краска)
                             glossy      — глянцевая (металл, стекло)
                             mirror      — зеркальная (полировка, хром)
                           По умолчанию: semi_matte
                           Пример: --reflectivity semi_matte

  --contrast {dark_on_light,light_on_dark,color}
                           Контраст дефекта относительно фона:
                             dark_on_light  — тёмный на светлом
                             light_on_dark  — светлый на тёмном
                             color          — цветной
                           По умолчанию: dark_on_light
                           Пример: --contrast dark_on_light

--------------------------------------------------------------------------------
 ГЕОМЕТРИЯ СЦЕНЫ
--------------------------------------------------------------------------------

  --fov-width FLOAT        Ширина поля зрения.
                           Единица: мм.
                           По умолчанию: 500
                           Пример: --fov-width 500

  --fov-height FLOAT       Высота поля зрения.
                           Единица: мм.
                           По умолчанию: 300
                           Пример: --fov-height 300

  --working-distance FLOAT Рабочая дистанция (камера → объект).
                           Единица: мм.
                           По умолчанию: 800
                           Пример: --working-distance 800

--------------------------------------------------------------------------------
 ДВИЖЕНИЕ
--------------------------------------------------------------------------------

  --line-speed FLOAT       Скорость линии.
                           Единица: мм/с.
                           По умолчанию: 0 (статика).
                           Пример: --line-speed 1000

  --part-spacing FLOAT     Расстояние между деталями.
                           Единица: мм.
                           По умолчанию: 200
                           Пример: --part-spacing 200

  --images-per-part INT    Количество изображений на деталь.
                           Единица: штук.
                           По умолчанию: 1
                           Пример: --images-per-part 1

  --is-moving              Флаг: объект движется.
                           Если не указан — считается статика.
                           Пример: --is-moving

--------------------------------------------------------------------------------
 ТРЕБОВАНИЯ К СИСТЕМЕ
--------------------------------------------------------------------------------

  --min-pixels INT         Минимум пикселей на дефект (3–5 рекомендуется).
                           Единица: штук.
                           По умолчанию: 4
                           Пример: --min-pixels 4

  --ambient-light {bright,normal,dim,dark}
                           Освещение в цеху:
                             bright  — яркий цех (окна, солнце) — 1000 лк
                             normal  — обычный цех — 300 лк
                             dim     — тусклый цех — 100 лк
                             dark    — темнота (кожух) — 10 лк
                           По умолчанию: normal
                           Пример: --ambient-light normal

  --budget {low,medium,high}
                           Бюджет:
                             low     — до $3000
                             medium  — $3000–10000
                             high    — $10000+
                           По умолчанию: medium
                           Пример: --budget medium

  --num-cameras INT        Количество камер.
                           Единица: штук.
                           По умолчанию: 1
                           Пример: --num-cameras 1

  --mount {C,CS,M12,M42,F}
                           Крепление объектива:
                             C    — C-mount (стандарт)
                             CS   — CS-mount (для маленьких сенсоров)
                             M12  — M12 (компактные)
                             M42  — M42 (большие сенсоры)
                             F    — F-mount (Full Frame)
                           По умолчанию: C
                           Пример: --mount C

  --tilt FLOAT             Угол наклона камеры к объекту.
                           Единица: градусы.
                           По умолчанию: 0 (перпендикулярно).
                           Пример: --tilt 15

--------------------------------------------------------------------------------
 РЕЖИМЫ РАБОТЫ
--------------------------------------------------------------------------------

  --gui                    Запустить веб-интерфейс Gradio.
                           Пример: python check_camera.py --gui

  --pdf                    Сохранить PDF-отчёт.
                           Пример: --pdf

  --csv                    Сохранить CSV-отчёт.
                           Пример: --csv

  --plots                  Сохранить графики PNG.
                           Пример: --plots

  --all                    Сохранить всё: PDF + CSV + plots.
                           Пример: --all

  --compare                Сравнить 3预设 конфигурации:
                             Базовая (наклон 0°)
                             Наклон 15°
                             Премиум наклон 30°
                           Пример: python check_camera.py --compare

  --compare-file FILE      Сравнить конфигурации из JSON-файла.
                           Пример: python check_camera.py --compare-file configs.json

  --compare-json JSON      Сравнить конфигурации из JSON-строки.
                           Пример: python check_camera.py --compare-json '[...]'

  --help, -h               Показать эту справку.

--------------------------------------------------------------------------------
 ПРИМЕРЫ
--------------------------------------------------------------------------------

  1) Простой расчёт:
     python check_camera.py --defect-size 0.5 --defect-type displacement \\
       --material metal --reflectivity semi_matte --contrast dark_on_light \\
       --fov-width 500 --fov-height 300 --working-distance 800

  2) С движением и полным экспортом:
     python check_camera.py --defect-size 0.5 --defect-type displacement \\
       --material metal --reflectivity semi_matte --contrast dark_on_light \\
       --fov-width 500 --fov-height 300 --working-distance 800 \\
       --line-speed 1000 --part-spacing 200 --is-moving \\
       --budget medium --all

  3) С наклоном камеры:
     python check_camera.py --defect-size 0.3 --defect-type scratch \\
       --material glass --reflectivity glossy --contrast dark_on_light \\
       --fov-width 300 --fov-height 200 --working-distance 600 \\
       --tilt 15 --budget high --pdf --plots

  4) GUI:
     python check_camera.py --gui

  5) Сравнение预设:
     python check_camera.py --compare

  6) Сравнение из файла:
     python check_camera.py --compare-file configs.json

  7) Сравнение из JSON-строки:
     python check_camera.py --compare-json '[{"name":"A","defect_size_mm":0.5,...}]'

================================================================================
"""


def parse_args():
    """Парсит аргументы командной строки."""
    if len(sys.argv) == 1:
        print(EXTENDED_HELP)
        sys.exit(0)

    parser = argparse.ArgumentParser(
        prog="check_camera.py",
        description=(
            "Калькулятор подбора камеры, объектива и освещения "
            "для промышленного компьютерного зрения.\n"
            "Запустите без аргументов, чтобы увидеть подробную справку."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Пример: python check_camera.py --defect-size 0.5 --defect-type displacement ..."
    )

    # Объект и дефект
    parser.add_argument("--defect-size", type=float, default=0.5,
                        help="Минимальный размер дефекта, мм (по умолчанию: 0.5)")
    parser.add_argument("--defect-type", type=str, default="displacement",
                        choices=["scratch", "chip", "displacement", "missing", "color", "crack"],
                        help="Тип дефекта (по умолчанию: displacement)")
    parser.add_argument("--material", type=str, default="metal",
                        choices=["metal", "plastic", "glass", "fabric", "ceramic"],
                        help="Материал поверхности (по умолчанию: metal)")
    parser.add_argument("--reflectivity", type=str, default="semi_matte",
                        choices=["matte", "semi_matte", "glossy", "mirror"],
                        help="Отражающая способность (по умолчанию: semi_matte)")
    parser.add_argument("--contrast", type=str, default="dark_on_light",
                        choices=["dark_on_light", "light_on_dark", "color"],
                        help="Контраст дефекта (по умолчанию: dark_on_light)")

    # Геометрия
    parser.add_argument("--fov-width", type=float, default=500,
                        help="Ширина поля зрения, мм (по умолчанию: 500)")
    parser.add_argument("--fov-height", type=float, default=300,
                        help="Высота поля зрения, мм (по умолчанию: 300)")
    parser.add_argument("--working-distance", type=float, default=800,
                        help="Рабочая дистанция, мм (по умолчанию: 800)")

    # Движение
    parser.add_argument("--line-speed", type=float, default=0,
                        help="Скорость линии, мм/с (по умолчанию: 0 — статика)")
    parser.add_argument("--part-spacing", type=float, default=200,
                        help="Расстояние между деталями, мм (по умолчанию: 200)")
    parser.add_argument("--images-per-part", type=int, default=1,
                        help="Изображений на деталь (по умолчанию: 1)")
    parser.add_argument("--is-moving", action="store_true",
                        help="Флаг: объект движется (по умолчанию: статика)")

    # Требования
    parser.add_argument("--min-pixels", type=int, default=4,
                        help="Минимум пикселей на дефект (по умолчанию: 4)")
    parser.add_argument("--ambient-light", type=str, default="normal",
                        choices=["bright", "normal", "dim", "dark"],
                        help="Освещение в цеху (по умолчанию: normal)")
    parser.add_argument("--budget", type=str, default="medium",
                        choices=["low", "medium", "high"],
                        help="Бюджет (по умолчанию: medium)")
    parser.add_argument("--num-cameras", type=int, default=1,
                        help="Количество камер (по умолчанию: 1)")
    parser.add_argument("--mount", type=str, default="C",
                        choices=["C", "CS", "M12", "M42", "F"],
                        help="Крепление объектива (по умолчанию: C)")
    parser.add_argument("--tilt", type=float, default=0.0,
                        help="Угол наклона камеры, градусы (по умолчанию: 0)")

    # Режимы
    parser.add_argument("--gui", action="store_true", help="Запустить GUI Gradio")
    parser.add_argument("--pdf", action="store_true", help="Сохранить PDF-отчёт")
    parser.add_argument("--csv", action="store_true", help="Сохранить CSV-отчёт")
    parser.add_argument("--plots", action="store_true", help="Сохранить графики PNG")
    parser.add_argument("--all", action="store_true", help="Сохранить всё: PDF + CSV + plots")
    parser.add_argument("--compare", action="store_true",
                        help="Сравнить 3预设 конфигурации")
    parser.add_argument("--compare-file", type=str, default=None,
                        help="JSON-файл с конфигурациями для сравнения")
    parser.add_argument("--compare-json", type=str, default=None,
                        help="JSON-строка с конфигурациями для сравнения")

    return parser.parse_args()


# --- Маппинги ---

def map_ambient_light(value: str) -> str:
    mapping = {
        "bright": "яркий цех (окна, солнце)",
        "normal": "обычный цех",
        "dim": "тусклый цех",
        "dark": "темнота (кожух)",
    }
    return mapping.get(value, "обычный цех")


def map_defect_type(value: str) -> DefectType:
    mapping = {
        "scratch": DefectType.SCRATCH,
        "chip": DefectType.CHIP,
        "displacement": DefectType.DISPLACEMENT,
        "missing": DefectType.MISSING,
        "color": DefectType.COLOR,
        "crack": DefectType.CRACK,
    }
    return mapping[value]


def map_material(value: str) -> Material:
    mapping = {
        "metal": Material.METAL,
        "plastic": Material.PLASTIC,
        "glass": Material.GLASS,
        "fabric": Material.FABRIC,
        "ceramic": Material.CERAMIC,
    }
    return mapping[value]


def map_reflectivity(value: str) -> Reflectivity:
    mapping = {
        "matte": Reflectivity.MATTE,
        "semi_matte": Reflectivity.SEMI_MATTE,
        "glossy": Reflectivity.GLOSSY,
        "mirror": Reflectivity.MIRROR,
    }
    return mapping[value]


def map_contrast(value: str) -> Contrast:
    mapping = {
        "dark_on_light": Contrast.DARK_ON_LIGHT,
        "light_on_dark": Contrast.LIGHT_ON_DARK,
        "color": Contrast.COLOR,
    }
    return mapping[value]


def map_budget(value: str) -> BudgetLevel:
    mapping = {
        "low": BudgetLevel.LOW,
        "medium": BudgetLevel.MEDIUM,
        "high": BudgetLevel.HIGH,
    }
    return mapping[value]


def map_mount(value: str) -> LensMount:
    mapping = {
        "C": LensMount.C,
        "CS": LensMount.CS,
        "M12": LensMount.M12,
        "M42": LensMount.M42,
        "F": LensMount.F,
    }
    return mapping[value]


def args_to_requirements(args) -> CustomerRequirements:
    return CustomerRequirements(
        defect_size_mm=args.defect_size,
        defect_type=map_defect_type(args.defect_type),
        material=map_material(args.material),
        reflectivity=map_reflectivity(args.reflectivity),
        contrast=map_contrast(args.contrast),
        fov_width_mm=args.fov_width,
        fov_height_mm=args.fov_height,
        working_distance_mm=args.working_distance,
        line_speed_mm_s=args.line_speed,
        part_spacing_mm=args.part_spacing,
        images_per_part=args.images_per_part,
        is_moving=args.is_moving,
        min_pixels_per_defect=args.min_pixels,
        ambient_light=map_ambient_light(args.ambient_light),
        budget=map_budget(args.budget),
        num_cameras=args.num_cameras,
        preferred_mount=map_mount(args.mount),
        camera_tilt_deg=args.tilt,
    )


# --- Загрузка конфигураций из JSON ---

def load_configs_from_json(json_data: str) -> tuple:
    """
    Загружает конфигурации из JSON-строки.

    Формат:
    [
      {"name": "Базовая", "defect_size_mm": 0.5, ...},
      ...
    ]

    Возвращает (names, requirements).
    """
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        print(f"ОШИБКА: невалидный JSON: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("ОШИБКА: JSON должен быть списком конфигураций.")
        sys.exit(1)

    names = []
    requirements = []

    for i, item in enumerate(data):
        name = item.get("name", f"Конфигурация {i+1}")
        names.append(name)
        try:
            req = CustomerRequirements(
                defect_size_mm=float(item.get("defect_size_mm", 0.5)),
                defect_type=map_defect_type(item.get("defect_type", "displacement")),
                material=map_material(item.get("material", "metal")),
                reflectivity=map_reflectivity(item.get("reflectivity", "semi_matte")),
                contrast=map_contrast(item.get("contrast", "dark_on_light")),
                fov_width_mm=float(item.get("fov_width_mm", 500)),
                fov_height_mm=float(item.get("fov_height_mm", 300)),
                working_distance_mm=float(item.get("working_distance_mm", 800)),
                line_speed_mm_s=float(item.get("line_speed_mm_s", 0)),
                part_spacing_mm=float(item.get("part_spacing_mm", 200)),
                images_per_part=int(item.get("images_per_part", 1)),
                is_moving=bool(item.get("is_moving", False)),
                min_pixels_per_defect=int(item.get("min_pixels_per_defect", 4)),
                ambient_light=map_ambient_light(item.get("ambient_light", "normal")),
                budget=map_budget(item.get("budget", "medium")),
                num_cameras=int(item.get("num_cameras", 1)),
                preferred_mount=map_mount(item.get("preferred_mount", "C")),
                camera_tilt_deg=float(item.get("camera_tilt_deg", 0.0)),
            )
            requirements.append(req)
        except (KeyError, ValueError) as e:
            print(f"ОШИБКА в конфигурации '{name}': {e}")
            sys.exit(1)

    return names, requirements


def load_configs_from_file(filepath: str) -> tuple:
    if not os.path.exists(filepath):
        print(f"ОШИБКА: файл не найден: {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return load_configs_from_json(content)


# --- Режимы ---

def run_compare_mode_from_configs(names: List[str], requirements: List[CustomerRequirements]):
    """Универсальный режим сравнения."""
    if not requirements:
        print("Нет конфигураций для сравнения.")
        return

    configs = []
    for req in requirements:
        rec = select_camera_system(req)
        configs.append(rec)
        print_recommendation(rec, req)
        print("\n")

    comparison = compare_configurations(configs, names)
    print(comparison)

    visualize_recommendation(configs[0], requirements[0])
    export_to_pdf(configs[0], requirements[0])
    export_to_csv(configs[0], requirements[0])
    export_comparison_to_csv(configs, names)


def run_compare_mode_default():
    """预设: три конфигурации."""
    req1 = CustomerRequirements(
        defect_size_mm=0.5, defect_type=DefectType.DISPLACEMENT,
        material=Material.METAL, reflectivity=Reflectivity.SEMI_MATTE,
        contrast=Contrast.DARK_ON_LIGHT,
        fov_width_mm=500, fov_height_mm=300, working_distance_mm=800,
        line_speed_mm_s=1000, part_spacing_mm=200, images_per_part=1,
        is_moving=True, min_pixels_per_defect=4,
        ambient_light="обычный цех", budget=BudgetLevel.MEDIUM,
        num_cameras=1, preferred_mount=LensMount.C, camera_tilt_deg=0.0,
    )
    req2 = CustomerRequirements(
        defect_size_mm=0.5, defect_type=DefectType.DISPLACEMENT,
        material=Material.METAL, reflectivity=Reflectivity.SEMI_MATTE,
        contrast=Contrast.DARK_ON_LIGHT,
        fov_width_mm=500, fov_height_mm=300, working_distance_mm=800,
        line_speed_mm_s=1000, part_spacing_mm=200, images_per_part=1,
        is_moving=True, min_pixels_per_defect=4,
        ambient_light="обычный цех", budget=BudgetLevel.LOW,
        num_cameras=1, preferred_mount=LensMount.C, camera_tilt_deg=15.0,
    )
    req3 = CustomerRequirements(
        defect_size_mm=0.3, defect_type=DefectType.SCRATCH,
        material=Material.GLASS, reflectivity=Reflectivity.GLOSSY,
        contrast=Contrast.DARK_ON_LIGHT,
        fov_width_mm=300, fov_height_mm=200, working_distance_mm=600,
        line_speed_mm_s=500, part_spacing_mm=100, images_per_part=2,
        is_moving=True, min_pixels_per_defect=5,
        ambient_light="яркий цех (окна, солнце)", budget=BudgetLevel.HIGH,
        num_cameras=2, preferred_mount=LensMount.C, camera_tilt_deg=30.0,
    )
    names = ["Базовая", "Наклон 15°", "Премиум наклон 30°"]
    run_compare_mode_from_configs(names, [req1, req2, req3])


def run_single_mode(args):
    """Одиночный расчёт."""
    req = args_to_requirements(args)
    rec = select_camera_system(req)

    print_recommendation(rec, req)

    if args.all or args.plots:
        visualize_recommendation(rec, req)

    if args.all or args.pdf:
        plot_file = "recommendation_plots.png" if (args.all or args.plots) else None
        export_to_pdf(rec, req, plot_filename=plot_file)

    if args.all or args.csv:
        export_to_csv(rec, req)


def main():
    """Точка входа."""
    args = parse_args()

    # GUI
    if args.gui:
        if GRADIO_AVAILABLE:
            interface = build_gradio_interface()
            if interface:
                interface.launch()
        else:
            print("Gradio не установлен. Установите: pip install gradio")
        return

    # Compare из JSON-строки
    if args.compare_json:
        names, reqs = load_configs_from_json(args.compare_json)
        run_compare_mode_from_configs(names, reqs)
        return

    # Compare из файла
    if args.compare_file:
        names, reqs = load_configs_from_file(args.compare_file)
        run_compare_mode_from_configs(names, reqs)
        return

    # Compare预设
    if args.compare:
        run_compare_mode_default()
        return

    # Одиночный расчёт
    run_single_mode(args)


if __name__ == "__main__":
    main()

# Установка зависимостей
#pip install fpdf2 gradio matplotlib

# Без аргументов — подробная справка
#python check_camera.py

# Простой расчёт
#python check_camera.py --defect-size 0.5 --defect-type displacement \
#  --material metal --reflectivity semi_matte --contrast dark_on_light \
#  --fov-width 500 --fov-height 300 --working-distance 800

# С движением и экспортом
#python check_camera.py --defect-size 0.5 --defect-type displacement \
#  --material metal --reflectivity semi_matte --contrast dark_on_light \
#  --fov-width 500 --fov-height 300 --working-distance 800 \
#  --line-speed 1000 --part-spacing 200 --is-moving \
#  --budget medium --all

# С наклоном
#python check_camera.py --defect-size 0.3 --defect-type scratch \
#  --material glass --reflectivity glossy --contrast dark_on_light \
#  --fov-width 300 --fov-height 200 --working-distance 600 \
#  --tilt 15 --budget high --pdf --plots

# GUI
#python check_camera.py --gui

# Сравнение
#python check_camera.py --compare

# Сравнение из файла
#python check_camera.py --compare-file configs.json

# Сравнение из JSON-строки
#python check_camera.py --compare-json '[{"name":"A","defect_size_mm":0.5}]'
