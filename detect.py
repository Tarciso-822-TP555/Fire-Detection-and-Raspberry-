import cv2
import numpy as np
from ultralytics import YOLO
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import time
import threading
import logging
from collections import deque
import json
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Métricas Prometheus
FIRE_DETECTIONS = Counter('fire_detections_total', 'Total fire detections')
FIRE_CONFIDENCE = Gauge('fire_detection_confidence', 'Confidence of fire detection')
FIRE_AREA = Gauge('fire_detection_area', 'Area of detected fire')
FRAME_PROCESS_TIME = Histogram('frame_processing_seconds', 'Time to process frame')
FIRE_TREND = Gauge('fire_trend', 'Fire trend indicator (-1 decreasing, 0 stable, 1 increasing)')
FIRE_DETECTED = Gauge('fire_detected', 'Whether fire is currently detected (1=yes, 0=no)')
VIDEO_SOURCE = Gauge('video_source', 'Current video source (0=webcam, 1=video_file)')


class FireDetectionSystem:
    def __init__(self, model_path, camera_index=0, video_file=None):
        self.model = YOLO(model_path)
        self.video_file = video_file
        self.camera_index = camera_index
        self.use_webcam = video_file is None

        # Inicializa a fonte de vídeo
        self.cap = self.initialize_video_source()

        # Configuração para análise de tendência
        self.detection_history = deque(maxlen=60)
        self.fire_areas = deque(maxlen=30)
        self.trend_history = deque(maxlen=10)

        # Status do sistema
        self.current_frame = None
        self.processing = False
        self.frame_count = 0
        self.video_loop = True if video_file else False

        # Configuração da janela (MANTIDO)
        self.window_name = "Fire Detection System"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 800, 600)

        # Parâmetros NMS
        self.nms_threshold = 0.4

        # Métrica da fonte de vídeo
        VIDEO_SOURCE.set(0 if self.use_webcam else 1)

    def initialize_video_source(self):
        """Inicializa a fonte de vídeo (webcam ou arquivo)"""
        if self.use_webcam:
            logger.info(f"Inicializando webcam (dispositivo {self.camera_index})")
            cap = cv2.VideoCapture(self.camera_index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
        else:
            logger.info(f"Inicializando vídeo: {self.video_file}")
            cap = cv2.VideoCapture(self.video_file)

        return cap

    def apply_nms(self, boxes, scores, iou_threshold=0.4):
        """Aplica Non-Maximum Suppression para eliminar detecções redundantes"""
        if len(boxes) == 0:
            return []

        # Converte para formato numpy
        boxes_array = np.array(boxes)
        scores_array = np.array(scores)

        # Aplica NMS
        indices = cv2.dnn.NMSBoxes(
            bboxes=boxes_array.tolist(),
            scores=scores_array.tolist(),
            score_threshold=0.3,
            nms_threshold=iou_threshold
        )

        if len(indices) > 0:
            return indices.flatten().tolist()
        return []

    def restart_video_if_needed(self):
        """Reinicia o vídeo se chegou ao fim (apenas para modo arquivo)"""
        if not self.use_webcam and self.video_loop:
            ret, _ = self.cap.read()
            if not ret:
                logger.info("Reiniciando vídeo...")
                self.cap.release()
                self.cap = cv2.VideoCapture(self.video_file)

    def switch_to_webcam(self):
        """Alterna para modo webcam"""
        if not self.use_webcam:
            logger.info("Alternando para modo webcam...")
            self.cap.release()
            self.use_webcam = True
            self.video_loop = False
            self.cap = self.initialize_video_source()
            VIDEO_SOURCE.set(0)

    def switch_to_video(self):
        """Alterna para modo arquivo de vídeo"""
        if self.use_webcam:
            logger.info("Alternando para modo vídeo...")
            self.cap.release()
            self.use_webcam = False
            self.video_loop = True
            self.video_file = "/app/inputs/video.mp4"
            self.cap = self.initialize_video_source()
            VIDEO_SOURCE.set(1)

    def calculate_fire_trend(self, current_fire_area):
        """Calcula a tendência do fogo baseado na área detectada"""
        if len(self.fire_areas) < 5:
            self.fire_areas.append(current_fire_area)
            return 0

        self.fire_areas.append(current_fire_area)

        short_window = min(5, len(self.fire_areas))
        long_window = min(15, len(self.fire_areas))

        recent_avg = np.mean(list(self.fire_areas)[-short_window:])
        previous_avg = np.mean(list(self.fire_areas)[-long_window:-short_window]) if len(
            self.fire_areas) >= long_window else recent_avg

        if previous_avg > 0:
            change_percent = (recent_avg - previous_avg) / previous_avg * 100
        else:
            change_percent = 100 if recent_avg > 0 else 0

        INCREASE_THRESHOLD = 15
        DECREASE_THRESHOLD = -15

        if change_percent > INCREASE_THRESHOLD and recent_avg > 100:
            trend = 1
        elif change_percent < DECREASE_THRESHOLD and previous_avg > 100:
            trend = -1
        else:
            trend = 0

        self.trend_history.append(trend)
        if len(self.trend_history) >= 3:
            trend_counts = np.bincount(np.array(self.trend_history) + 1)
            smoothed_trend = np.argmax(trend_counts) - 1
            return smoothed_trend

        return trend

    def process_frame(self, frame):
        """Processa um frame e retorna informações de detecção com NMS"""
        start_time = time.time()

        results = self.model.predict(frame, conf=0.3, imgsz=640, verbose=False)
        result = results[0]

        fire_detected = False
        max_confidence = 0
        total_fire_area = 0

        # Coleta todas as detecções de fogo
        fire_boxes = []
        fire_scores = []
        fire_detections = []

        for box in result.boxes:
            if result.names[int(box.cls)] == 'fire':
                confidence = float(box.conf)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                fire_boxes.append([x1, y1, x2, y2])
                fire_scores.append(confidence)
                fire_detections.append({
                    'box': box,
                    'confidence': confidence,
                    'area': (x2 - x1) * (y2 - y1)
                })

        # Aplica NMS se houver múltiplas detecções
        nms_indices = []
        if len(fire_boxes) > 1:
            nms_indices = self.apply_nms(fire_boxes, fire_scores, self.nms_threshold)

            for idx in nms_indices:
                detection = fire_detections[idx]
                fire_detected = True
                max_confidence = max(max_confidence, detection['confidence'])
                total_fire_area += detection['area']

                FIRE_DETECTIONS.inc()
                # CORREÇÃO: Seta a confiança atual
                FIRE_CONFIDENCE.set(detection['confidence'])
                # CORREÇÃO: Seta a área atual
                FIRE_AREA.set(detection['area'])

        elif len(fire_boxes) == 1:
            detection = fire_detections[0]
            fire_detected = True
            max_confidence = detection['confidence']
            total_fire_area = detection['area']
            nms_indices = [0]

            FIRE_DETECTIONS.inc()
            # CORREÇÃO: Seta a confiança atual
            FIRE_CONFIDENCE.set(detection['confidence'])
            # CORREÇÃO: Seta a área atual
            FIRE_AREA.set(detection['area'])

        # CORREÇÃO CRÍTICA: Se não há fogo, reseta as métricas para zero
        if not fire_detected:
            FIRE_CONFIDENCE.set(0)  # Confiança zero quando não há fogo
            FIRE_AREA.set(0)  # Área zero quando não há fogo
            max_confidence = 0
            total_fire_area = 0

        # Atualiza histórico e calcula tendência
        self.detection_history.append(1 if fire_detected else 0)
        trend = self.calculate_fire_trend(total_fire_area)

        FIRE_TREND.set(trend)
        FIRE_DETECTED.set(1 if fire_detected else 0)

        # Gera frame anotado (MANTIDO)
        annotated_frame = result.plot()

        # Adiciona informações na tela (MANTIDO)
        trend_text = "↑ AUMENTANDO" if trend == 1 else "↓ DIMINUINDO" if trend == -1 else "→ ESTAVEL"
        source_text = "WEBCAM" if self.use_webcam else "VÍDEO"
        trend_color = (0, 0, 255) if trend == 1 else (0, 255, 255) if trend == -1 else (0, 255, 0)

        cv2.putText(annotated_frame, f"Fonte: {source_text}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(annotated_frame, f"Tendencia: {trend_text}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, trend_color, 2)
        cv2.putText(annotated_frame, f"Fogo: {'SIM' if fire_detected else 'NAO'}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255) if fire_detected else (0, 255, 0), 2)
        cv2.putText(annotated_frame, f"Area: {total_fire_area:.0f}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(annotated_frame,
                    f"Deteccoes: {len(fire_boxes)} -> {len(nms_indices) if len(fire_boxes) > 1 else len(fire_boxes)}",
                    (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Instruções de controle (MANTIDO)
        cv2.putText(annotated_frame, "Teclas: [Q] Sair | [W] Webcam | [V] Video | [R] Reiniciar",
                    (10, annotated_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        processing_time = time.time() - start_time
        FRAME_PROCESS_TIME.observe(processing_time)

        return annotated_frame, fire_detected, max_confidence, total_fire_area

    def handle_keyboard_input(self):
        """Processa entrada do teclado para controle do sistema"""
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            return 'quit'
        elif key == ord('w') or key == ord('W'):
            self.switch_to_webcam()
            return 'switch_webcam'
        elif key == ord('v') or key == ord('V'):
            self.switch_to_video()
            return 'switch_video'
        elif key == ord('r') or key == ord('R'):
            # Reinicia o vídeo atual
            if not self.use_webcam:
                self.cap.release()
                self.cap = cv2.VideoCapture(self.video_file)
                logger.info("Vídeo reiniciado")
            return 'restart'

        return None

    def run_detection(self):
        """Loop principal de detecção"""
        logger.info("Iniciando sistema de detecção de fogo...")
        logger.info("Controles: [Q] Sair | [W] Webcam | [V] Video | [R] Reiniciar")

        while True:
            # Processa entrada do teclado (MANTIDO)
            key_action = self.handle_keyboard_input()
            if key_action == 'quit':
                break

            # Reinicia vídeo se necessário
            self.restart_video_if_needed()

            ret, frame = self.cap.read()
            if not ret:
                if self.use_webcam:
                    logger.error("Erro ao capturar frame da câmera")
                    time.sleep(1)
                    continue
                else:
                    logger.info("Fim do vídeo alcançado")
                    if self.video_loop:
                        continue
                    else:
                        break

            self.processing = True
            self.frame_count += 1

            processed_frame, fire_detected, confidence, area = self.process_frame(frame)
            self.current_frame = processed_frame

            # Exibe o frame na janela (MANTIDO)
            cv2.imshow(self.window_name, processed_frame)

            self.processing = False

        cv2.destroyAllWindows()

    def start_prometheus(self, port=8001):
        def run_prometheus():
            start_http_server(port)
            logger.info(f"Servidor Prometheus iniciado na porta {port}")

        prometheus_thread = threading.Thread(target=run_prometheus, daemon=True)
        prometheus_thread.start()


def main():
    # Configurações via variáveis de ambiente
    MODEL_PATH = os.getenv('MODEL_PATH', "models/yolo11n_50epochs/weights/best.onnx")
    CAMERA_INDEX = int(os.getenv('CAMERA_INDEX', '0'))
    VIDEO_FILE = os.getenv('VIDEO_FILE')
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', '8001'))

    if VIDEO_FILE and not os.path.exists(VIDEO_FILE):
        logger.warning(f"Arquivo de vídeo não encontrado: {VIDEO_FILE}. Usando webcam.")
        VIDEO_FILE = None

    # Inicializa sistema
    fire_system = FireDetectionSystem(
        model_path=MODEL_PATH,
        camera_index=CAMERA_INDEX,
        video_file=VIDEO_FILE
    )

    # Inicia servidor Prometheus em thread separada
    fire_system.start_prometheus(PROMETHEUS_PORT)

    # Inicia detecção
    try:
        fire_system.run_detection()
    except KeyboardInterrupt:
        logger.info("Parando sistema...")
    finally:
        fire_system.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()