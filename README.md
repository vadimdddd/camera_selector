# Camera & Lighting Selector

Camera & Lighting Selector — инструмент для проектирования промышленных CV-систем. 
Подбирает камеру, объектив и освещение по требованиям заказчика (размер дефекта, FOV, скорость линии, материал, бюджет). 
База: 40+ камер (Basler, FLIR, Cognex, Hikrobot, IDS, Balluff, Teledyne DALSA), 30+ объективов 
(Computar, Kowa, Fujinon, Schneider), 50+ источников освещения (CCS, Advanced Illumination, Metaphase, Effilux, Smart Vision Lights). 
Расчёт разрешения, motion blur, FPS, затвора, интерфейса, DOF, углов обзора, наклона и перспективы, мощности освещения. 
Проверка совместимости, бюджета. Экспорт PDF/CSV, GUI на Gradio, CLI.

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
