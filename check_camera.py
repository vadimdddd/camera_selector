"""
================================================================================
КАЛЬКУЛЯТОР ПОДБОРА КАМЕРЫ, ОБЪЕКТИВА И ОСВЕЩЕНИЯ
ДЛЯ ПРОМЫШЛЕННОГО КОМПЬЮТЕРНОГО ЗРЕНИЯ
================================================================================

ВОЗМОЖНОСТИ
--------------------------------------------------------------------------------
  - Подбор камеры по разрешению, затвору, FPS, интерфейсу, бюджету
    (только USB3 Vision и GigE Vision — CoaXPress, 10GigE и прочее исключены)
  - Ограничение по брендам: только проверенные промышленные производители
    (Hikrobot, Daheng Imaging, Basler China, Huaray, Wuxi Bopixel)
  - Автоматическая дедупликация базы камер по (vendor, model)
  - Подбор объектива с проверкой:
      * совместимости крепления (C / CS / M12 / M42 / M58 / F)
      * покрытия сенсора (виньетирование)
      * покрытия FOV по ширине И по высоте
  - Расчёт угла обзора (HFOV, VFOV, DFOV)
  - Проверка фактического FOV на рабочей дистанции против требуемого
  - Расчёт угла наклона камеры (tilt) и компенсации перспективы
  - Расчёт глубины резкости (DOF) через гиперфокальное расстояние
  - Расчёт требуемой освещённости (люкс) и мощности света (Вт)
  - Логика автоопределения необходимости света:
      * "needed"      — свет обязателен
      * "borderline"  — на грани, желателен
      * "not_needed"  — достаточно рабочего света цеха
      * режимы: auto / on / off (--lighting)
  - Подбор конкретной модели света из базы (CCS, Advanced Illumination,
    Smart Vision Lights)
  - Проверка пропускной способности интерфейса (Мбит/с) с запасом 80%
  - Проверка максимальной длины кабеля (USB3 ≈ 4.6 м, GigE ≈ 100 м)
  - Проверка пропорций FOV vs сенсора (landscape/portrait)
  - Расчёт количества камер для покрытия зоны (--total-area-width/height)
    с учётом перекрытия (--overlap-pct)
  - Мультивариантный вывод: все подходящие камеры группируются по запасу
      * 🟢 минимальный запас (до ×1.10) — оптимум по цене
      * 🟡 умеренный запас (×1.11–1.20) — компромисс
      * 🔴 с запасом (> ×1.20) — на вырост
  - Подсказки при отсутствии решений (что уменьшить/увеличить)
  - Сравнение нескольких конфигураций (предустановки / JSON-файл / JSON-строка)
  - Визуализация (FOV, DOF, бюджет, наклон) через matplotlib
  - Экспорт в PDF (со встроенными PNG) и CSV
  - GUI на Gradio
  - CLI через argparse

РЕЖИМЫ РАБОТЫ
--------------------------------------------------------------------------------
  inspection  — инспекция дефектов (по умолчанию)
  tracking    — трекинг движущихся объектов (FPS от скорости и допустимого
                смещения: fps = object_speed / (defect_size × shift_ratio),
                минимум 25 FPS)
  detection   — детекция объектов (крупные объекты, мягкие требования к свету)

АВТООПРЕДЕЛЕНИЕ СВЕТА (--lighting auto | on | off)
--------------------------------------------------------------------------------
  off  — свет принудительно отключён
  on   — свет принудительно включён
  auto — эвристика:
           * tracking/detection + крупный объект + светлый цех → не нужен
           * tracking/detection + тёмный цех                → нужен
           * очень короткая выдержка (< 0.5 мс)              → нужен
           * зеркальная поверхность                          → нужен
           * мелкий дефект (< 0.5 мм)                        → нужен
           * мелкий дефект + короткая выдержка               → нужен
           * тёмный цех (< 100 лк)                           → нужен
           * крупный дефект + длинная выдержка + светлый цех → не нужен
           * промежуточные случаи                            → borderline

ПРОВЕРКА ПРОПУСКНОЙ СПОСОБНОСТИ
--------------------------------------------------------------------------------
  Требуемая полоса (Мбит/с):
      area-камеры:     width × height × fps × bit_depth / 1e6
      линейные:        width × line_rate × bit_depth / 1e6

  Лимиты интерфейсов (с запасом 80%):
      USB3 : 5000 Мбит/с → эффективно ~4000 Мбит/с
      GigE : 1000 Мбит/с → эффективно ~800  Мбит/с

  Камеры, не проходящие по полосе, автоматически исключаются из вариантов.

ГРУППИРОВКА ВАРИАНТОВ
--------------------------------------------------------------------------------
  overall_factor = min(разрешение / требуемое, макс.FPS / требуемый FPS)

  Чем ближе к 1.0, тем плотнее камера «сидит» на требованиях (дешевле).
  Чем больше запас, тем дороже, но устойчивее к росту задачи.

  Группы:
      🟢 ≤ 1.10 — минимальный запас (обычно лучший выбор по цене)
      🟡 1.11–1.20 — умеренный запас
      🔴 > 1.20 — с большим запасом (на будущее)

УСТАНОВКА
--------------------------------------------------------------------------------
  pip install fpdf2 gradio matplotlib numpy

ЗАПУСК
--------------------------------------------------------------------------------
  python check_camera.py                  # краткая подсказка
  python check_camera.py --help           # справка argparse
  python check_camera.py [ОПЦИИ]          # одиночный расчёт
  python check_camera.py --gui            # веб-интерфейс Gradio
  python check_camera.py --pdf --csv --plots
  python check_camera.py --all            # PDF + CSV + графики

ОСНОВНЫЕ АРГУМЕНТЫ CLI
--------------------------------------------------------------------------------
  Объект и дефект:
    --defect-size FLOAT        размер дефекта, мм (по умолчанию 0.5)
    --defect-type {scratch,chip,displacement,missing,color,crack}
    --material {metal,plastic,glass,fabric,ceramic}
    --reflectivity {matte,semi_matte,glossy,mirror}
    --contrast {dark_on_light,light_on_dark,color}

  Геометрия:
    --fov-width FLOAT          ширина FOV, мм (500)
    --fov-height FLOAT         высота FOV, мм (300)
    --working-distance FLOAT   рабочая дистанция, мм (800)
    --tilt FLOAT               угол наклона камеры, ° (0)
    --server-distance FLOAT    расстояние до сервера, м (3.0)
    --mount {C,CS,M12,M42,M58,F}

  Движение:
    --line-speed FLOAT         скорость линии, мм/с (0)
    --part-spacing FLOAT       расстояние между деталями, мм (200)
    --images-per-part INT      кадров на деталь (1)
    --is-moving                флаг: объект движется

  Задача:
    --task-type {inspection,tracking,detection}   (inspection)
    --object-speed FLOAT       скорость объекта для tracking, мм/с (0)
    --shift-ratio FLOAT        допустимое смещение (доля размера) (0.3)

  Требования:
    --min-pixels INT           мин. пикселей на дефект (4)
    --ambient-light {bright,normal,dim,dark}      (normal)
    --budget {low,medium,high}                    (medium)
    --num-cameras INT                             (1)
    --lighting {auto,on,off}                      (auto)

  Зона покрытия (опционально):
    --total-area-width FLOAT   ширина зоны, м (0 — не задано)
    --total-area-height FLOAT  высота зоны, м (0 — не задано)
    --overlap-pct FLOAT        перекрытие кадров, % (20)

  Экспорт:
    --pdf / --csv / --plots / --all

  GUI:
    --gui

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

  3) Трекинг объекта:
     python check_camera.py --task-type tracking --object-speed 2000 \\
       --shift-ratio 0.3 --defect-size 5 --fov-width 400 --fov-height 300 \\
       --working-distance 600 --line-speed 2000 --is-moving

  4) С наклоном камеры:
     python check_camera.py --defect-size 0.3 --defect-type scratch \\
       --material glass --reflectivity glossy --contrast dark_on_light \\
       --fov-width 300 --fov-height 200 --working-distance 600 \\
       --tilt 15 --budget high --pdf --plots

  5) Свет принудительно включён:
     python check_camera.py ... --lighting on

  6) Зона покрытия 3×2 м, перекрытие 25%:
     python check_camera.py ... --total-area-width 3 --total-area-height 2 \\
       --overlap-pct 25

  7) GUI:
     python check_camera.py --gui

СТРУКТУРА КОДА
--------------------------------------------------------------------------------
  Раздел 1   Справочники (разрешения, сенсоры, свет, камеры, объективы, свет)
  Раздел 2   Перечисления (DefectType, Material, Reflectivity, Contrast,
             BudgetLevel, LensMount, TaskType)
  Раздел 3   Структуры данных (CustomerRequirements, CameraVariant,
             CameraRecommendation)
  Раздел 4   Функции расчёта (разрешение, выдержка, FPS, фокус, FOV, DOF,
             освещённость, мощность света, пропускная способность)
  Раздел 4b  Логика автоопределения света (decide_lighting_needed)
  Раздел 5   Выбор оборудования (камеры, объективы, свет, совместимость)
  Раздел 6   Главная функция (select_camera_system)
  Раздел 7   Визуализация (matplotlib)
  Раздел 8   Сравнение конфигураций
  Раздел 9   Форматирование текстового вывода
  Раздел 10  Экспорт PDF
  Раздел 11  Экспорт CSV
  Раздел 12  GUI на Gradio
  Раздел 13  CLI через argparse

ОГРАНИЧЕНИЯ
--------------------------------------------------------------------------------
  - База камер ограничена USB3 и GigE. CoaXPress, 10GigE, Camera Link
    и другие высокоскоростные интерфейсы не поддерживаются.
  - База камер ограничена проверенными промышленными брендами
    (см. ALLOWED_VENDORS). Любительские и полупромышленные бренды
    отфильтрованы.
  - Расчёт освещённости — оценочный, основан на упрощённой модели
    (чувствительность сенсора, диафрагма, выдержка, отражательность,
    фоновая засветка). Реальные условия могут требовать поправок.
  - Расчёт DOF использует кружок рассеяния 0.005 мм по умолчанию.
  - Перспективные искажения оцениваются упрощённо (через tan угла наклона),
    без полной проективной геометрии.

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

try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("ВНИМАНИЕ: fpdf2 не установлена. PDF не будет создан.")

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

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
    (640, 480), (720, 540), (800, 600), (816, 624),
    (1280, 720), (1280, 1024),
    (1440, 1080), (1600, 1200), (1620, 1240),
    (1920, 1080), (1920, 1200), (2048, 1200),
    (2048, 1536), (2080, 1544), (2448, 2048), (2592, 1944),
    (2848, 2848), (3072, 2048), (3088, 2064), (3840, 2160),
    (3840, 2748), (4024, 3036), (4096, 2160), (4096, 3000),
    (4096, 3072), (4112, 3008), (4504, 4504), (4608, 3072),
    (4912, 3684), (5120, 5120), (5320, 4600), (5472, 3648),
    (6500, 5000), (8192, 5460),
    (2048, 2), (4096, 2), (8192, 2), (10240, 2),
]

# ------------------------------------------------------------------------------
# 1.2 РАЗМЕРЫ СЕНСОРОВ (физическая ширина в мм)
# ------------------------------------------------------------------------------
SENSOR_WIDTH_MM = {
    '1/4"': 3.2, '1/3"': 4.8, '1/2.9"': 5.6, '1/2.5"': 5.8,
    '1/2"': 6.4, '1/1.8"': 7.2, '1/1.7"': 7.6, '1/1.2"': 10.6,
    '2/3"': 8.8, '1"': 12.8, '1.1"': 14.1, '1.4"': 16.0,
    '4/3"': 17.3, 'APS-C': 23.6, 'Full Frame': 36.0,
    'Medium Format': 53.7, 'Line': 0.0,
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
# 1.6 МАКСИМАЛЬНАЯ ДЛИНА КАБЕЛЯ ПО ИНТЕРФЕЙСУ (метры)
# ------------------------------------------------------------------------------
INTERFACE_MAX_DISTANCE_M = {
    'USB3': 4.6,
    'GigE': 100,
}

# ------------------------------------------------------------------------------
# 1.7 ПРОПУСКНАЯ СПОСОБНОСТЬ ИНТЕРФЕЙСОВ (Мбит/с)
# ------------------------------------------------------------------------------
INTERFACE_BANDWIDTH_MBPS = {
    'USB3': 5000,   # 5 Гбит/с (реально ~3.5 Гбит/с)
    'GigE': 1000,   # 1 Гбит/с (реально ~950 Мбит/с)
}

# Запас по пропускной способности (реально ~80% от теоретической)
INTERFACE_BANDWIDTH_SAFETY = 0.8

# ------------------------------------------------------------------------------
# 1.8 РАЗРЕШЁННЫЕ ИНТЕРФЕЙСЫ (только USB3 и GigE)
# ------------------------------------------------------------------------------
ALLOWED_INTERFACES = {'USB3', 'GigE'}

# ------------------------------------------------------------------------------
# 1.9 БЕЛЫЙ СПИСОК БРЕНДОВ (только проверенные промышленные)
# ------------------------------------------------------------------------------
ALLOWED_VENDORS = {
    'Hikrobot',
    'Daheng Imaging',
    'Basler China',
    'Huaray',
    'Wuxi Bopixel',
}

# ------------------------------------------------------------------------------
# 1.10 БАЗА ДАННЫХ КАМЕР
# Формат: model, vendor, resolution, sensor_format, shutter, max_fps,
#         interface, mount, price_usd, type, mono_color, pixel_size_um,
#         poe_support, ip_rating, notes
# ------------------------------------------------------------------------------
CAMERA_DATABASE = [
    # ==========================================================================
    # HIKROBOT
    # ==========================================================================
    {'model': 'MV-CA003-20GM', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 200,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 200,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': 'VGA @ 200 FPS.'},

    {'model': 'MV-CA003-20UM', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 200,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 190,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'VGA @ 200 FPS. USB3.'},

    {'model': 'MV-CA003-20UC', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 200,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 210,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'VGA @ 200 FPS, цветная.'},

    {'model': 'MV-CA013-20GM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 280,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS.'},

    {'model': 'MV-CA013-20GC', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 320,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS, цветная.'},

    {'model': 'MV-CA013-20UM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 90,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 290,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 90 FPS. USB3.'},

    {'model': 'MV-CA050-10GM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 550,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    {'model': 'MV-CA050-10GC', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 600,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS, цветная.'},

    {'model': 'MV-CA050-20UM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 500,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 40 FPS. USB3.'},

    {'model': 'MV-CA050-20UC', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 560,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 40 FPS, цветная.'},

    {'model': 'MV-CA060-10GM', 'vendor': 'Hikrobot', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Rolling', 'max_fps': 30,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 600,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 30 FPS. Rolling.'},

    {'model': 'MV-CA120-10GM', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 900,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS.'},

    {'model': 'MV-CS003-10UM', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 360,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 300,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 6.9,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'VGA @ 360 FPS, Sony.'},

    {'model': 'MV-CS003-10UC', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 360,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 310,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 6.9,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'VGA @ 360 FPS, цветная.'},

    {'model': 'MV-CS004-10GM', 'vendor': 'Hikrobot', 'resolution': (720, 540),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 260,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 350,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 6.9,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '0.4 Мп @ 260 FPS, Sony.'},

    {'model': 'MV-CS013-10GM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 88,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 350,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 88 FPS. Sony.'},

    {'model': 'MV-CS013-10GC', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 88,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 400,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 88 FPS, цветная.'},

    {'model': 'MV-CS013-10UM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 150,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 380,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 150 FPS. USB3.'},

    {'model': 'MV-CS013-10UC', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 150,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 430,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 150 FPS, цветная.'},

    {'model': 'MV-CS016-10GM', 'vendor': 'Hikrobot', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 80,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 380,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 80 FPS. Sony.'},

    {'model': 'MV-CS016-10GC', 'vendor': 'Hikrobot', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 80,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 420,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 80 FPS, цветная.'},

    {'model': 'MV-CS016-10UM', 'vendor': 'Hikrobot', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 160,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 420,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 160 FPS. USB3.'},

    {'model': 'MV-CS020-10GM', 'vendor': 'Hikrobot', 'resolution': (1620, 1240),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 480,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2 Мп @ 60 FPS. Sony.'},

    {'model': 'MV-CS020-10UC', 'vendor': 'Hikrobot', 'resolution': (1620, 1240),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 460,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.5,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '2 Мп @ 60 FPS, цветная.'},

    {'model': 'MV-CS050-10GM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 620,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS. Sony.'},

    {'model': 'MV-CS050-10GC', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 680,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS, цветная.'},

    {'model': 'MV-CS050-30UM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 720,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 60 FPS. USB3.'},

    {'model': 'MV-CS050-30UC', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 800,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 60 FPS, цветная.'},

    {'model': 'MV-CS060-10GM', 'vendor': 'Hikrobot', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 18,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 580,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 18 FPS.'},

    {'model': 'MV-CS060-10GC', 'vendor': 'Hikrobot', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 18,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 640,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 18 FPS, цветная.'},

    {'model': 'MV-CS080-10GM', 'vendor': 'Hikrobot', 'resolution': (2848, 2848),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 15,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 780,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.74,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '8 Мп @ 15 FPS.'},

    {'model': 'MV-CS120-10GM', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 850,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS. Sony.'},

    {'model': 'MV-CS120-10UC', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 10,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 980,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS, цветная.'},

    {'model': 'MV-CS200-10GM', 'vendor': 'Hikrobot', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 5,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1250,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '20 Мп @ 5 FPS.'},

    {'model': 'MV-CU003-10UM', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 260,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 180,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'VGA @ 260 FPS.'},

    {'model': 'MV-CU003-10GM', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 260,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 160,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': 'VGA @ 260 FPS. Самый дешёвый.'},

    {'model': 'MV-CU004-10UM', 'vendor': 'Hikrobot', 'resolution': (720, 540),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 250,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 190,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 6.9,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '0.4 Мп @ 250 FPS.'},

    {'model': 'MV-CU013-10GM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 100,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 320,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 100 FPS.'},

    {'model': 'MV-CU013-10GC', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 100,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 360,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 100 FPS, цветная.'},

    {'model': 'MV-CU013-20UM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 160,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 260,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 160 FPS.'},

    {'model': 'MV-CU016-10GM', 'vendor': 'Hikrobot', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 80,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 350,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 80 FPS.'},

    {'model': 'MV-CU020-10GM', 'vendor': 'Hikrobot', 'resolution': (1620, 1240),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 420,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2 Мп @ 60 FPS.'},

    {'model': 'MV-CU050-10GM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 520,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    {'model': 'MV-CU050-10GC', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 580,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS, цветная.'},

    {'model': 'MV-CU050-20GM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 600,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 40 FPS.'},

    {'model': 'MV-CU060-10UM', 'vendor': 'Hikrobot', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 30,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 640,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '6 Мп @ 30 FPS. USB3.'},

    {'model': 'MV-CU060-10GC', 'vendor': 'Hikrobot', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 20,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 680,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 20 FPS, цветная.'},

    {'model': 'MV-CU120-10GM', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 780,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS.'},

    {'model': 'MV-CU120-10UC', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 10,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 850,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS, цветная.'},

    {'model': 'MV-CH050-10UM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 74,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 500,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 74 FPS. USB3.'},

    {'model': 'MV-CH050-10GM', 'vendor': 'Hikrobot', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 780,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 40 FPS.'},

    {'model': 'MV-CH089-10UM', 'vendor': 'Hikrobot', 'resolution': (4096, 2160),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 45,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 1100,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '9 Мп @ 45 FPS, 4K. USB3.'},

    {'model': 'MV-CH089-10GM', 'vendor': 'Hikrobot', 'resolution': (4096, 2160),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 25,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1250,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '9 Мп @ 25 FPS, 4K.'},

    {'model': 'MV-CH120-10UM', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 32,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 1400,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '12 Мп @ 32 FPS. USB3.'},

    {'model': 'MV-CH200-10GM', 'vendor': 'Hikrobot', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1400,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '20 Мп @ 10 FPS.'},

    # --- MV-CL линейные сканеры (только GigE) ---
    {'model': 'MV-CL021-40GM', 'vendor': 'Hikrobot', 'resolution': (2048, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 40000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 800,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 7.0,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2K линейный, 40 кГц.'},

    {'model': 'MV-CL042-91GC', 'vendor': 'Hikrobot', 'resolution': (4096, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 91000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 950,
     'type': 'line', 'mono_color': 'Color', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '4K линейный, 91 кГц, цветной.'},

    {'model': 'MV-CL042-91GM', 'vendor': 'Hikrobot', 'resolution': (4096, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 91000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 900,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '4K линейный, 91 кГц.'},

    {'model': 'MV-CL086-41GM', 'vendor': 'Hikrobot', 'resolution': (8192, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 41000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 1300,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '8K линейный, 41 кГц.'},

    {'model': 'MV-CL104-23GC', 'vendor': 'Hikrobot', 'resolution': (10240, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 23000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 1300,
     'type': 'line', 'mono_color': 'Color', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '10K линейный, 23 кГц, цветной.'},

    # --- MV-CE entry-level ---
    {'model': 'MV-CE003-20GM', 'vendor': 'Hikrobot', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Rolling', 'max_fps': 200,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 130,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': 'VGA @ 200 FPS. Entry-level.'},

    {'model': 'MV-CE013-50GM', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Rolling', 'max_fps': 50,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 180,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 50 FPS. Entry-level.'},

    {'model': 'MV-CE013-50GC', 'vendor': 'Hikrobot', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Rolling', 'max_fps': 50,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 220,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 50 FPS, цветная.'},

    {'model': 'MV-CE060-10GC', 'vendor': 'Hikrobot', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Rolling', 'max_fps': 20,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 550,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 20 FPS, цветная.'},

    {'model': 'MV-CE120-10GC', 'vendor': 'Hikrobot', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 780,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS, цветная.'},

    # ==========================================================================
    # DAHENG IMAGING
    # ==========================================================================
    {'model': 'MER-030-120UM', 'vendor': 'Daheng Imaging', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 120,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 210,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'VGA @ 120 FPS. USB3.'},

    {'model': 'MER-131-75GM', 'vendor': 'Daheng Imaging', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 75,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 350,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 75 FPS.'},

    {'model': 'MER-131-210U3M', 'vendor': 'Daheng Imaging', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 210,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 550,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 210 FPS. USB3.'},

    {'model': 'MER-132-43GC', 'vendor': 'Daheng Imaging', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 43,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 380,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 43 FPS, цветная.'},

    {'model': 'MER-200-20GM', 'vendor': 'Daheng Imaging', 'resolution': (1600, 1200),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 20,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 400,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2 Мп @ 20 FPS.'},

    {'model': 'MER-230-168U3M', 'vendor': 'Daheng Imaging', 'resolution': (1920, 1200),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 168,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 750,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '2.3 Мп @ 168 FPS.'},

    {'model': 'MER-500-7UM', 'vendor': 'Daheng Imaging', 'resolution': (2592, 1944),
     'sensor_format': '1/2.5"', 'shutter': 'Rolling', 'max_fps': 7,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 500,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.2,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 7 FPS.'},

    {'model': 'MER-500-14GM', 'vendor': 'Daheng Imaging', 'resolution': (2592, 1944),
     'sensor_format': '1/2.5"', 'shutter': 'Rolling', 'max_fps': 14,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 600,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.2,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 14 FPS.'},

    {'model': 'MER-1070-10GM', 'vendor': 'Daheng Imaging', 'resolution': (3840, 2748),
     'sensor_format': '1/1.7"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 880,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 1.67,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '10 Мп @ 10 FPS.'},

    {'model': 'MER-2000-10GM', 'vendor': 'Daheng Imaging', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1300,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '20 Мп @ 10 FPS.'},

    {'model': 'MER2-041-302U3M', 'vendor': 'Daheng Imaging', 'resolution': (720, 540),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 302,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 300,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 6.9,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '0.4 Мп @ 302 FPS.'},

    {'model': 'MER2-041-302GM', 'vendor': 'Daheng Imaging', 'resolution': (720, 540),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 302,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 450,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 6.9,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '0.4 Мп @ 302 FPS. GigE.'},

    {'model': 'MER2-051-25U3M', 'vendor': 'Daheng Imaging', 'resolution': (816, 624),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 250,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 280,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '0.5 Мп @ 250 FPS.'},

    {'model': 'MER2-132-30U3C', 'vendor': 'Daheng Imaging', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 420,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS, цветная.'},

    {'model': 'MER2-132-60U3M', 'vendor': 'Daheng Imaging', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 400,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS.'},

    {'model': 'MER2-160-227U3M', 'vendor': 'Daheng Imaging', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 227,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 350,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 227 FPS.'},

    {'model': 'MER2-160-130GM', 'vendor': 'Daheng Imaging', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 130,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 600,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 130 FPS.'},

    {'model': 'MER2-202-60GM', 'vendor': 'Daheng Imaging', 'resolution': (1600, 1200),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 610,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2 Мп @ 60 FPS.'},

    {'model': 'MER2-231-41U3M', 'vendor': 'Daheng Imaging', 'resolution': (1920, 1200),
     'sensor_format': '1/1.2"', 'shutter': 'Global', 'max_fps': 41,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 600,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '2.3 Мп @ 41 FPS.'},

    {'model': 'MER2-231-50GM', 'vendor': 'Daheng Imaging', 'resolution': (1920, 1200),
     'sensor_format': '1/1.2"', 'shutter': 'Global', 'max_fps': 50,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 720,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2.3 Мп @ 50 FPS.'},

    {'model': 'MER2-302-30GM', 'vendor': 'Daheng Imaging', 'resolution': (2048, 1536),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 30,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 580,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '3 Мп @ 30 FPS.'},

    {'model': 'MER2-302-37U3M', 'vendor': 'Daheng Imaging', 'resolution': (2048, 1536),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 37,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 500,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '3 Мп @ 37 FPS.'},

    {'model': 'MER2-302-60GM', 'vendor': 'Daheng Imaging', 'resolution': (2048, 1536),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 680,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '3 Мп @ 60 FPS.'},

    {'model': 'MER2-302-125U3M', 'vendor': 'Daheng Imaging', 'resolution': (2048, 1536),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 125,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 780,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '3 Мп @ 125 FPS.'},

    {'model': 'MER2-503-23U3M', 'vendor': 'Daheng Imaging', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 520,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    {'model': 'MER2-503-23GM', 'vendor': 'Daheng Imaging', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 680,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    {'model': 'MER2-503-36U3M', 'vendor': 'Daheng Imaging', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 36,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 620,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 36 FPS.'},

    {'model': 'MER2-503-60GM', 'vendor': 'Daheng Imaging', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 880,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 60 FPS.'},

    {'model': 'MER2-503-84U3M', 'vendor': 'Daheng Imaging', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 84,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 950,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 84 FPS. USB3.'},

    {'model': 'MER2-503-84GM', 'vendor': 'Daheng Imaging', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 84,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1080,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 84 FPS. GigE.'},

    {'model': 'MER2-630-18GM', 'vendor': 'Daheng Imaging', 'resolution': (3088, 2064),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 18,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 750,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 18 FPS.'},

    {'model': 'MER2-630-30U3M', 'vendor': 'Daheng Imaging', 'resolution': (3088, 2064),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 30,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 850,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '6 Мп @ 30 FPS.'},

    {'model': 'MER2-630-30GM', 'vendor': 'Daheng Imaging', 'resolution': (3088, 2064),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 30,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 950,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 30 FPS.'},

    {'model': 'MER2-1000-7UM', 'vendor': 'Daheng Imaging', 'resolution': (3840, 2748),
     'sensor_format': '1/1.7"', 'shutter': 'Rolling', 'max_fps': 7,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 750,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 1.67,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '10 Мп @ 7 FPS.'},

    {'model': 'MER2-1220-32U3M', 'vendor': 'Daheng Imaging', 'resolution': (4024, 3036),
     'sensor_format': '1/1.7"', 'shutter': 'Global', 'max_fps': 32,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 1200,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 1.85,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '12 Мп @ 32 FPS.'},

    {'model': 'MER2-1220-32GM', 'vendor': 'Daheng Imaging', 'resolution': (4024, 3036),
     'sensor_format': '1/1.7"', 'shutter': 'Global', 'max_fps': 32,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1280,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 1.85,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '12 Мп @ 32 FPS.'},

    {'model': 'MER2-2000-8UM', 'vendor': 'Daheng Imaging', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 8,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 1300,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '20 Мп @ 8 FPS.'},

    # --- MER-L линейные сканеры ---
    {'model': 'MER2-702-20GM-L', 'vendor': 'Daheng Imaging', 'resolution': (2048, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 52000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 850,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 7.0,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2K линейный, 52 кГц.'},

    {'model': 'MER2-1204-13GM-L', 'vendor': 'Daheng Imaging', 'resolution': (4096, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 45000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 1050,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '4K линейный, 45 кГц.'},

    {'model': 'MER2-2406-14GM-L', 'vendor': 'Daheng Imaging', 'resolution': (8192, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 28000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 1400,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '8K линейный, 28 кГц.'},

    # ==========================================================================
    # BASLER CHINA
    # ==========================================================================
    {'model': 'a2A1920-51gmPRO-CN', 'vendor': 'Basler China', 'resolution': (1920, 1080),
     'sensor_format': '1/2.3"', 'shutter': 'Global', 'max_fps': 51,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 550,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.9,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': 'HD @ 51 FPS.'},

    {'model': 'a2A1920-160umPRO-CN', 'vendor': 'Basler China', 'resolution': (1920, 1080),
     'sensor_format': '1/2.3"', 'shutter': 'Global', 'max_fps': 160,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 500,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.9,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'HD @ 160 FPS. USB3.'},

    {'model': 'a2A2590-60umPRO-CN', 'vendor': 'Basler China', 'resolution': (2592, 1944),
     'sensor_format': '1/2.5"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 720,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.2,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 60 FPS.'},

    {'model': 'a2A2600-20gmPRO-CN', 'vendor': 'Basler China', 'resolution': (2592, 1944),
     'sensor_format': '1/2.5"', 'shutter': 'Global', 'max_fps': 20,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 680,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.2,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 20 FPS.'},

    {'model': 'acA640-300gm-CN', 'vendor': 'Basler China', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 300,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 320,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': 'VGA @ 300 FPS.'},

    {'model': 'acA1300-60gm-CN', 'vendor': 'Basler China', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 420,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS.'},

    {'model': 'acA1600-20gm-CN', 'vendor': 'Basler China', 'resolution': (1600, 1200),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 20,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 500,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2 Мп @ 20 FPS.'},

    {'model': 'acA1920-40gm-CN', 'vendor': 'Basler China', 'resolution': (1920, 1200),
     'sensor_format': '1/1.2"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 780,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2.3 Мп @ 40 FPS.'},

    {'model': 'acA1920-155um-CN', 'vendor': 'Basler China', 'resolution': (1920, 1080),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 155,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 620,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'HD @ 155 FPS. USB3.'},

    {'model': 'acA2440-20gm-CN', 'vendor': 'Basler China', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 20,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 900,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 20 FPS.'},

    {'model': 'acA2440-35um-CN', 'vendor': 'Basler China', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 35,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 980,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 35 FPS. USB3.'},

    {'model': 'acA2500-14gm-CN', 'vendor': 'Basler China', 'resolution': (2592, 1944),
     'sensor_format': '1/2.5"', 'shutter': 'Rolling', 'max_fps': 14,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 550,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.2,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 14 FPS.'},

    {'model': 'acA3800-14um-CN', 'vendor': 'Basler China', 'resolution': (3840, 2748),
     'sensor_format': '1/1.7"', 'shutter': 'Rolling', 'max_fps': 14,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 850,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 1.67,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '10 Мп @ 14 FPS.'},

    {'model': 'acA4112-20um-CN', 'vendor': 'Basler China', 'resolution': (4112, 3008),
     'sensor_format': '1.1"', 'shutter': 'Rolling', 'max_fps': 20,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 1100,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '12 Мп @ 20 FPS.'},

    {'model': 'acA5472-5gm-CN', 'vendor': 'Basler China', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 5,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 950,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '20 Мп @ 5 FPS.'},

    {'model': 'acA5472-17um-CN', 'vendor': 'Basler China', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 17,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 1500,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '20 Мп @ 17 FPS.'},

    # ==========================================================================
    # HUARAY
    # ==========================================================================
    {'model': 'MV-A130-10GM', 'vendor': 'Huaray', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 90,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 320,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 90 FPS.'},

    {'model': 'MV-A200-10GM', 'vendor': 'Huaray', 'resolution': (1600, 1200),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 420,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2 Мп @ 60 FPS.'},

    {'model': 'MV-A500-10GM', 'vendor': 'Huaray', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 620,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    {'model': 'MV-CA050-10UM', 'vendor': 'Huaray', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 40,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 560,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 40 FPS. USB3.'},

    {'model': 'MV-CA060-10GM', 'vendor': 'Huaray', 'resolution': (3072, 2048),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 30,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 720,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 30 FPS.'},

    {'model': 'MV-CA120-10GM', 'vendor': 'Huaray', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Global', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1050,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS.'},

    {'model': 'MV-CU003-10GM', 'vendor': 'Huaray', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 200,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 180,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': 'VGA @ 200 FPS.'},

    {'model': 'MV-CU013-10GM', 'vendor': 'Huaray', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 300,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS.'},

    {'model': 'MV-CS013-10GM', 'vendor': 'Huaray', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 88,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 350,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 88 FPS.'},

    {'model': 'MV-CS050-10GM', 'vendor': 'Huaray', 'resolution': (2448, 2048),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 620,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    # Линейные сканеры (только GigE)
    {'model': 'MV-CL042-90GM', 'vendor': 'Huaray', 'resolution': (4096, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 90000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 950,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '4K линейный, 90 кГц.'},

    {'model': 'MV-CL086-40GM', 'vendor': 'Huaray', 'resolution': (8192, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 40000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 1300,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '8K линейный, 40 кГц.'},

    # ==========================================================================
    # WUXI BOPIXEL
    # ==========================================================================
    {'model': 'BOP-UB003M', 'vendor': 'Wuxi Bopixel', 'resolution': (640, 480),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 250,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 140,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': 'VGA @ 250 FPS. USB3.'},

    {'model': 'BOP-UB050M', 'vendor': 'Wuxi Bopixel', 'resolution': (800, 600),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 250,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 160,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '0.5 Мп @ 250 FPS.'},

    {'model': 'BOP-UB120M', 'vendor': 'Wuxi Bopixel', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 100,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 260,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 100 FPS.'},

    {'model': 'BOP-UB130M', 'vendor': 'Wuxi Bopixel', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 170,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS.'},

    {'model': 'BOP-UB130C', 'vendor': 'Wuxi Bopixel', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 200,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 4.8,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS, цветная.'},

    {'model': 'BOP-UB016M', 'vendor': 'Wuxi Bopixel', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 130,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 280,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 130 FPS.'},

    {'model': 'BOP-UB200M', 'vendor': 'Wuxi Bopixel', 'resolution': (1600, 1200),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 50,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 240,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.5,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '2 Мп @ 50 FPS.'},

    {'model': 'BOP-UB230M', 'vendor': 'Wuxi Bopixel', 'resolution': (1920, 1200),
     'sensor_format': '1/1.2"', 'shutter': 'Global', 'max_fps': 168,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 480,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '2.3 Мп @ 168 FPS.'},

    {'model': 'BOP-UB231M', 'vendor': 'Wuxi Bopixel', 'resolution': (1920, 1200),
     'sensor_format': '1/1.2"', 'shutter': 'Global', 'max_fps': 41,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 320,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '2.3 Мп @ 41 FPS.'},

    {'model': 'BOP-UB500M', 'vendor': 'Wuxi Bopixel', 'resolution': (2592, 1944),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 400,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    {'model': 'BOP-UB500C', 'vendor': 'Wuxi Bopixel', 'resolution': (2592, 1944),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 450,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS, цветная.'},

    {'model': 'BOP-UB630M', 'vendor': 'Wuxi Bopixel', 'resolution': (3088, 2064),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 18,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 550,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '6 Мп @ 18 FPS.'},

    {'model': 'BOP-UB1200M', 'vendor': 'Wuxi Bopixel', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 750,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS.'},

    {'model': 'BOP-UB2000M', 'vendor': 'Wuxi Bopixel', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 5,
     'interface': 'USB3', 'mount': 'C', 'price_usd': 1050,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': False, 'ip_rating': 'IP30', 'notes': '20 Мп @ 5 FPS.'},

    {'model': 'BOP-EG050M', 'vendor': 'Wuxi Bopixel', 'resolution': (800, 600),
     'sensor_format': '1/3"', 'shutter': 'Global', 'max_fps': 200,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 190,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '0.5 Мп @ 200 FPS.'},

    {'model': 'BOP-EG120M', 'vendor': 'Wuxi Bopixel', 'resolution': (1280, 1024),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 88,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 320,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 88 FPS.'},

    {'model': 'BOP-EG130M', 'vendor': 'Wuxi Bopixel', 'resolution': (1280, 1024),
     'sensor_format': '1/2"', 'shutter': 'Global', 'max_fps': 60,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 220,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.8,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.3 Мп @ 60 FPS.'},

    {'model': 'BOP-EG016M', 'vendor': 'Wuxi Bopixel', 'resolution': (1440, 1080),
     'sensor_format': '1/2.9"', 'shutter': 'Global', 'max_fps': 80,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 350,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '1.6 Мп @ 80 FPS.'},

    {'model': 'BOP-EG200M', 'vendor': 'Wuxi Bopixel', 'resolution': (1600, 1200),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 50,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 300,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 4.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2 Мп @ 50 FPS.'},

    {'model': 'BOP-EG231M', 'vendor': 'Wuxi Bopixel', 'resolution': (1920, 1200),
     'sensor_format': '1/1.2"', 'shutter': 'Global', 'max_fps': 41,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 380,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 5.86,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2.3 Мп @ 41 FPS.'},

    {'model': 'BOP-EG500M', 'vendor': 'Wuxi Bopixel', 'resolution': (2592, 1944),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 480,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS.'},

    {'model': 'BOP-EG500C', 'vendor': 'Wuxi Bopixel', 'resolution': (2592, 1944),
     'sensor_format': '2/3"', 'shutter': 'Global', 'max_fps': 23,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 550,
     'type': 'area', 'mono_color': 'Color', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '5 Мп @ 23 FPS, цветная.'},

    {'model': 'BOP-EG630M', 'vendor': 'Wuxi Bopixel', 'resolution': (3088, 2064),
     'sensor_format': '1/1.8"', 'shutter': 'Global', 'max_fps': 18,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 600,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '6 Мп @ 18 FPS.'},

    {'model': 'BOP-EG1200M', 'vendor': 'Wuxi Bopixel', 'resolution': (4096, 3000),
     'sensor_format': '1.1"', 'shutter': 'Rolling', 'max_fps': 10,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 850,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 3.45,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '12 Мп @ 10 FPS.'},

    {'model': 'BOP-EG2000M', 'vendor': 'Wuxi Bopixel', 'resolution': (5472, 3648),
     'sensor_format': '1"', 'shutter': 'Rolling', 'max_fps': 5,
     'interface': 'GigE', 'mount': 'C', 'price_usd': 1200,
     'type': 'area', 'mono_color': 'Mono', 'pixel_size_um': 2.4,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '20 Мп @ 5 FPS.'},

    # --- BOP-EL линейные сканеры ---
    {'model': 'BOP-EL2048M', 'vendor': 'Wuxi Bopixel', 'resolution': (2048, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 38000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 600,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 7.0,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '2K линейный, 38 кГц.'},

    {'model': 'BOP-EL4096M', 'vendor': 'Wuxi Bopixel', 'resolution': (4096, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 28000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 850,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '4K линейный, 28 кГц.'},

    {'model': 'BOP-EL8192M', 'vendor': 'Wuxi Bopixel', 'resolution': (8192, 2),
     'sensor_format': 'Line', 'shutter': 'Global', 'max_fps': 18000,
     'interface': 'GigE', 'mount': 'M42', 'price_usd': 1250,
     'type': 'line', 'mono_color': 'Mono', 'pixel_size_um': 3.5,
     'poe_support': True, 'ip_rating': 'IP30', 'notes': '8K линейный, 18 кГц.'},
]


# ==============================================================================
# ФИЛЬТРАЦИЯ: только USB3 и GigE, только проверенные бренды, дедупликация
# ==============================================================================

def _filter_cameras(db):
    """Оставляет только промышленные камеры USB3/GigE от проверенных брендов."""
    result = []
    for cam in db:
        if cam.get('vendor') not in ALLOWED_VENDORS:
            continue
        if cam.get('interface') not in ALLOWED_INTERFACES:
            continue
        result.append(cam)
    return result


def _dedup_cameras(db):
    """Убирает дубликаты камер по (vendor, model)."""
    seen = set()
    result = []
    for cam in db:
        key = (cam.get('vendor', ''), cam.get('model', ''))
        if key in seen:
            continue
        seen.add(key)
        result.append(cam)
    return result


CAMERA_DATABASE = _filter_cameras(CAMERA_DATABASE)
CAMERA_DATABASE = _dedup_cameras(CAMERA_DATABASE)


# ==============================================================================
# 1.11 БАЗА ДАННЫХ ОБЪЕКТИВОВ (45 моделей)
# ==============================================================================
LENS_DATABASE = [
    # COMPUTAR — MP2 (стандартные, 2/3")
    {'model': 'Computar M0414-MP2', 'focal_length_mm': 4, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '1/2"', 'price_usd': 220,
     'notes': 'Сверхширокоугольный 4 мм.'},
    {'model': 'Computar M0614-MP2', 'focal_length_mm': 6, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '1/2"', 'price_usd': 200,
     'notes': 'Широкоугольный 6 мм.'},
    {'model': 'Computar M0814-MP2', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 150,
     'notes': 'Стандарт 8 мм.'},
    {'model': 'Computar M1214-MP2', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 160,
     'notes': 'Стандарт 12 мм.'},
    {'model': 'Computar M1614-MP2', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 170,
     'notes': 'Стандарт 16 мм.'},
    {'model': 'Computar M2514-MP2', 'focal_length_mm': 25, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 180,
     'notes': '25 мм.'},
    {'model': 'Computar M3514-MP2', 'focal_length_mm': 35, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 200,
     'notes': '35 мм.'},
    {'model': 'Computar M5028-MP2', 'focal_length_mm': 50, 'max_aperture': 2.8,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 220,
     'notes': '50 мм.'},
    {'model': 'Computar M7528-MP2', 'focal_length_mm': 75, 'max_aperture': 2.8,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 280,
     'notes': '75 мм.'},

    # COMPUTAR — 1"
    {'model': 'Computar M0824-MPW2', 'focal_length_mm': 8, 'max_aperture': 2.4,
     'mount': 'C', 'sensor_coverage': '1"', 'price_usd': 300,
     'notes': '8 мм для 1".'},
    {'model': 'Computar M1224-MPW2', 'focal_length_mm': 12, 'max_aperture': 2.4,
     'mount': 'C', 'sensor_coverage': '1"', 'price_usd': 320,
     'notes': '12 мм для 1".'},
    {'model': 'Computar M1624-MPW2', 'focal_length_mm': 16, 'max_aperture': 2.4,
     'mount': 'C', 'sensor_coverage': '1"', 'price_usd': 350,
     'notes': '16 мм для 1".'},
    {'model': 'Computar M2528-MPW2', 'focal_length_mm': 25, 'max_aperture': 2.8,
     'mount': 'C', 'sensor_coverage': '1"', 'price_usd': 380,
     'notes': '25 мм для 1".'},

    # COMPUTAR — CS-mount
    {'model': 'Computar T0412CS', 'focal_length_mm': 4, 'max_aperture': 1.2,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 70,
     'notes': '4 мм CS.'},
    {'model': 'Computar T0614CS', 'focal_length_mm': 6, 'max_aperture': 1.4,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 75,
     'notes': '6 мм CS.'},
    {'model': 'Computar T0814CS', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 80,
     'notes': '8 мм CS.'},
    {'model': 'Computar T1214CS', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 90,
     'notes': '12 мм CS.'},
    {'model': 'Computar T1614CS', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'CS', 'sensor_coverage': '1/3"', 'price_usd': 100,
     'notes': '16 мм CS.'},

    # KOWA — HC
    {'model': 'Kowa LM6HC', 'focal_length_mm': 6, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 350,
     'notes': '6 мм.'},
    {'model': 'Kowa LM8HC', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 300,
     'notes': '8 мм.'},
    {'model': 'Kowa LM12HC', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 320,
     'notes': '12 мм.'},
    {'model': 'Kowa LM16HC', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 340,
     'notes': '16 мм.'},
    {'model': 'Kowa LM25HC', 'focal_length_mm': 25, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 360,
     'notes': '25 мм.'},
    {'model': 'Kowa LM35HC', 'focal_length_mm': 35, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 380,
     'notes': '35 мм.'},
    {'model': 'Kowa LM50HC', 'focal_length_mm': 50, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 420,
     'notes': '50 мм.'},
    {'model': 'Kowa LM75HC', 'focal_length_mm': 75, 'max_aperture': 1.8,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 480,
     'notes': '75 мм.'},

    # FUJINON
    {'model': 'Fujinon HF6XA-5M', 'focal_length_mm': 6, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 400,
     'notes': '6 мм 5 Мп.'},
    {'model': 'Fujinon HF8XA-5M', 'focal_length_mm': 8, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 350,
     'notes': '8 мм 5 Мп.'},
    {'model': 'Fujinon HF12XA-5M', 'focal_length_mm': 12, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 380,
     'notes': '12 мм 5 Мп.'},
    {'model': 'Fujinon HF16XA-5M', 'focal_length_mm': 16, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 400,
     'notes': '16 мм 5 Мп.'},
    {'model': 'Fujinon HF25XA-5M', 'focal_length_mm': 25, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 450,
     'notes': '25 мм 5 Мп.'},
    {'model': 'Fujinon HF35XA-5M', 'focal_length_mm': 35, 'max_aperture': 1.6,
     'mount': 'C', 'sensor_coverage': '2/3"', 'price_usd': 500,
     'notes': '35 мм 5 Мп.'},

    # SCHNEIDER
    {'model': 'Schneider Xenon-Diamond 8mm', 'focal_length_mm': 8, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 800,
     'notes': '8 мм для 4/3".'},
    {'model': 'Schneider Xenon-Diamond 12mm', 'focal_length_mm': 12, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 850,
     'notes': '12 мм для 4/3".'},
    {'model': 'Schneider Xenon-Diamond 16mm', 'focal_length_mm': 16, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 900,
     'notes': '16 мм для 4/3".'},
    {'model': 'Schneider Xenon-Diamond 25mm', 'focal_length_mm': 25, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 950,
     'notes': '25 мм для 4/3".'},
    {'model': 'Schneider Xenon-Diamond 35mm', 'focal_length_mm': 35, 'max_aperture': 1.4,
     'mount': 'C', 'sensor_coverage': '4/3"', 'price_usd': 1000,
     'notes': '35 мм для 4/3".'},

    # M42-объективы
    {'model': 'Kowa LM12XC', 'focal_length_mm': 12, 'max_aperture': 1.8,
     'mount': 'M42', 'sensor_coverage': '4/3"', 'price_usd': 450,
     'notes': '12 мм M42.'},
    {'model': 'Kowa LM16XC', 'focal_length_mm': 16, 'max_aperture': 1.8,
     'mount': 'M42', 'sensor_coverage': '4/3"', 'price_usd': 480,
     'notes': '16 мм M42.'},
    {'model': 'Kowa LM25XC', 'focal_length_mm': 25, 'max_aperture': 1.8,
     'mount': 'M42', 'sensor_coverage': '4/3"', 'price_usd': 520,
     'notes': '25 мм M42.'},
    {'model': 'Kowa LM35XC', 'focal_length_mm': 35, 'max_aperture': 1.8,
     'mount': 'M42', 'sensor_coverage': '4/3"', 'price_usd': 580,
     'notes': '35 мм M42.'},
]


# ==============================================================================
# 1.12 БАЗА ДАННЫХ ОСВЕЩЕНИЯ
# ==============================================================================
LIGHTING_DATABASE = [
    {'model': 'LDR2-74-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 3.6, 'price_usd': 250, 'notes': '74 мм. Мелкие детали.'},
    {'model': 'LDR2-100-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 5.0, 'price_usd': 320, 'notes': '100 мм. Стандарт.'},
    {'model': 'LDR2-150-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 9.0, 'price_usd': 500, 'notes': '150 мм. Крупные детали.'},
    {'model': 'LDR2-200-W', 'vendor': 'CCS', 'lighting_type': 'Кольцевое белое',
     'power_w': 15.0, 'price_usd': 750, 'notes': '200 мм.'},

    {'model': 'DRL-100-W', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 8.0, 'price_usd': 600, 'notes': 'Блики 100 мм.'},
    {'model': 'DRL-150-W', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 12.0, 'price_usd': 850, 'notes': 'Крупные зеркала.'},
    {'model': 'DRL-200-W', 'vendor': 'CCS', 'lighting_type': 'Диффузный купол',
     'power_w': 18.0, 'price_usd': 1100, 'notes': 'Очень крупные зеркала.'},

    {'model': 'LFL-100-W', 'vendor': 'CCS', 'lighting_type': 'Тёмное поле (низкоугловое)',
     'power_w': 6.0, 'price_usd': 450, 'notes': 'Царапины 100 мм.'},
    {'model': 'LFL-150-W', 'vendor': 'CCS', 'lighting_type': 'Тёмное поле (низкоугловое)',
     'power_w': 9.0, 'price_usd': 600, 'notes': 'Царапины 150 мм.'},

    {'model': 'BLP-100-W', 'vendor': 'CCS', 'lighting_type': 'Контровое (backlight)',
     'power_w': 10.0, 'price_usd': 550, 'notes': 'Силуэт 100 мм.'},
    {'model': 'BLP-200-W', 'vendor': 'CCS', 'lighting_type': 'Контровое (backlight)',
     'power_w': 18.0, 'price_usd': 900, 'notes': 'Силуэт 200 мм.'},

    {'model': 'CXL-100-W', 'vendor': 'CCS', 'lighting_type': 'Коаксиальное или диффузный купол',
     'power_w': 5.0, 'price_usd': 500, 'notes': 'Зеркала 100 мм.'},
    {'model': 'CXL-150-W', 'vendor': 'CCS', 'lighting_type': 'Коаксиальное или диффузный купол',
     'power_w': 8.0, 'price_usd': 750, 'notes': 'Зеркала 150 мм.'},

    {'model': 'RL-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Кольцевое белое', 'power_w': 6.0, 'price_usd': 280,
     'notes': 'Общий контроль.'},
    {'model': 'DL-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Диффузный купол', 'power_w': 10.0, 'price_usd': 700,
     'notes': 'Блики.'},
    {'model': 'LF-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Тёмное поле (низкоугловое)', 'power_w': 7.0, 'price_usd': 500,
     'notes': 'Царапины.'},
    {'model': 'BL-100', 'vendor': 'Advanced Illumination',
     'lighting_type': 'Контровое (backlight)', 'power_w': 12.0, 'price_usd': 650,
     'notes': 'Силуэт.'},

    {'model': 'SVL-RL-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Кольцевое белое', 'power_w': 4.5, 'price_usd': 180,
     'notes': 'Самый дешёвый.'},
    {'model': 'SVL-DL-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Диффузный купол', 'power_w': 8.5, 'price_usd': 500,
     'notes': 'Блики.'},
    {'model': 'SVL-LF-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Тёмное поле (низкоугловое)', 'power_w': 5.5, 'price_usd': 380,
     'notes': 'Царапины.'},
    {'model': 'SVL-BL-100', 'vendor': 'Smart Vision Lights',
     'lighting_type': 'Контровое (backlight)', 'power_w': 9.0, 'price_usd': 450,
     'notes': 'Силуэт.'},
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
    M58 = "M58"
    F = "F"


class TaskType(str, Enum):
    INSPECTION = "inspection"
    TRACKING = "tracking"
    DETECTION = "detection"


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
    server_distance_m: float = 3.0
    total_area_width_m: Optional[float] = None
    total_area_height_m: Optional[float] = None
    overlap_pct: float = 20.0
    task_type: str = "inspection"
    object_speed_mm_s: float = 0.0
    shift_ratio: float = 0.5
    lighting_mode: str = "auto"


@dataclass
class CameraVariant:
    label: str
    overall_factor: float
    camera_model: str
    camera_price_usd: float
    resolution: tuple
    sensor_format: str
    shutter_type: str
    fps_max: float
    interface: str
    camera_type: str
    camera_notes: str
    focal_length_mm: float
    aperture: float
    lens_model: str
    lens_price_usd: float
    lens_mount: str
    lens_sensor_coverage: str
    depth_of_field_mm: float
    hfov_deg: float
    vfov_deg: float
    dfov_deg: float
    actual_fov_width_mm: float
    actual_fov_height_mm: float
    fov_covers_required: bool
    lighting_type: str
    lighting_model: str
    lighting_price_usd: float
    lighting_power_w: float
    lighting_needed: bool
    lighting_note: str
    num_cameras: int
    total_price_usd: float
    budget_ok: bool
    bandwidth_mbps: float = 0.0
    bandwidth_ok: bool = True
    bandwidth_limit_mbps: float = 0.0
    warnings: list = field(default_factory=list)


@dataclass
class CameraRecommendation:
    variants: list = field(default_factory=list)
    fps_required: float = 0
    max_exposure_time_ms: float = 0
    required_illuminance_lux: float = 0
    lighting_notes: str = ""
    lighting_decision: str = ""
    lighting_reason: str = ""
    num_cameras_actual: int = 1
    num_cameras_notes: str = ""
    perspective_distortion_pct: float = 0
    fov_edge_near_mm: float = 0
    fov_edge_far_mm: float = 0
    fov_center_mm: float = 0
    camera_tilt_deg: float = 0
    compatibility_notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


# ==============================================================================
# РАЗДЕЛ 4: ФУНКЦИИ РАСЧЁТА
# ==============================================================================

def calculate_fps_for_tracking(object_speed_mm_s, object_size_mm, shift_ratio=0.3):
    if object_size_mm <= 0 or object_speed_mm_s <= 0:
        return 10.0
    max_shift_mm = object_size_mm * shift_ratio
    return object_speed_mm_s / max_shift_mm


def calculate_required_resolution(fov_width_mm, fov_height_mm,
                                   defect_size_mm, min_pixels_per_defect):
    pixels_per_mm = min_pixels_per_defect / defect_size_mm
    required_width_px = math.ceil(fov_width_mm * pixels_per_mm)
    required_height_px = math.ceil(fov_height_mm * pixels_per_mm)
    chosen = None
    for res_w, res_h in STANDARD_RESOLUTIONS:
        if res_h == 2:
            if res_w >= required_width_px:
                chosen = (res_w, 2)
                break
        elif res_w >= required_width_px and res_h >= required_height_px:
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


def calculate_required_fps(req, line_speed_mm_s, part_spacing_mm,
                            images_per_part, is_moving):
    if req.task_type == "tracking":
        fps = calculate_fps_for_tracking(
            req.object_speed_mm_s or line_speed_mm_s,
            req.defect_size_mm,
            req.shift_ratio
        )
        return max(fps, 25.0)

    if not is_moving or part_spacing_mm <= 0:
        return 10.0
    return max(10.0, (line_speed_mm_s / part_spacing_mm) * images_per_part)


def calculate_focal_length(sensor_width_mm, working_distance_mm, fov_width_mm):
    return (sensor_width_mm * working_distance_mm) / fov_width_mm


def calculate_field_of_view_angles(sensor_width_mm, sensor_height_mm, focal_length_mm):
    hfov_rad = 2 * math.atan(sensor_width_mm / (2 * focal_length_mm))
    vfov_rad = 2 * math.atan(sensor_height_mm / (2 * focal_length_mm))
    diagonal_mm = math.sqrt(sensor_width_mm ** 2 + sensor_height_mm ** 2)
    dfov_rad = 2 * math.atan(diagonal_mm / (2 * focal_length_mm))
    return (math.degrees(hfov_rad), math.degrees(vfov_rad), math.degrees(dfov_rad))


def calculate_fov_from_angles(hfov_deg, vfov_deg, working_distance_mm):
    hfov_rad = math.radians(hfov_deg)
    vfov_rad = math.radians(vfov_deg)
    width_mm = 2 * working_distance_mm * math.tan(hfov_rad / 2)
    height_mm = 2 * working_distance_mm * math.tan(vfov_rad / 2)
    return width_mm, height_mm


def check_fov_coverage(hfov_deg, vfov_deg, working_distance_mm,
                        required_fov_w_mm, required_fov_h_mm):
    actual_w, actual_h = calculate_fov_from_angles(
        hfov_deg, vfov_deg, working_distance_mm
    )
    warnings = []
    if actual_w < required_fov_w_mm * 0.95:
        warnings.append(
            f"FOV по ширине: {actual_w:.0f} мм < требуется {required_fov_w_mm:.0f} мм."
        )
    if actual_h < required_fov_h_mm * 0.95:
        warnings.append(
            f"FOV по высоте: {actual_h:.0f} мм < требуется {required_fov_h_mm:.0f} мм."
        )
    return actual_w, actual_h, warnings


def calculate_cameras_for_area(req, hfov_deg, vfov_deg):
    if req.total_area_width_m is None or req.total_area_height_m is None:
        return req.num_cameras, ""

    fov_w_mm, fov_h_mm = calculate_fov_from_angles(
        hfov_deg, vfov_deg, req.working_distance_mm
    )
    fov_w_m = fov_w_mm / 1000.0
    fov_h_m = fov_h_mm / 1000.0

    if fov_w_m <= 0 or fov_h_m <= 0:
        return req.num_cameras, ""

    overlap = 1.0 - (req.overlap_pct / 100.0)
    eff_fov_w = fov_w_m * overlap
    eff_fov_h = fov_h_m * overlap

    n_w = math.ceil(req.total_area_width_m / eff_fov_w)
    n_h = math.ceil(req.total_area_height_m / eff_fov_h)
    total = n_w * n_h

    notes = (
        f"Зона {req.total_area_width_m}×{req.total_area_height_m} м. "
        f"Одна камера покрывает {fov_w_m:.1f}×{fov_h_m:.1f} м. "
        f"С перекрытием {req.overlap_pct}% нужно {n_w}×{n_h} = {total} камер."
    )
    return total, notes


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
                                    sensor_sensitivity, max_exposure_time_s, aperture,
                                    quantum_efficiency=0.6):
    base_lux = (sensor_sensitivity * (aperture ** 2)) / \
               max(max_exposure_time_s * quantum_efficiency, 1e-6)
    reflection_compensation = 1.0 / max(reflectivity_coefficient, 0.2)
    ambient_compensation = max(0.3, 1.0 - ambient_lux / 500.0)
    return base_lux * reflection_compensation * ambient_compensation


def calculate_lighting_power(required_lux, coverage_area_m2,
                              led_efficiency_lm_per_w=120.0,
                              optics_efficiency=0.8,
                              safety_factor=1.5):
    if coverage_area_m2 <= 0 or required_lux <= 0:
        return 0.0
    total_lumens = required_lux * coverage_area_m2
    effective_lm_per_w = led_efficiency_lm_per_w * optics_efficiency
    power_w = total_lumens / effective_lm_per_w * safety_factor
    return power_w


# ------------------------------------------------------------------------------
# ПРОПУСКНАЯ СПОСОБНОСТЬ
# ------------------------------------------------------------------------------

def calculate_bandwidth_mbps(resolution, fps, bit_depth=8):
    """Считает требуемую пропускную способность в Мбит/с."""
    if not resolution or len(resolution) < 2:
        return 0.0
    res_w, res_h = resolution
    if res_h == 2:
        # Линейный сканер — res_h = 2, считаем по line rate
        # bandwidth = ширина × line_rate × bit_depth
        return res_w * fps * bit_depth / 1e6
    return res_w * res_h * fps * bit_depth / 1e6


def check_bandwidth(camera, fps_required):
    """
    Проверяет, хватит ли пропускной способности интерфейса.

    Возвращает:
        (bandwidth_mbps, limit_mbps, ok, note)
    """
    interface = camera.get('interface', '')
    resolution = camera.get('resolution', (0, 0))

    bandwidth = calculate_bandwidth_mbps(resolution, fps_required, bit_depth=8)

    limit = INTERFACE_BANDWIDTH_MBPS.get(interface, 0)
    effective_limit = limit * INTERFACE_BANDWIDTH_SAFETY

    ok = bandwidth <= effective_limit

    note = ""
    if not ok:
        note = (
            f"⚠ {interface}: нужно {bandwidth:.0f} Мбит/с > "
            f"лимит {effective_limit:.0f} Мбит/с. "
            f"Снизьте FPS или разрешение."
        )

    return bandwidth, effective_limit, ok, note


# ==============================================================================
# РАЗДЕЛ 4b: ЛОГИКА АВТООПРЕДЕЛЕНИЯ СВЕТА
# ==============================================================================

def decide_lighting_needed(req, exposure_ms, ambient_lux):
    if req.lighting_mode == "off":
        return ("not_needed",
                "Свет отключён пользователем (--lighting off).")
    if req.lighting_mode == "on":
        return ("needed",
                "Свет принудительно включён (--lighting on).")

    if req.task_type in ("tracking", "detection"):
        if req.defect_size_mm >= 10 and ambient_lux >= 200:
            return ("not_needed",
                    f"Задача {req.task_type} для крупного объекта "
                    f"({req.defect_size_mm} мм) при рабочем свете "
                    f"({ambient_lux} лк) — свет не требуется.")
        if req.defect_size_mm >= 10 and ambient_lux < 200:
            return ("needed",
                    f"Задача {req.task_type}, но цех тёмный "
                    f"({ambient_lux} лк) — нужен прожектор.")
        if req.defect_size_mm < 10:
            return ("borderline",
                    f"Объект мелкий ({req.defect_size_mm} мм) — свет желателен.")

    if exposure_ms < 0.5:
        return ("needed",
                f"Очень короткая выдержка ({exposure_ms:.2f} мс) — нужен яркий свет.")

    if req.reflectivity.value == 'зеркальная (полировка, хром)':
        return ("needed",
                "Зеркальная поверхность — нужен купол или коаксиальный свет.")

    if req.defect_size_mm < 0.5:
        return ("needed",
                f"Мелкий дефект ({req.defect_size_mm} мм) — нужен контролируемый свет.")

    if req.defect_size_mm < 2.0 and exposure_ms < 2.0:
        return ("needed",
                f"Мелкий дефект ({req.defect_size_mm} мм) + короткая выдержка "
                f"({exposure_ms:.2f} мс) — нужен свет.")

    if ambient_lux < 100:
        return ("needed",
                f"Тёмный цех ({ambient_lux} лк) — нужен дополнительный свет.")

    if req.defect_size_mm >= 2.0 and exposure_ms >= 2.0 and ambient_lux >= 200:
        return ("not_needed",
                f"Дефект {req.defect_size_mm} мм, выдержка {exposure_ms:.2f} мс, "
                f"рабочий свет {ambient_lux} лк — достаточно.")

    if 0.5 <= req.defect_size_mm < 2.0 and ambient_lux >= 200:
        return ("borderline",
                "На грани — свет желателен, но не обязателен.")

    return ("not_needed",
            "Параметры задачи не требуют дополнительного света.")


# ==============================================================================
# РАЗДЕЛ 5: ВЫБОР ОБОРУДОВАНИЯ
# ==============================================================================

def select_camera_options(required_resolution, shutter_type,
                           fps_required, server_distance_m=3.0,
                           preferred_type=None) -> list:
    """Возвращает ВСЕ подходящие камеры с USB3/GigE, отсортированные по запасу."""
    req_w, req_h = required_resolution
    candidates = []

    for cam in CAMERA_DATABASE:
        res_w, res_h = cam['resolution']

        if preferred_type and cam.get('type') != preferred_type:
            continue
        if shutter_type == 'Global' and cam['shutter'] != 'Global':
            continue

        max_dist = INTERFACE_MAX_DISTANCE_M.get(cam['interface'], 999)
        if server_distance_m > max_dist:
            continue

        if cam.get('type') == 'line':
            if res_w < req_w:
                continue
            res_factor = res_w / req_w
        else:
            if res_w < req_w or res_h < req_h:
                continue
            res_factor = min(res_w / req_w, res_h / req_h)

        if cam['max_fps'] < fps_required:
            continue
        fps_factor = cam['max_fps'] / max(fps_required, 1.0)

        # Проверка пропускной способности
        bandwidth, limit, bw_ok, bw_note = check_bandwidth(cam, fps_required)
        if not bw_ok:
            continue

        candidates.append({
            'camera': cam,
            'res_factor': res_factor,
            'fps_factor': fps_factor,
            'overall_factor': min(res_factor, fps_factor),
            'bandwidth_mbps': bandwidth,
            'bandwidth_limit_mbps': limit,
        })

    candidates.sort(key=lambda c: c['overall_factor'])
    return candidates


def check_camera_lens_compatibility(camera: dict, lens: dict) -> list:
    notes = []
    camera_mount = camera.get('mount', 'C')
    lens_mount = lens.get('mount', 'C')

    if camera_mount != lens_mount:
        if camera_mount == 'CS' and lens_mount == 'C':
            notes.append(f"Крепление: адаптер C→CS (5 мм).")
        elif camera_mount == 'C' and lens_mount == 'CS':
            notes.append(f"Крепление: C-mount камера + CS-объектив — НЕСОВМЕСТИМО.")
        else:
            notes.append(f"Крепление: {lens_mount}-mount vs {camera_mount}-mount — переходник.")

    camera_sensor = camera.get('sensor_format', '1/2"')
    lens_coverage = lens.get('sensor_coverage', '2/3"')
    camera_sensor_width = SENSOR_WIDTH_MM.get(camera_sensor, 6.4)
    lens_coverage_width = SENSOR_WIDTH_MM.get(lens_coverage, 8.8)

    if lens_coverage_width < camera_sensor_width:
        notes.append(
            f"Покрытие: объектив {lens_coverage} < сенсор {camera_sensor}. "
            f"Возможно виньетирование."
        )
    return notes


def check_camera_interface_notes(camera: dict, server_distance_m: float) -> list:
    notes = []
    interface = camera['interface']
    max_dist = INTERFACE_MAX_DISTANCE_M.get(interface, 0)
    if server_distance_m > max_dist * 0.8:
        notes.append(f"⚠ {interface}: сервер на {server_distance_m} м, макс. {max_dist} м.")
    return notes


def select_lens_from_database(focal_length_target_mm, budget_usd,
                               preferred_mount='C', sensor_format='1/2"',
                               required_fov_width_mm=None,
                               required_fov_height_mm=None,
                               working_distance_mm=None):
    sensor_width = SENSOR_WIDTH_MM.get(sensor_format, 6.4)
    candidates = []

    for lens in LENS_DATABASE:
        if lens['focal_length_mm'] <= 0:
            continue
        if preferred_mount and lens['mount'] != preferred_mount:
            continue
        lens_coverage = SENSOR_WIDTH_MM.get(lens['sensor_coverage'], 0)
        if lens_coverage < sensor_width:
            continue
        if lens['price_usd'] > budget_usd:
            continue

                # Проверка покрытия FOV (и по ширине, и по высоте)
        if required_fov_width_mm and working_distance_mm:
            f = lens['focal_length_mm']
            sensor_height = sensor_width * SENSOR_HEIGHT_RATIO

            # Ширина
            hfov_rad = 2 * math.atan(sensor_width / (2 * f))
            fov_w_mm = 2 * working_distance_mm * math.tan(hfov_rad / 2)
            if fov_w_mm < required_fov_width_mm * 0.98:
                continue

            # Высота (если задана)
            if required_fov_height_mm:
                vfov_rad = 2 * math.atan(sensor_height / (2 * f))
                fov_h_mm = 2 * working_distance_mm * math.tan(vfov_rad / 2)
                if fov_h_mm < required_fov_height_mm * 0.98:
                    continue

        candidates.append(lens)

    if not candidates:
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
        return None

    candidates.sort(key=lambda x: abs(x['focal_length_mm'] - focal_length_target_mm))
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
    if req.task_type in ("tracking", "detection"):
        if req.reflectivity == Reflectivity.MIRROR:
            return ("Коаксиальное или диффузный купол",
                    "Зеркальная поверхность.")
        return ("Кольцевое белое",
                "Белый свет для детекции объектов.")

    if req.reflectivity == Reflectivity.MIRROR:
        return ("Коаксиальное или диффузный купол",
                "Зеркальная поверхность: избегать бликов.")
    if req.defect_type in (DefectType.SCRATCH, DefectType.CHIP, DefectType.CRACK):
        return ("Тёмное поле (низкоугловое)",
                "Низкоугловой свет подчёркивает неровности.")
    if req.defect_type in (DefectType.MISSING, DefectType.DISPLACEMENT):
        if req.contrast == Contrast.DARK_ON_LIGHT:
            return ("Контровое (backlight)", "Обратная подсветка — силуэт.")
        return ("Диффузный купол", "Равномерный свет без теней.")
    if req.defect_type == DefectType.COLOR:
        return ("Кольцевое белое", "Белый свет для цветопередачи.")
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

    # Шаг 2: Выдержка
    max_exposure_s = calculate_max_exposure_time(
        req.line_speed_mm_s, req.fov_width_mm, chosen_res[0]
    )
    max_exposure_ms = max_exposure_s * 1000

    # Шаг 3: FPS
    fps_required = calculate_required_fps(
        req, req.line_speed_mm_s, req.part_spacing_mm,
        req.images_per_part, req.is_moving
    )

    # Шаг 4: Затвор
    if req.is_moving and req.line_speed_mm_s > 0:
        shutter_type = 'Global'
        shutter_text = "Global Shutter"
    else:
        shutter_type = 'Rolling'
        shutter_text = "Rolling Shutter"

    # Шаг 5: Решение о свете
    ambient_lux = AMBIENT_LIGHT_LUX.get(req.ambient_light, 300)
    lighting_decision, lighting_reason = decide_lighting_needed(
        req, max_exposure_ms, ambient_lux
    )

    if lighting_decision == "not_needed":
        lighting_type = "Рабочий свет цеха"
        lighting_model = "Не требуется"
        lighting_price = 0
        lighting_power_w = 0.0
        required_lux = 0
        lighting_notes = lighting_reason
    else:
        lighting_type, lighting_notes = select_lighting_type(req)
        reflectivity_coef = REFLECTIVITY_COEFFICIENT.get(req.reflectivity.value, 0.4)
        sensor_sens = SENSOR_SENSITIVITY.get(
            'Global Shutter CMOS' if shutter_type == 'Global' else 'Rolling Shutter CMOS', 2.0
        )
        required_lux = calculate_required_illuminance(
            ambient_lux, reflectivity_coef, sensor_sens, max_exposure_s, 1.4
        )
        required_lux = max(required_lux, 500.0)
        coverage_area_m2 = (req.fov_width_mm / 1000) * (req.fov_height_mm / 1000)
        lighting_power_w = calculate_lighting_power(required_lux, coverage_area_m2)

        light = select_lighting_from_database(
            lighting_type, lighting_power_w, 10000
        )
        if light:
            lighting_model = f"{light['vendor']} {light['model']} ({light['power_w']} Вт)"
            lighting_price = light['price_usd']
        else:
            lighting_model = f"Не найдено (нужно ~{lighting_power_w:.0f} Вт)"
            lighting_price = 0

    # Шаг 6: Интерфейс
    bit_depth = 8
    bandwidth_required = calculate_bandwidth_mbps(chosen_res, fps_required, bit_depth)
    if bandwidth_required < 950:
        interface = "GigE Vision"
    else:
        interface = "USB3 Vision"

    # Шаг 7: Бюджет (для совместимости)
    budget_limits = {
        BudgetLevel.LOW: 3000,
        BudgetLevel.MEDIUM: 10000,
        BudgetLevel.HIGH: 100000,
    }
    total_budget = budget_limits[req.budget] * req.num_cameras

    # Шаг 8: Выбор камер
    camera_options_list = select_camera_options(
        chosen_res, shutter_type, fps_required,
        server_distance_m=req.server_distance_m,
        preferred_type='area',
    )

    if not camera_options_list:
        warnings.append("Не найдено ни одной камеры под требования.")

    # Шаг 9: Собираем варианты
    variants = []
    for i, entry in enumerate(camera_options_list):
        camera = entry['camera']
        factor = entry['overall_factor']
        bandwidth_mbps = entry['bandwidth_mbps']
        bandwidth_limit = entry['bandwidth_limit_mbps']

        camera_model = f"{camera['vendor']} {camera['model']}"
        camera_price = camera['price_usd']
        sensor_format = camera['sensor_format']
        camera_type = camera.get('type', 'area')
        camera_notes = camera.get('notes', '')

        # Объектив
        sensor_width_mm = SENSOR_WIDTH_MM.get(sensor_format, 6.4)
        sensor_height_mm = sensor_width_mm * SENSOR_HEIGHT_RATIO
        focal_length_target = calculate_focal_length(
            sensor_width_mm, req.working_distance_mm, req.fov_width_mm
        )

        preferred_mount = req.preferred_mount.value
        if camera_type == 'line':
            preferred_mount = 'M42'

        lens = select_lens_from_database(
            focal_length_target, total_budget * 0.2,
            preferred_mount=preferred_mount,
            sensor_format=sensor_format,
            required_fov_width_mm=req.fov_width_mm,
            required_fov_height_mm=req.fov_height_mm,
            working_distance_mm=req.working_distance_mm,
            )

        if lens is None:
            lens_model = "Не найдено"
            lens_price = 0
            focal_length = round(focal_length_target, 1)
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

        dof_mm = calculate_depth_of_field(focal_length, aperture, req.working_distance_mm)

        if focal_length > 0:
            hfov, vfov, dfov = calculate_field_of_view_angles(
                sensor_width_mm, sensor_height_mm, focal_length
            )
        else:
            hfov, vfov, dfov = 0.0, 0.0, 0.0

        actual_fov_w, actual_fov_h, fov_warnings = check_fov_coverage(
            hfov, vfov, req.working_distance_mm,
            req.fov_width_mm, req.fov_height_mm
        )
        fov_covers = (actual_fov_w >= req.fov_width_mm * 0.95 and
                      actual_fov_h >= req.fov_height_mm * 0.95)

        # Проверка пропорций (landscape vs portrait)
        req_ratio = req.fov_width_mm / max(req.fov_height_mm, 1)
        cam_res = camera['resolution']
        cam_ratio = cam_res[0] / max(cam_res[1], 1)

        ratio_diff = abs(req_ratio - cam_ratio)
        warnings_local = []
        if ratio_diff > 0.3:
            req_orient = "landscape" if req_ratio > 1 else "portrait"
            cam_orient = "landscape" if cam_ratio > 1 else "portrait"
            if req_orient != cam_orient:
                warnings_local = [
                    f"⚠ FOV {req.fov_width_mm:.0f}×{req.fov_height_mm:.0f} "
                    f"({req_orient}), камера {cam_res[0]}×{cam_res[1]} "
                    f"({cam_orient}). Поверните камеру на 90° или измените FOV."
                ]
            else:
                warnings_local = [
                    f"⚠ Пропорции FOV и сенсора различаются "
                    f"({req_ratio:.2f} vs {cam_ratio:.2f})."
                ]

        num_cameras_v, _ = calculate_cameras_for_area(req, hfov, vfov)
        total_price = (camera_price + lens_price + lighting_price) * num_cameras_v

        variant_warnings = list(warnings) + fov_warnings + warnings_local
        if lens is not None:
            compat = check_camera_lens_compatibility(camera, lens)
            if compat:
                variant_warnings.extend(compat)
        iface_notes = check_camera_interface_notes(camera, req.server_distance_m)
        if iface_notes:
            variant_warnings.extend(iface_notes)

        variants.append(CameraVariant(
            label=f"Вариант {i+1}",
            overall_factor=round(factor, 2),
            camera_model=camera_model,
            camera_price_usd=camera_price,
            resolution=camera['resolution'],
            sensor_format=sensor_format,
            shutter_type=shutter_text,
            fps_max=camera['max_fps'],
            interface=camera['interface'],
            camera_type=camera_type,
            camera_notes=camera_notes,
            focal_length_mm=round(focal_length, 1),
            aperture=aperture,
            lens_model=lens_model,
            lens_price_usd=lens_price,
            lens_mount=lens_mount,
            lens_sensor_coverage=lens_sensor_coverage,
            depth_of_field_mm=round(dof_mm, 1),
            hfov_deg=round(hfov, 1),
            vfov_deg=round(vfov, 1),
            dfov_deg=round(dfov, 1),
            actual_fov_width_mm=round(actual_fov_w, 1),
            actual_fov_height_mm=round(actual_fov_h, 1),
            fov_covers_required=fov_covers,
            lighting_type=lighting_type,
            lighting_model=lighting_model,
            lighting_price_usd=lighting_price,
            lighting_power_w=round(lighting_power_w, 1),
            lighting_needed=(lighting_decision == "needed"),
            lighting_note=lighting_reason,
            num_cameras=num_cameras_v,
            total_price_usd=round(total_price, 0),
            budget_ok=total_price <= total_budget,
            bandwidth_mbps=round(bandwidth_mbps, 0),
            bandwidth_ok=True,
            bandwidth_limit_mbps=round(bandwidth_limit, 0),
            warnings=variant_warnings,
        ))

    # Перспектива
    if variants:
        first = variants[0]
        fov_center, fov_near, fov_far, perspective_pct = calculate_tilt_and_perspective(
            req.working_distance_mm, req.fov_width_mm,
            req.camera_tilt_deg, first.hfov_deg
        )
    else:
        fov_center, fov_near, fov_far, perspective_pct = (0, 0, 0, 0)

    if variants:
        num_cameras_actual, num_cameras_notes = calculate_cameras_for_area(
            req, variants[0].hfov_deg, variants[0].vfov_deg
        )
    else:
        num_cameras_actual, num_cameras_notes = req.num_cameras, ""

    return CameraRecommendation(
        variants=variants,
        fps_required=round(fps_required, 1),
        max_exposure_time_ms=round(max_exposure_ms, 3),
        required_illuminance_lux=round(required_lux, 0),
        lighting_notes=lighting_notes,
        lighting_decision=lighting_decision,
        lighting_reason=lighting_reason,
        num_cameras_actual=num_cameras_actual,
        num_cameras_notes=num_cameras_notes,
        perspective_distortion_pct=round(perspective_pct, 1),
        fov_edge_near_mm=round(fov_near, 1),
        fov_edge_far_mm=round(fov_far, 1),
        fov_center_mm=round(fov_center, 1),
        camera_tilt_deg=req.camera_tilt_deg,
        compatibility_notes=compatibility_notes,
        warnings=warnings,
    )


# ==============================================================================
# РАЗДЕЛ 7: ВИЗУАЛИЗАЦИЯ
# ==============================================================================

def visualize_recommendation(rec, req, filename="recommendation_plots.png"):
    if not MATPLOTLIB_AVAILABLE or not rec.variants:
        return

    variant = rec.variants[len(rec.variants) // 2]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    ax1 = axes[0, 0]
    angles = ['HFOV', 'VFOV', 'DFOV']
    values = [variant.hfov_deg, variant.vfov_deg, variant.dfov_deg]
    bars = ax1.bar(angles, values, color=['#4C72B0', '#55A868', '#C44E52'])
    ax1.set_ylabel('Угол (°)')
    ax1.set_title('Углы обзора')
    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{val:.1f}°', ha='center', fontsize=10)

    ax2 = axes[0, 1]
    distances = np.linspace(req.working_distance_mm * 0.5,
                            req.working_distance_mm * 2.0, 50)
    dofs = [calculate_depth_of_field(variant.focal_length_mm, variant.aperture, d)
            for d in distances]
    ax2.plot(distances, dofs, color='#4C72B0', linewidth=2)
    ax2.axvline(req.working_distance_mm, color='red', linestyle='--',
                label=f'Рабочая: {req.working_distance_mm} мм')
    ax2.axhline(variant.depth_of_field_mm, color='green', linestyle=':',
                label=f'DOF: {variant.depth_of_field_mm} мм')
    ax2.set_xlabel('Дистанция (мм)')
    ax2.set_ylabel('DOF (мм)')
    ax2.set_title('DOF')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    ax3 = axes[1, 0]
    labels = ['Камера', 'Объектив']
    sizes = [variant.camera_price_usd, variant.lens_price_usd]
    if variant.lighting_price_usd > 0:
        labels.append('Освещение')
        sizes.append(variant.lighting_price_usd)
    if sum(sizes) > 0:
        ax3.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax3.set_title(f'Цена: ${variant.total_price_usd:.0f}')
    else:
        ax3.text(0.5, 0.5, 'Нет данных', ha='center', va='center')

    ax4 = axes[1, 1]
    ax4.set_xlim(-req.fov_width_mm, req.fov_width_mm)
    ax4.set_ylim(0, req.working_distance_mm * 1.2)
    ax4.axhline(y=0, color='black', linewidth=2)
    tilt_rad = math.radians(rec.camera_tilt_deg)
    cam_x = req.working_distance_mm * math.tan(tilt_rad)
    cam_y = req.working_distance_mm
    ax4.plot(cam_x, cam_y, 'ro', markersize=12)
    ax4.plot([cam_x, -rec.fov_edge_near_mm / 2], [cam_y, 0], 'b--', alpha=0.5)
    ax4.plot([cam_x, rec.fov_edge_far_mm / 2], [cam_y, 0], 'r--', alpha=0.5)
    ax4.set_xlabel('Ширина (мм)')
    ax4.set_ylabel('Дистанция (мм)')
    ax4.set_title(f'Наклон: {rec.camera_tilt_deg}°, искажения: {rec.perspective_distortion_pct:.1f}%')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"Графики сохранены: {filename}")


# ==============================================================================
# РАЗДЕЛ 8: СРАВНЕНИЕ КОНФИГУРАЦИЙ
# ==============================================================================

def compare_configurations(configs, names):
    if not configs:
        return "Нет конфигураций."

    lines = ["=" * 110, "СРАВНЕНИЕ КОНФИГУРАЦИЙ", "=" * 110]

    header = f"{'Параметр':<28}"
    for name in names:
        header += f"{name:<25}"
    lines.append(header)
    lines.append("-" * 110)

    def mid(c):
        return c.variants[len(c.variants) // 2] if c.variants else None

    rows = [
        ("Камера", [(mid(c).camera_model[:22] if mid(c) else "—") for c in configs]),
        ("FPS", [str(c.fps_required) for c in configs]),
        ("Свет", ["не нужен" if c.lighting_decision == "not_needed" else "нужен" for c in configs]),
        ("Итого", [(f"${mid(c).total_price_usd:.0f}" if mid(c) else "—") for c in configs]),
    ]

    for label, values in rows:
        line = f"{label:<28}"
        for val in values:
            line += f"{val:<25}"
        lines.append(line)

    lines.append("=" * 110)
    return "\n".join(lines)


def export_comparison_to_csv(configs, names, filename="comparison.csv"):
    if not configs:
        return

    def mid(c):
        return c.variants[len(c.variants) // 2] if c.variants else None

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Параметр"] + names)
        writer.writerow(["Камера"] + [(mid(c).camera_model if mid(c) else "—") for c in configs])
        writer.writerow(["FPS"] + [str(c.fps_required) for c in configs])
        writer.writerow(["Итого"] + [(f"${mid(c).total_price_usd:.0f}" if mid(c) else "—") for c in configs])
    print(f"Сравнение сохранено: {filename}")


# ==============================================================================
# РАЗДЕЛ 9: ВЫВОД
# ==============================================================================

def format_recommendation_text(rec, req) -> str:
    lines = []
    lines.append("=" * 90)
    lines.append("РЕКОМЕНДАЦИЯ ПО КАМЕРЕ, ОБЪЕКТИВУ И ОСВЕЩЕНИЮ")
    lines.append("=" * 90)

    lines.append(f"\nВХОДНЫЕ ТРЕБОВАНИЯ:")
    lines.append(f"  Размер объекта/дефекта: {req.defect_size_mm} мм, {req.defect_type.value}")
    lines.append(f"  Материал: {req.material.value}, {req.reflectivity.value}")
    lines.append(f"  FOV: {req.fov_width_mm}×{req.fov_height_mm} мм")
    lines.append(f"  Рабочая дистанция: {req.working_distance_mm} мм")
    lines.append(f"  Скорость: {req.line_speed_mm_s} мм/с")
    lines.append(f"  Движение: {'да' if req.is_moving else 'нет'}")
    lines.append(f"  Тип задачи: {req.task_type}")
    if req.task_type == "tracking":
        lines.append(f"  Скорость объекта: {req.object_speed_mm_s} мм/с")
        lines.append(f"  Допустимое смещение: {req.shift_ratio} × размера")
    lines.append(f"  Угол наклона камеры: {req.camera_tilt_deg}°")
    lines.append(f"  Дистанция сервера: {req.server_distance_m} м")
    lines.append(f"  Освещение в цеху: {req.ambient_light}")
    lines.append(f"  Режим света: {req.lighting_mode}")

    lines.append(f"\n--- ОБЩИЕ ПАРАМЕТРЫ ---")
    lines.append(f"  Требуемый FPS: {rec.fps_required}")
    lines.append(f"  Макс. выдержка: {rec.max_exposure_time_ms} мс")

    lines.append(f"\n--- РЕШЕНИЕ О СВЕТЕ ---")
    if rec.lighting_decision == "not_needed":
        lines.append(f"  ✅ Дополнительный свет: НЕ ТРЕБУЕТСЯ")
        lines.append(f"  Обоснование: {rec.lighting_reason}")
    elif rec.lighting_decision == "borderline":
        lines.append(f"  ⚠️ Свет на грани: {rec.lighting_reason}")
        lines.append(f"  Требуемая освещённость: {rec.required_illuminance_lux} лк")
    else:
        lines.append(f"  💡 Дополнительный свет: НУЖЕН")
        lines.append(f"  Обоснование: {rec.lighting_reason}")
        lines.append(f"  Требуемая освещённость: {rec.required_illuminance_lux} лк")
        lines.append(f"  Тип: {rec.lighting_notes}")

        lines.append(f"\n{'=' * 100}")
    lines.append(f"ВАРИАНТЫ КОМПЛЕКТОВ ({len(rec.variants)})")
    lines.append(f"{'=' * 100}")

    # Если ничего не найдено — подсказки
    if not rec.variants:
        lines.append("")
        lines.append("⚠️  НЕ НАЙДЕНО НИ ОДНОЙ КАМЕРЫ ПОД ТРЕБОВАНИЯ")
        lines.append("")
        lines.append("ВОЗМОЖНЫЕ ПРИЧИНЫ:")

        # Проверяем требуемое разрешение
        (req_w, req_h), _ = calculate_required_resolution(
            req.fov_width_mm, req.fov_height_mm,
            req.defect_size_mm, req.min_pixels_per_defect
        )

                # Максимум среди area-камер в базе
        max_area_res_w = max(
            (c['resolution'][0] for c in CAMERA_DATABASE
             if c.get('type') != 'line'),
            default=0
        )
        max_area_res_h = max(
            (c['resolution'][1] for c in CAMERA_DATABASE
             if c.get('type') != 'line'),
            default=0
        )

        if req_w > max_area_res_w or req_h > max_area_res_h:
            lines.append(f"  1. Требуемое разрешение {req_w}×{req_h} px")
            lines.append(f"     превышает максимум базы {max_area_res_w}×"
                         f"{max_area_res_h} px")
            lines.append(f"     Решение: уменьшите FOV или увеличьте "
                         f"размер дефекта")

        # Проверяем FOV
                # Проверяем FOV
        if req.defect_size_mm < 0.5:
            # Реальный максимум FOV = макс. разрешение / (пикс на мм)
            px_per_mm = req.min_pixels_per_defect / max(req.defect_size_mm, 0.001)
            max_fov_w = int(max_area_res_w / px_per_mm) if px_per_mm > 0 else 0
            max_fov_h = int(max_area_res_h / px_per_mm) if px_per_mm > 0 else 0

            # Сохраняем пропорции как в задаче
            if max_fov_w > 0 and max_fov_h > 0:
                aspect = req.fov_width_mm / max(req.fov_height_mm, 1)
                if aspect > 1:
                    max_fov_h = int(max_fov_w / aspect)
                else:
                    max_fov_w = int(max_fov_h * aspect)

            lines.append(f"  2. Дефект {req.defect_size_mm} мм — очень мелкий")
            lines.append(f"     Для FOV {req.fov_width_mm}×{req.fov_height_mm} мм")
            if max_fov_w > 0 and max_fov_h > 0:
                lines.append(f"     рекомендуем уменьшить FOV до "
                             f"{max_fov_w}×{max_fov_h} мм")
            lines.append(f"     (макс. разрешение area-камер {max_area_res_w}×"
                         f"{max_area_res_h} px)")

        # Проверяем свет
        if rec.required_illuminance_lux > 50000:
            lines.append(f"  3. Требуется свет {rec.required_illuminance_lux:.0f} лк —")
            lines.append(f"     это очень много (прямое солнце ~100 000 лк)")
            lines.append(f"     Решение: импульсный стробоскоп ИЛИ "
                         f"уменьшение FOV")

        # Проверяем FPS
        if rec.fps_required > 200:
            lines.append(f"  4. Требуемый FPS {rec.fps_required:.0f} — очень высокий")
            lines.append(f"     Решение: снизить скорость объекта или "
                         f"увеличить часть кадра между кадрами")

        lines.append("")
        lines.append("ЧТО ПОПРОБОВАТЬ:")
        lines.append(f"  • Уменьшить FOV: --fov-width {int(req.fov_width_mm/2)} "
                     f"--fov-height {int(req.fov_height_mm/2)}")
        lines.append(f"  • Увеличить размер дефекта: --defect-size "
                     f"{req.defect_size_mm * 2}")
        lines.append(f"  • Уменьшить мин. пикселей: --min-pixels "
                     f"{max(2, req.min_pixels_per_defect - 1)}")

    # Определяем группы
    group1 = [v for v in rec.variants if v.overall_factor <= 1.10]
    group2 = [v for v in rec.variants if 1.10 < v.overall_factor <= 1.20]
    group3 = [v for v in rec.variants if v.overall_factor > 1.20]

    # Сортируем по цене
    group1.sort(key=lambda v: v.total_price_usd)
    group2.sort(key=lambda v: v.total_price_usd)
    group3.sort(key=lambda v: v.total_price_usd)

    def print_group(title, group, emoji):
        lines.append(f"\n{emoji} {title} ({len(group)} камер)")
        lines.append("-" * 100)

        header = (
            f"{'#':<4} "
            f"{'Модель':<30} "
            f"{'Разр.':<11} "
            f"{'FPS':<6} "
            f"{'Запас':<8} "
            f"{'Интерфейс':<10} "
            f"{'Трафик':<10} "
            f"{'Цена':<10} "
            f"{'FOV':<4}"
        )
        lines.append(header)
        lines.append("-" * 100)

        for i, v in enumerate(group, 1):
            res_str = f"{v.resolution[0]}×{v.resolution[1]}"
            fov_ok = "✓" if v.fov_covers_required else "⚠"
            model_short = v.camera_model[:30]

            line = (
                f"{i:<4} "
                f"{model_short:<30} "
                f"{res_str:<11} "
                f"{v.fps_max:<6.0f} "
                f"×{v.overall_factor:<7.2f} "
                f"{v.interface:<10} "
                f"{f'{int(v.bandwidth_mbps)}M':<10} "
                f"${v.total_price_usd:<9.0f} "
                f"{fov_ok:<4}"
            )
            lines.append(line)

    print_group("МИНИМАЛЬНЫЙ ЗАПАС (до ×1.10)", group1, "🟢")
    print_group("УМЕРЕННЫЙ ЗАПАС (×1.11–1.20)", group2, "🟡")
    print_group("С ЗАПАСОМ (>×1.20)", group3, "🔴")

    lines.append("\n" + "=" * 100)
    return "\n".join(lines)


def print_recommendation(rec, req):
    print(format_recommendation_text(rec, req))


# ==============================================================================
# РАЗДЕЛ 10: ЭКСПОРТ PDF
# ==============================================================================

def export_to_pdf(rec, req, filename="camera_recommendation.pdf",
                   plot_filename=None):
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
            safe = str(item).encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 6, safe, ln=True)
        pdf.ln(3)

    section("Requirements", [
        f"Object: {req.defect_size_mm} mm, {req.defect_type.value}",
        f"FOV: {req.fov_width_mm}x{req.fov_height_mm} mm",
        f"Working distance: {req.working_distance_mm} mm",
        f"Task: {req.task_type}",
        f"Lighting: {rec.lighting_decision}",
    ])

    section("Lighting Decision", [
        f"Decision: {rec.lighting_decision}",
        f"Reason: {rec.lighting_reason}",
    ])

    for i, v in enumerate(rec.variants[:5]):
        section(f"Variant {i+1}", [
            f"Camera: {v.camera_model}",
            f"Lens: {v.lens_model}",
            f"Total: ${v.total_price_usd:.0f}",
        ])

    if plot_filename and os.path.exists(plot_filename):
        pdf.add_page()
        pdf.image(plot_filename, x=10, y=30, w=190)

    pdf.output(filename)
    print(f"\nPDF сохранён: {filename}")


# ==============================================================================
# РАЗДЕЛ 11: ЭКСПОРТ CSV
# ==============================================================================

def export_to_csv(rec, req, filename="camera_recommendation.csv"):
    rows = [
        ["Параметр", "Значение", "Единица"],
        ["--- ТРЕБОВАНИЯ ---", "", ""],
        ["Размер объекта", req.defect_size_mm, "мм"],
        ["FOV ширина", req.fov_width_mm, "мм"],
        ["FOV высота", req.fov_height_mm, "мм"],
        ["Рабочая дистанция", req.working_distance_mm, "мм"],
        ["Тип задачи", req.task_type, ""],
        ["Решение о свете", rec.lighting_decision, ""],
        ["Обоснование света", rec.lighting_reason, ""],
    ]

    for i, v in enumerate(rec.variants):
        rows.append([f"--- ВАРИАНТ {i+1} ---", "", ""])
        rows.append(["Камера", v.camera_model, ""])
        rows.append(["Разрешение", f"{v.resolution[0]}x{v.resolution[1]}", "px"])
        rows.append(["FPS max", v.fps_max, "кадр/с"])
        rows.append(["Интерфейс", v.interface, ""])
        rows.append(["Трафик", f"{v.bandwidth_mbps:.0f}", "Мбит/с"])
        rows.append(["Свет", v.lighting_model, ""])
        rows.append(["Итого", v.total_price_usd, "USD"])

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerows(rows)

    print(f"CSV сохранён: {filename}")


# ==============================================================================
# РАЗДЕЛ 12: GUI НА GRADIO
# ==============================================================================

def build_gradio_interface():
    if not GRADIO_AVAILABLE:
        print("Gradio не установлен.")
        return None

    def calculate_ui(*args):
        try:
            (defect_size_mm, defect_type, material, reflectivity, contrast,
             fov_width_mm, fov_height_mm, working_distance_mm,
             line_speed_mm_s, part_spacing_mm, images_per_part, is_moving,
             min_pixels_per_defect, ambient_light, budget, num_cameras,
             preferred_mount, camera_tilt_deg, server_distance_m,
             task_type, object_speed, shift_ratio, lighting_mode) = args

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
                server_distance_m=float(server_distance_m),
                task_type=task_type,
                object_speed_mm_s=float(object_speed),
                shift_ratio=float(shift_ratio),
                lighting_mode=lighting_mode,
            )
            rec = select_camera_system(req)
            return format_recommendation_text(rec, req)
        except Exception as e:
            import traceback
            return f"ОШИБКА: {e}\n\n{traceback.format_exc()}"

    with gr.Blocks(title="Camera & Lighting Selector") as interface:
        gr.Markdown("# Подбор камеры и освещения")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Объект")
                defect_size = gr.Number(label="Размер (мм)", value=0.5)
                defect_type = gr.Dropdown(choices=[d.value for d in DefectType],
                                          label="Тип дефекта", value=DefectType.DISPLACEMENT.value)
                material = gr.Dropdown(choices=[m.value for m in Material],
                                       label="Материал", value=Material.METAL.value)
                reflectivity = gr.Dropdown(choices=[r.value for r in Reflectivity],
                                           label="Отражательность", value=Reflectivity.SEMI_MATTE.value)
                contrast = gr.Dropdown(choices=[c.value for c in Contrast],
                                       label="Контраст", value=Contrast.DARK_ON_LIGHT.value)

            with gr.Column():
                gr.Markdown("### Геометрия")
                fov_w = gr.Number(label="FOV ширина (мм)", value=500)
                fov_h = gr.Number(label="FOV высота (мм)", value=300)
                working_dist = gr.Number(label="Рабочая дистанция (мм)", value=800)
                line_speed = gr.Number(label="Скорость (мм/с)", value=1000)
                part_spacing = gr.Number(label="Расстояние (мм)", value=200)
                images_per_part = gr.Number(label="Кадров на объект", value=1)
                is_moving = gr.Checkbox(label="Движется", value=True)

            with gr.Column():
                gr.Markdown("### Требования")
                min_px = gr.Number(label="Мин. пикселей", value=4)
                ambient = gr.Dropdown(choices=list(AMBIENT_LIGHT_LUX.keys()),
                                      label="Свет в цеху", value="обычный цех")
                budget = gr.Dropdown(choices=[b.value for b in BudgetLevel],
                                     label="Бюджет", value=BudgetLevel.MEDIUM.value)
                num_cam = gr.Number(label="Камер", value=1)
                preferred_mount = gr.Dropdown(choices=[m.value for m in LensMount],
                                              label="Крепление", value=LensMount.C.value)
                tilt = gr.Number(label="Наклон (°)", value=0.0)
                server_dist = gr.Number(label="Сервер (м)", value=3.0)

            with gr.Column():
                gr.Markdown("### Свет и тип")
                task_type = gr.Dropdown(choices=["inspection", "tracking", "detection"],
                                        label="Тип задачи", value="inspection")
                object_speed = gr.Number(label="Скорость объекта (мм/с)", value=0)
                shift_ratio = gr.Number(label="Смещение (доля)", value=0.3)
                lighting_mode = gr.Dropdown(choices=["auto", "on", "off"],
                                            label="Режим света", value="auto")

        btn = gr.Button("Рассчитать", variant="primary")
        output = gr.Textbox(label="Результат", lines=60)

        btn.click(fn=calculate_ui,
                  inputs=[defect_size, defect_type, material, reflectivity, contrast,
                          fov_w, fov_h, working_dist, line_speed, part_spacing,
                          images_per_part, is_moving, min_px, ambient, budget,
                          num_cam, preferred_mount, tilt, server_dist,
                          task_type, object_speed, shift_ratio, lighting_mode],
                  outputs=output)

    return interface


# ==============================================================================
# РАЗДЕЛ 13: CLI
# ==============================================================================

def parse_args():
    if len(sys.argv) == 1:
        print("Запустите с --help для справки.")
        sys.exit(0)

    parser = argparse.ArgumentParser(
        prog="check_camera.py",
        description="Калькулятор подбора камеры и освещения (USB3/GigE).",
    )

    parser.add_argument("--defect-size", type=float, default=0.5)
    parser.add_argument("--defect-type", type=str, default="displacement",
                        choices=["scratch", "chip", "displacement", "missing", "color", "crack"])
    parser.add_argument("--material", type=str, default="metal",
                        choices=["metal", "plastic", "glass", "fabric", "ceramic"])
    parser.add_argument("--reflectivity", type=str, default="semi_matte",
                        choices=["matte", "semi_matte", "glossy", "mirror"])
    parser.add_argument("--contrast", type=str, default="dark_on_light",
                        choices=["dark_on_light", "light_on_dark", "color"])
    parser.add_argument("--fov-width", type=float, default=500)
    parser.add_argument("--fov-height", type=float, default=300)
    parser.add_argument("--working-distance", type=float, default=800)
    parser.add_argument("--line-speed", type=float, default=0)
    parser.add_argument("--part-spacing", type=float, default=200)
    parser.add_argument("--images-per-part", type=int, default=1)
    parser.add_argument("--is-moving", action="store_true")
    parser.add_argument("--min-pixels", type=int, default=4)
    parser.add_argument("--ambient-light", type=str, default="normal",
                        choices=["bright", "normal", "dim", "dark"])
    parser.add_argument("--budget", type=str, default="medium",
                        choices=["low", "medium", "high"])
    parser.add_argument("--num-cameras", type=int, default=1)
    parser.add_argument("--mount", type=str, default="C",
                        choices=["C", "CS", "M12", "M42", "M58", "F"])
    parser.add_argument("--tilt", type=float, default=0.0)
    parser.add_argument("--server-distance", type=float, default=3.0)
    parser.add_argument("--total-area-width", type=float, default=0)
    parser.add_argument("--total-area-height", type=float, default=0)
    parser.add_argument("--overlap-pct", type=float, default=20.0)
    parser.add_argument("--task-type", type=str, default="inspection",
                        choices=["inspection", "tracking", "detection"])
    parser.add_argument("--object-speed", type=float, default=0)
    parser.add_argument("--shift-ratio", type=float, default=0.3)
    parser.add_argument("--lighting", type=str, default="auto",
                        choices=["auto", "on", "off"])
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--plots", action="store_true")
    parser.add_argument("--all", action="store_true")

    return parser.parse_args()


def map_ambient_light(value: str) -> str:
    return {
        "bright": "яркий цех (окна, солнце)",
        "normal": "обычный цех",
        "dim": "тусклый цех",
        "dark": "темнота (кожух)",
    }.get(value, "обычный цех")


def map_defect_type(value: str) -> DefectType:
    return {
        "scratch": DefectType.SCRATCH, "chip": DefectType.CHIP,
        "displacement": DefectType.DISPLACEMENT, "missing": DefectType.MISSING,
        "color": DefectType.COLOR, "crack": DefectType.CRACK,
    }[value]


def map_material(value: str) -> Material:
    return {
        "metal": Material.METAL, "plastic": Material.PLASTIC,
        "glass": Material.GLASS, "fabric": Material.FABRIC,
        "ceramic": Material.CERAMIC,
    }[value]


def map_reflectivity(value: str) -> Reflectivity:
    return {
        "matte": Reflectivity.MATTE, "semi_matte": Reflectivity.SEMI_MATTE,
        "glossy": Reflectivity.GLOSSY, "mirror": Reflectivity.MIRROR,
    }[value]


def map_contrast(value: str) -> Contrast:
    return {
        "dark_on_light": Contrast.DARK_ON_LIGHT,
        "light_on_dark": Contrast.LIGHT_ON_DARK,
        "color": Contrast.COLOR,
    }[value]


def map_budget(value: str) -> BudgetLevel:
    return {
        "low": BudgetLevel.LOW, "medium": BudgetLevel.MEDIUM,
        "high": BudgetLevel.HIGH,
    }[value]


def map_mount(value: str) -> LensMount:
    return {
        "C": LensMount.C, "CS": LensMount.CS, "M12": LensMount.M12,
        "M42": LensMount.M42, "M58": LensMount.M58, "F": LensMount.F,
    }[value]


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
        server_distance_m=args.server_distance,
        total_area_width_m=args.total_area_width if args.total_area_width > 0 else None,
        total_area_height_m=args.total_area_height if args.total_area_height > 0 else None,
        overlap_pct=args.overlap_pct,
        task_type=args.task_type,
        object_speed_mm_s=args.object_speed,
        shift_ratio=args.shift_ratio,
        lighting_mode=args.lighting,
    )


def run_single_mode(args):
    req = args_to_requirements(args)
    rec = select_camera_system(req)
    print_recommendation(rec, req)

    plot_file = None
    if args.all or args.plots:
        visualize_recommendation(rec, req)
        plot_file = "recommendation_plots.png"

    if args.all or args.pdf:
        export_to_pdf(rec, req, plot_filename=plot_file)

    if args.all or args.csv:
        export_to_csv(rec, req)


def main():
    args = parse_args()

    if args.gui:
        if GRADIO_AVAILABLE:
            interface = build_gradio_interface()
            if interface:
                interface.launch()
        return

    run_single_mode(args)


if __name__ == "__main__":
    main()
