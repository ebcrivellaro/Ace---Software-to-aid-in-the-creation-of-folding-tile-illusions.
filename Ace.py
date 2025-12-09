# Esse é o código do Ace.py, ao ser executado, ele cria uma janela com a imagem do monitor mas com um filtro aplicado em um retangulo no centro da tela
# O modelo atual do código é feito para monitores widescreen e pode ser modificado para aplicar a outros aspectos de monitores

#Importação da bibliotecas
import cv2
import numpy as np
import time
import pyautogui
from pynput import keyboard
import pygetwindow as gw

#Classe que controla a captura de tela
class ScreenCapture:
    def __init__(self):
        self.update_monitor_size()
    
    def update_monitor_size(self):
        """Atualiza as dimensões do monitor"""
        try:
            screen_size = pyautogui.size()
            self.monitor = {
                "top": 0,
                "left": 0,
                "width": screen_size.width,
                "height": screen_size.height
            }
        except Exception as e:
            print(f"Erro ao obter tamanho do monitor: {e}")
            self.monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
    
    def capture(self):
        """Captura a tela usando pyautogui"""
        try:
            screenshot = pyautogui.screenshot()
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"Erro na captura: {e}")
            return None

# Configurações
UPDATE_INTERVAL = 0.05
PREVIEW_ASPECT = 21/9

# Variáveis de controle
rect_x, rect_y = 0.5, 0.5
rect_height = 0.4
show_grid = True
running = True
outline_color = (0, 255, 0)
outline_thickness = 2
preview_window_name = "Preview - Filtro Inteligente (21:9)"
show_cell_outlines = False  
cell_outline_color = (255, 0, 0)
reverse_rotation = False

# Configurações de grid
GRID_PRESETS = [
    {'cols': 3, 'rows': 4, 'name': '3x4'},
    {'cols': 4, 'rows': 3, 'name': '4x3'},
    {'cols': 3, 'rows': 3, 'name': '3x3'},
    {'cols': 4, 'rows': 4, 'name': '4x4'}
]
current_grid = 0

# Inicializa o capturador de tela
screen_capturer = ScreenCapture()

def is_preview_active():
    try:
        active_window = gw.getActiveWindow()
        return active_window is not None and preview_window_name in active_window.title
    except:
        return False

def detect_rectangle(image):
    """Detecta retângulos na imagem"""
    if image is None:
        return None
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                center_x, center_y = image.shape[1]//2, image.shape[0]//2
                
                if (abs((x + w//2) - center_x) < image.shape[1]*0.3 and \
                   abs((y + h//2) - center_y) < image.shape[0]*0.3):
                    return x, y, w, h
        
        return None
    except Exception as e:
        print(f"Erro na detecção de retângulos: {e}")
        return None

def process_cell(cell, angle):
    """Processa uma célula individual da grade"""
    try:
        # Aplica a inversão de rotação se reverse_rotation for True
        if reverse_rotation:
            angle = -angle
            
        rotated = cv2.rotate(cell, cv2.ROTATE_90_CLOCKWISE if angle == 90 else cv2.ROTATE_90_COUNTERCLOCKWISE)
        return cv2.resize(rotated, (cell.shape[1], cell.shape[0]))
    except Exception as e:
        print(f"Erro ao processar célula: {e}")
        return cell

def apply_grid_effect(image):
    """Aplica o efeito de grade na imagem"""
    if not show_grid or image is None:
        return image
        
    try:
        h, w = image.shape[:2]
        grid = GRID_PRESETS[current_grid]
        
        rect_h = int(h * rect_height)
        rect_w = int(rect_h * (grid['cols']/grid['rows']))
        
        x1 = int(w * rect_x - rect_w/2)
        y1 = int(h * rect_y - rect_h/2)
        x2 = x1 + rect_w
        y2 = y1 + rect_h
        
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        rect_w, rect_h = x2 - x1, y2 - y1
        
        result = image.copy()
        
        if rect_w > 0 and rect_h > 0:
            roi = image[y1:y2, x1:x2].copy()
            cell_w = rect_w // grid['cols']
            cell_h = rect_h // grid['rows']
            
            for i in range(grid['cols']):
                for j in range(grid['rows']):
                    x, y = i * cell_w, j * cell_h
                    cell = roi[y:y+cell_h, x:x+cell_w].copy()
                    
                    if grid['name'] == '4x3':
                        rotation_pattern = [-90, 90, -90, 90,
                                             90, -90, 90, -90,
                                            -90, 90, -90, 90]
                        index = j * grid['cols'] + i
                        angle = rotation_pattern[index]
                    else:
                        if grid['cols'] == grid['rows']:
                            angle = 90 if (i + j) % 2 == 0 else -90
                        else:
                            angle = -90 if (i + j * grid['cols'] + 1) % 2 != 0 else 90

                    
                    processed_cell = process_cell(cell, angle)
                    if processed_cell.shape == cell.shape:
                        roi[y:y+cell_h, x:x+cell_w] = processed_cell
                    
                    # Desenha o outline da célula se ativado
                    if show_cell_outlines:
                        cv2.rectangle(roi, (x, y), (x+cell_w, y+cell_h), cell_outline_color, 1)
            
            result[y1:y2, x1:x2] = roi
        
        # Ajuste fino do retângulo
        adjust_factor = 1.00
        adj_x1 = int(x1 + (rect_w * (1 - adjust_factor)/2))
        adj_y1 = int(y1 + (rect_h * (1 - adjust_factor)/2))
        adj_x2 = int(x2 - (rect_w * (1 - adjust_factor)/2))
        adj_y2 = int(y2 - (rect_h * (1 - adjust_factor)/2))
        
        cv2.rectangle(result, (adj_x1, adj_y1), (adj_x2, adj_y2), outline_color, outline_thickness)
        
        # Mostra informações adicionais
        info_text = f"Grid: {grid['name']}"
        if show_cell_outlines:
            info_text += " | Outlines ON"
        if reverse_rotation:
            info_text += " | Rotação Invertida"
            
        cv2.putText(result, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, outline_color, 2)
        return result
    except Exception as e:
        print(f"Erro ao aplicar efeito de grade: {e}")
        return image

def on_press(key):
    global rect_x, rect_y, rect_height, show_grid, running, current_grid
    global show_cell_outlines, reverse_rotation  # Novas variáveis globais
    
    if not is_preview_active():
        return
        
    try:
        if key.char == 'p':
            screen = screen_capturer.capture()
            if screen is None:
                return
                
            rect = detect_rectangle(screen)
            if rect:
                x, y, w, h = rect
                h_img, w_img = screen.shape[:2]
                rect_x = (x + w/2) / w_img
                rect_y = (y + h/2) / h_img
                rect_height = h / h_img
        
        elif key.char == 'a': rect_x = max(0, rect_x - 0.01)
        elif key.char == 'd': rect_x = min(1, rect_x + 0.01)
        elif key.char == 'w': rect_y = max(0, rect_y - 0.01)
        elif key.char == 's': rect_y = min(1, rect_y + 0.01)
        elif key.char == 'q': rect_height = max(0.1, rect_height - 0.01)
        elif key.char == 'e': rect_height = min(0.9, rect_height + 0.01)
        elif key.char == 'g': show_grid = not show_grid
        elif key.char == '1': current_grid = 0
        elif key.char == '2': current_grid = 1
        elif key.char == '3': current_grid = 2
        elif key.char == '4': current_grid = 3
        
        # Nova funcionalidade: Toggle dos outlines das células
        elif key.char == 't': 
            show_cell_outlines = not show_cell_outlines
            print(f"Outlines das células: {'ON' if show_cell_outlines else 'OFF'}")
            
        # Nova funcionalidade: Inverter rotação
        elif key.char == 'r':
            reverse_rotation = not reverse_rotation
            print(f"Rotação invertida: {'ON' if reverse_rotation else 'OFF'}")
    
    except AttributeError:
        if key == keyboard.Key.esc: 
            running = False

# Configura o listener do teclado
listener = keyboard.Listener(on_press=on_press)
listener.start()

print("Controles (janela ativa):")
print("WASD: Mover retângulo")
print("Q/E: Ajustar tamanho")
print("G: Alternar grade")
print("1-4: Mudar grid (3x4, 4x3, 3x3, 4x4)")
print("P: Detectar retângulo automaticamente")
print("T: Alternar outlines das células")
print("R: Inverter direção de rotação")
print("ESC: Sair")

# Configura a janela de preview
preview_height = 1000
preview_width = int(preview_height * PREVIEW_ASPECT)

cv2.namedWindow(preview_window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(preview_window_name, preview_width, preview_height)
cv2.moveWindow(preview_window_name, 100, 100)

# Loop principal
while running:
    try:
        screen = screen_capturer.capture()
        if screen is None:
            time.sleep(1)
            continue
            
        processed = apply_grid_effect(screen)
        display_img = cv2.resize(processed, (preview_width, preview_height))
        cv2.imshow(preview_window_name, display_img)
        
        if cv2.waitKey(1) == 27: 
            running = False
        time.sleep(UPDATE_INTERVAL)
    except Exception as e:
        print(f"Erro no loop principal: {e}")
        running = False

# Limpeza final
cv2.destroyAllWindows()
listener.stop()