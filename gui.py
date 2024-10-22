import sys
import os
import shutil
import threading  # 스레딩을 위해
import time  # 지연을 위해
import win32gui
import win32process
import win32con
import win32api  # 메시지 전송을 위해
import psutil
import json  # JSON 저장 및 불러오기를 위해
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QDialog,
    QLineEdit,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QAbstractItemView,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage

from pynput import mouse  # 마우스 이벤트 감지를 위해

import cv2  # OpenCV를 사용한 이미지 매칭을 위해 추가
import numpy as np  # 이미지 매칭을 위해 추가

import os
import uuid
import datetime


class CustomWindow(QMainWindow):
    # 시그널 정의
    click_signal = pyqtSignal(dict, int)  # 클릭 정보와 hwnd를 함께 전달
    execution_finished_signal = pyqtSignal()
    update_image_signal = pyqtSignal(int)
    center_item_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        # 윈도우 설정
        self.setWindowTitle("Minimal White & Black UI")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #FFFFFF;
                border-radius: 10px;
            }
            QLabel {
                border-radius: 5px;
                background-color: #F5F5F5;
                padding: 15px;
                border: 1px solid #000000;
                font-size: 16px;
                color: #000000;
            }
            QListWidget {
                border-radius: 5px;
                border: 1px solid #000000;
                background-color: #FFFFFF;
                padding: 10px;
                color: #000000;
                font-size: 14px;
            }
            QPushButton {
                background-color: #FFFFFF;
                border-radius: 5px;
                padding: 10px;
                border: 2px solid #000000;
                font-size: 14px;
                color: #000000;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            """
        )

        # 메인 레이아웃
        main_layout = QVBoxLayout()

        # 이미지 레이블
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(800, 400)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #F5F5F5; color: #000000;")
        self.image_label.setText("No Image Available")
        main_layout.addWidget(self.image_label)

        # 리스트 위젯
        self.list_widget = QListWidget(self)
        self.list_widget.setFixedSize(800, 100)
        main_layout.addWidget(self.list_widget)

        # 버튼 레이아웃
        button_layout_top = QHBoxLayout()
        button_layout_bottom = QVBoxLayout()

        # 위, 아래 이동 버튼
        up_button = QPushButton("▲", self)
        down_button = QPushButton("▼", self)
        up_button.clicked.connect(self.move_item_up)
        down_button.clicked.connect(self.move_item_down)
        button_layout_top.addWidget(up_button)
        button_layout_top.addWidget(down_button)

        # 복제, 삭제, 설정 버튼
        copy_button = QPushButton("복제", self)
        delete_button = QPushButton("삭제", self)
        settings_button = QPushButton("설정", self)
        copy_button.clicked.connect(self.duplicate_item)
        delete_button.clicked.connect(self.delete_item)
        settings_button.clicked.connect(self.open_settings)
        button_layout_top.addWidget(copy_button)
        button_layout_top.addWidget(delete_button)
        button_layout_top.addWidget(settings_button)

        # 녹화 및 실행 상태 변수
        self.is_recording = False
        self.is_executing = False

        # 녹화 버튼
        self.record_button = QPushButton("녹화", self)
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout_bottom.addWidget(self.record_button)

        # 저장 버튼
        save_button = QPushButton("저장", self)
        save_button.clicked.connect(self.save_click_data)  # 저장 버튼 연결
        button_layout_bottom.addWidget(save_button)

        # 불러오기 버튼
        load_button = QPushButton("불러오기", self)
        load_button.clicked.connect(self.load_click_data)  # 불러오기 버튼 연결
        button_layout_bottom.addWidget(load_button)

        # 실행 버튼
        self.execute_button = QPushButton("실행", self)
        self.execute_button.clicked.connect(self.toggle_execution)
        button_layout_bottom.addWidget(self.execute_button)

        main_layout.addLayout(button_layout_top)
        main_layout.addLayout(button_layout_bottom)

        # 메인 위젯 설정
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # 제외할 hwnd 목록 (자신의 윈도우 포함)
        self.hwnd = int(self.winId())
        self.excluded_hwnds = [self.hwnd]

        # 클릭 데이터 리스트
        self.click_data_list = []

        # 시그널 연결
        self.click_signal.connect(self.handle_click_signal)
        self.execution_finished_signal.connect(self.on_execution_finished)
        self.update_image_signal.connect(self.on_update_image)
        self.center_item_signal.connect(self.center_list_widget_on_item)

    def toggle_recording(self):
        """녹화 상태를 토글하고 UI를 업데이트합니다."""
        if self.is_recording:
            # 녹화 중지
            self.record_button.setText("녹화")
            self.record_button.setStyleSheet(
                "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
            )
            if hasattr(self, "mouse_listener"):
                self.mouse_listener.stop()
        else:
            # 녹화 시작 전에 기존 데이터가 있는지 확인
            if self.click_data_list:
                reply = self.show_custom_dialog(
                    "기록 삭제 확인", "기존 기록을 삭제할까요?", "예", "아니오"
                )
                if reply == "예":
                    # 기존 데이터 삭제
                    self.click_data_list.clear()
                    self.list_widget.clear()
                else:
                    # 녹화 시작하지 않음
                    return
            # 녹화 시작
            if self.is_executing:
                self.toggle_execution()
            self.record_button.setText("중지")
            self.record_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
            self.start_listening_for_clicks()
        self.is_recording = not self.is_recording

    def show_custom_dialog(self, title, message, accept_text, reject_text):
        """커스텀 다이얼로그를 생성하여 사용자에게 메시지를 보여줍니다."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setFixedSize(300, 150)
        dialog.setStyleSheet(
            """
            QDialog {
                background-color: #FFFFFF;
                border: 2px solid #000000;
            }
            QLabel {
                font-size: 14px;
                color: #000000;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #000000;
                padding: 5px;
                font-size: 14px;
                color: #000000;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            """
        )

        layout = QVBoxLayout()
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        button_layout = QHBoxLayout()
        accept_button = QPushButton(accept_text)
        reject_button = QPushButton(reject_text)
        accept_button.clicked.connect(lambda: dialog.done(1))
        reject_button.clicked.connect(lambda: dialog.done(0))
        button_layout.addWidget(accept_button)
        button_layout.addWidget(reject_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        result = dialog.exec_()
        return accept_text if result == 1 else reject_text

    def show_custom_message(self, title, message):
        """커스텀 메시지 다이얼로그를 보여줍니다."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setFixedSize(300, 150)
        dialog.setStyleSheet(
            """
            QDialog {
                background-color: #FFFFFF;
                border: 2px solid #000000;
            }
            QLabel {
                font-size: 14px;
                color: #000000;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #000000;
                padding: 5px;
                font-size: 14px;
                color: #000000;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            """
        )

        layout = QVBoxLayout()
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        ok_button = QPushButton("확인")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def save_click_data(self):
        """기록된 클릭 데이터를 JSON 파일로 저장합니다."""
        if not self.click_data_list:
            self.show_custom_message("저장", "저장할 데이터가 없습니다.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "파일 저장", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if file_name:
            try:
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(self.click_data_list, f, ensure_ascii=False, indent=4)
                self.show_custom_message("저장 완료", "데이터가 저장되었습니다.")
            except Exception as e:
                self.show_custom_message(
                    "저장 실패", f"데이터 저장 중 오류가 발생했습니다:\n{e}"
                )

    def load_click_data(self):
        """JSON 파일에서 클릭 데이터를 불러와 기존 데이터를 대체합니다."""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "파일 열기", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if file_name:
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                # 기존 데이터 대체
                self.click_data_list = loaded_data
                # 리스트 위젯 업데이트
                self.list_widget.clear()
                for click_info in self.click_data_list:
                    summary = self.create_summary(click_info)
                    self.list_widget.addItem(summary)
                self.show_custom_message("불러오기 완료", "데이터가 불러와졌습니다.")
            except Exception as e:
                self.show_custom_message(
                    "불러오기 실패", f"데이터 불러오기 중 오류가 발생했습니다:\n{e}"
                )

    def start_listening_for_clicks(self):
        """마우스 클릭 이벤트 리스너를 시작합니다."""
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()

    def on_click(self, x, y, button, pressed):
        """마우스 클릭 이벤트를 처리합니다."""
        if self.is_recording and pressed:
            hwnd = win32gui.WindowFromPoint((x, y))
            # 자신의 GUI나 설정 다이얼로그에서의 클릭은 무시
            if hwnd in self.excluded_hwnds:
                return
            self.record_click(hwnd, button, x, y)

    def record_click(self, hwnd, button, x, y):
        """클릭 정보를 기록하고 리스트에 추가합니다."""
        # 상대 좌표 계산
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        relative_x = x - left
        relative_y = y - top

        # 클릭 타입 설정
        click_type = "Click" if button == mouse.Button.left else "Right Click"
        window_class = win32gui.GetClassName(hwnd)
        window_text = win32gui.GetWindowText(hwnd)
        program = self.get_program_name_from_hwnd(hwnd)
        depth = self.get_window_depth(hwnd)
        window_title = win32gui.GetWindowText(hwnd)  # 윈도우 창 이름

        # 클릭 정보 딕셔너리 생성 (hwnd는 저장하지 않음)
        click_info = {
            "x": relative_x,
            "y": relative_y,
            "click_type": click_type,
            "window_class": window_class,
            "window_text": window_text,
            "window_title": window_title,
            "depth": depth,
            "program": program,
            # 추가된 필드 초기화
            "is_skip": False,
            "skip_image_path": "",
            "skip_image_target": {},
            "is_wait": False,
            "wait_image_path": "",
            "wait_image_target": {},
            "keyboard": "",
        }

        # 클릭 시그널 발송 (메인 스레드에서 GUI 업데이트)
        self.click_signal.emit(click_info, hwnd)

    def handle_click_signal(self, click_info, hwnd):
        """메인 스레드에서 클릭 정보를 처리합니다."""
        self.click_data_list.append(click_info)
        summary = self.create_summary(click_info)
        self.list_widget.addItem(summary)
        # 이미지 레이블 업데이트
        self.update_image_label(hwnd)

    def create_summary(self, click_info):
        """리스트 아이템에 표시할 요약 정보를 생성합니다."""
        summary = f"({click_info['x']}, {click_info['y']}) {click_info['window_title']} {click_info['program']}"
        max_length = 80
        if len(summary) > max_length:
            summary = summary[: max_length - 3] + "..."
        return summary

    def get_program_name_from_hwnd(self, hwnd):
        """hwnd로부터 프로그램 이름을 가져옵니다."""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = psutil.Process(pid)
            return process.name()
        except psutil.NoSuchProcess:
            return "Unknown"

    def get_window_depth(self, hwnd):
        """윈도우의 깊이를 계산합니다."""
        depth = 0
        while hwnd:
            hwnd = win32gui.GetParent(hwnd)
            depth += 1
        return depth

    def move_item_up(self):
        """선택된 아이템을 위로 이동합니다."""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            self.click_data_list.insert(
                current_row - 1, self.click_data_list.pop(current_row)
            )
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentRow(current_row - 1)

    def move_item_down(self):
        """선택된 아이템을 아래로 이동합니다."""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            self.click_data_list.insert(
                current_row + 1, self.click_data_list.pop(current_row)
            )
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentRow(current_row + 1)

    def duplicate_item(self):
        """선택된 아이템을 복제합니다."""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            self.click_data_list.insert(
                current_row + 1, self.click_data_list[current_row].copy()
            )
            item_text = self.list_widget.item(current_row).text()
            self.list_widget.insertItem(current_row + 1, item_text)

    def delete_item(self):
        """선택된 아이템을 삭제합니다."""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            del self.click_data_list[current_row]
            self.list_widget.takeItem(current_row)

    def open_settings(self):
        """설정 다이얼로그를 엽니다."""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            click_info = self.click_data_list[current_row]
            dialog = SettingsDialog(click_info, parent=self)
            dialog_hwnd = int(dialog.winId())
            self.excluded_hwnds.append(dialog_hwnd)
            if dialog.exec_() == QDialog.Accepted:
                summary = self.create_summary(click_info)
                self.list_widget.item(current_row).setText(summary)
            self.excluded_hwnds.remove(dialog_hwnd)

    def toggle_execution(self):
        """실행 상태를 토글하고 UI를 업데이트합니다."""
        if self.is_executing:
            # 실행 중지
            self.is_executing = False  # 먼저 실행 중지
        else:
            # 실행 시작
            if self.is_recording:
                self.toggle_recording()
            self.execute_button.setText("중지")
            self.execute_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
            self.is_executing = True
            # 실행 스레드 시작
            self.execution_thread = threading.Thread(target=self.execute_clicks)
            self.execution_thread.start()

    def on_execution_finished(self):
        """실행 완료 후 UI를 업데이트합니다."""
        self.is_executing = False
        self.execute_button.setText("실행")
        self.execute_button.setStyleSheet(
            "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
        )

    def execute_clicks(self):
        """기록된 클릭들을 실행합니다."""
        for idx, click_info in enumerate(self.click_data_list):
            if not self.is_executing:
                break

            hwnd = None
            # 최대 60초 동안 1초 간격으로 hwnd를 찾습니다.
            max_wait_time = 60
            waited_time = 0
            while hwnd is None and waited_time < max_wait_time:
                hwnd = self.find_matching_hwnd(click_info)
                if hwnd:
                    break
                else:
                    time.sleep(1)
                    waited_time += 1
                    print(f"Waiting for hwnd... {waited_time} seconds elapsed.")

            if hwnd:
                # is_skip 처리
                if click_info.get("is_skip"):
                    should_skip = self.check_skip_condition(click_info)
                    if should_skip:
                        print(f"Skipping action at index {idx} due to skip condition.")
                        continue

                # is_wait 처리
                if click_info.get("is_wait"):
                    self.handle_wait_condition(click_info)

                self.send_click(hwnd, click_info)
                self.update_image_signal.emit(hwnd)
                self.center_item_signal.emit(idx)
            else:
                print(
                    f"Could not find hwnd for click_info: {click_info} after {max_wait_time} seconds."
                )
                matching_hwnds = self.find_hwnds_by_class(click_info["window_class"])
                print(
                    f"Found {len(matching_hwnds)} hwnds with window_class '{click_info['window_class']}':"
                )
                for hwnd_info in matching_hwnds:
                    print(hwnd_info)
                    print(
                        f"Enabled: {hwnd_info['enabled']}, Visible: {hwnd_info['visible']}"
                    )
                time.sleep(0.1)

        self.execution_finished_signal.emit()

    def check_skip_condition(self, click_info):
        """Skip 조건을 확인합니다."""
        target_info = click_info.get("skip_image_target")
        image_path = click_info.get("skip_image_path")
        if not target_info or not image_path:
            return False

        hwnd = self.find_matching_hwnd(target_info)
        if hwnd:
            # 이미지 매칭 수행
            similarity = self.compare_window_image_with_target(hwnd, image_path)
            print(f"Skip condition similarity: {similarity}")
            if similarity >= 0.99:
                return True
        return False

    def handle_wait_condition(self, click_info):
        """Wait 조건을 처리합니다."""
        target_info = click_info.get("wait_image_target")
        image_path = click_info.get("wait_image_path")
        if not target_info or not image_path:
            return

        max_wait_time = 300
        waited_time = 0
        while waited_time < max_wait_time:
            hwnd = self.find_matching_hwnd(target_info)
            if hwnd:
                similarity = self.compare_window_image_with_target(hwnd, image_path)
                print(f"Wait condition similarity: {similarity}")
                if similarity >= 0.99:
                    break
            time.sleep(1)
            waited_time += 1
            print(f"Waiting for condition... {waited_time} seconds elapsed.")

    def compare_window_image_with_target(self, hwnd, image_path):
        """윈도우의 이미지 내에서 타겟 이미지를 찾아 유사도를 반환합니다."""
        try:
            # 테스트 폴더 생성
            test_dir = "./test"
            if not os.path.exists(test_dir):
                os.makedirs(test_dir)

            # Convert path to absolute and normalize
            if not os.path.isabs(image_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                image_path = os.path.join(script_dir, image_path)

            image_path = os.path.normpath(image_path)

            if not os.path.exists(image_path):
                print(f"Image file not found: {image_path}")
                return 0

            # Capture window image
            window_image = self.capture_hwnd_image_pil(hwnd)
            if window_image is None:
                print("Failed to capture window image")
                return 0

            # 현재 시간과 UUID를 조합하여 고유한 파일명 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            base_filename = f"{timestamp}_{unique_id}"

            # 윈도우 캡처 이미지 저장
            window_capture_path = os.path.join(test_dir, f"{base_filename}_window.png")
            window_image.save(window_capture_path)

            # Convert PIL image to numpy array
            window_array = np.array(window_image)
            window_gray = cv2.cvtColor(window_array, cv2.COLOR_RGB2GRAY)

            # Load target image with explicit encoding handling
            target_gray = cv2.imdecode(
                np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE
            )

            if target_gray is None:
                print(f"Failed to load target image: {image_path}")
                return 0

            print(f"Window image shape: {window_gray.shape}")
            print(f"Target image shape: {target_gray.shape}")

            # Perform template matching
            result = cv2.matchTemplate(window_gray, target_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            # 매칭 결과 이미지 생성 및 저장
            result_image = window_array.copy()
            h, w = target_gray.shape
            x, y = max_loc
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

            result_path = os.path.join(test_dir, f"{base_filename}_result.png")
            cv2.imwrite(result_path, cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR))

            print(f"Saved window capture: {window_capture_path}")
            print(f"Saved matching result: {result_path}")
            print(f"Match location: {max_loc}")
            print(f"Similarity: {max_val:.4f}")

            return max_val

        except Exception as e:
            print(f"Image comparison error: {str(e)}")
            import traceback

            traceback.print_exc()
            return 0

    def find_hwnds_by_class(self, window_class):
        """주어진 window_class와 일치하는 모든 hwnd의 정보를 반환합니다."""
        hwnds_info = []
        all_hwnds = self.get_all_hwnds()
        for hwnd in all_hwnds:
            current_window_class = win32gui.GetClassName(hwnd)
            if current_window_class == window_class:
                window_text = win32gui.GetWindowText(hwnd)
                depth = self.get_window_depth(hwnd)
                program = self.get_program_name_from_hwnd(hwnd)
                window_title = win32gui.GetWindowText(hwnd)
                enabled = win32gui.IsWindowEnabled(hwnd)
                visible = win32gui.IsWindowVisible(hwnd)

                hwnd_info = {
                    "hwnd": hwnd,
                    "window_class": current_window_class,
                    "window_text": window_text,
                    "window_title": window_title,
                    "depth": depth,
                    "program": program,
                    "enabled": enabled,  # Enabled 상태 추가
                    "visible": visible,  # Visible 상태 추가
                }
                hwnds_info.append(hwnd_info)
        return hwnds_info

    def find_matching_hwnd(self, click_info):
        """기록된 정보와 일치하는 hwnd를 찾습니다."""
        all_hwnds = self.get_all_hwnds()
        for hwnd in all_hwnds:
            if not win32gui.IsWindowEnabled(hwnd) or not win32gui.IsWindowVisible(hwnd):
                continue
            window_class = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            depth = self.get_window_depth(hwnd)
            program = self.get_program_name_from_hwnd(hwnd)
            window_title = win32gui.GetWindowText(hwnd)  # 윈도우 창 이름

            if (
                window_class == click_info["window_class"]
                and window_text == click_info["window_text"]
                and window_title == click_info["window_title"]
                and depth == click_info["depth"]
                and program == click_info["program"]
            ):
                return hwnd
        return None

    def send_click(self, hwnd, click_info):
        """지정된 좌표에서 hwnd로 클릭 메시지를 전송합니다."""
        x = click_info["x"]
        y = click_info["y"]
        click_type = click_info["click_type"]
        lParam = win32api.MAKELONG(x, y)
        if click_type == "Click":
            # WM_LBUTTONDOWN 및 WM_LBUTTONUP 전송
            win32api.PostMessage(
                hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam
            )
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, None, lParam)
        elif click_type == "Right Click":
            # WM_RBUTTONDOWN 및 WM_RBUTTONUP 전송
            win32api.PostMessage(
                hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam
            )
            win32api.PostMessage(hwnd, win32con.WM_RBUTTONUP, None, lParam)
        elif click_type == "Double Click":
            # WM_LBUTTONDBLCLK 및 WM_LBUTTONUP 전송
            win32api.PostMessage(
                hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lParam
            )
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, None, lParam)

    def get_all_hwnds(self):
        """현재 세션의 모든 hwnd를 가져옵니다."""
        hwnds = []
        win32gui.EnumWindows(self.enum_windows_callback, hwnds)
        all_hwnds = []
        for hwnd in hwnds:
            all_hwnds.append(hwnd)
            all_hwnds.extend(self.get_all_descendants(hwnd))
        return all_hwnds

    def enum_windows_callback(self, hwnd, hwnds):
        """EnumWindows 콜백 함수"""
        hwnds.append(hwnd)

    def get_all_descendants(self, hwnd):
        """모든 자식 hwnd를 재귀적으로 가져옵니다."""
        hwnd_list = []
        child_hwnds = []

        def callback(child_hwnd, _):
            child_hwnds.append(child_hwnd)

        win32gui.EnumChildWindows(hwnd, callback, None)
        for child_hwnd in child_hwnds:
            hwnd_list.append(child_hwnd)
            hwnd_list.extend(self.get_all_descendants(child_hwnd))
        return hwnd_list

    def update_image_label(self, hwnd):
        """hwnd의 이미지를 image_label에 업데이트합니다."""
        # hwnd의 이미지를 캡처하여 표시
        pixmap = self.capture_hwnd_image(hwnd)
        if pixmap:
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText("No Image Available")

    def on_update_image(self, hwnd):
        """update_image_signal 시그널을 처리하여 image_label을 업데이트합니다."""
        self.update_image_label(hwnd)

    def capture_hwnd_image(self, hwnd):
        """Windows API를 사용하여 hwnd의 이미지를 캡처합니다."""
        import win32ui
        from PIL import Image
        import io

        # 윈도우 사각형 얻기
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        # 디바이스 컨텍스트 생성
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        # BitBlt
        result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        if result == 0:
            # BitBlt 실패
            return None
        # 비트맵 정보를 메모리에 저장
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr,
            "raw",
            "BGRX",
            0,
            1,
        )
        # 클린업
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        # PIL 이미지를 QPixmap으로 변환
        buffer = io.BytesIO()
        im.save(buffer, format="PNG")
        qt_image = QImage.fromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qt_image)
        # image_label 크기에 맞게 픽스맵 크기 조정
        pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio)
        return pixmap

    def capture_hwnd_image_pil(self, hwnd):
        """hwnd의 이미지를 PIL 이미지로 반환합니다."""
        import win32ui
        from PIL import Image

        # 윈도우 사각형 얻기
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        # 디바이스 컨텍스트 생성
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        # BitBlt
        result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        if result == 0:
            # BitBlt 실패
            return None
        # 비트맵 정보를 메모리에 저장
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr,
            "raw",
            "BGRX",
            0,
            1,
        )
        # 클린업
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        return im

    def center_list_widget_on_item(self, idx):
        """리스트 위젯을 idx에 해당하는 아이템에 중앙 정렬합니다."""
        item = self.list_widget.item(idx)
        self.list_widget.scrollToItem(item, QAbstractItemView.PositionAtCenter)
        self.list_widget.setCurrentRow(idx)


class SettingsDialog(QDialog):
    # 시그널 정의
    skip_target_selected_signal = pyqtSignal()
    wait_target_selected_signal = pyqtSignal()

    def __init__(self, click_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setGeometry(300, 300, 400, 300)

        self.click_info = click_info  # 클릭 정보 저장

        # 타겟 정보 초기화
        self.skip_target_info = click_info.get("skip_image_target", {})
        self.wait_target_info = click_info.get("wait_image_target", {})

        # 시그널 연결
        self.skip_target_selected_signal.connect(self.on_skip_target_selected)
        self.wait_target_selected_signal.connect(self.on_wait_target_selected)

        # 폼 레이아웃 설정
        form_layout = QFormLayout()

        # 설정 필드들 초기화
        self.click_type = QComboBox(self)
        self.click_type.addItems(["Click", "Double Click", "Right Click"])
        self.click_type.setCurrentText(click_info.get("click_type", "Click"))

        self.window_class = QLineEdit(self)
        self.window_class.setText(click_info.get("window_class", ""))

        self.window_text = QLineEdit(self)
        self.window_text.setText(click_info.get("window_text", ""))

        self.window_title = QLineEdit(self)
        self.window_title.setText(click_info.get("window_title", ""))

        self.depth = QLineEdit(self)
        self.depth.setText(str(click_info.get("depth", 0)))

        self.program = QLineEdit(self)
        self.program.setText(click_info.get("program", ""))

        self.is_skip = QCheckBox(self)
        self.is_skip.setChecked(click_info.get("is_skip", False))
        self.is_skip.stateChanged.connect(self.update_skip_widgets)

        self.skip_image = QPushButton("이미지 선택", self)
        self.skip_image.clicked.connect(self.select_skip_image)
        self.skip_image_path = click_info.get("skip_image_path", "")
        if self.skip_image_path:
            display_text = self.truncate_path(self.skip_image_path)
            self.skip_image.setText(display_text)

        self.skip_target_button = QPushButton("Skip Target 설정", self)
        self.skip_target_button.clicked.connect(self.select_skip_target)
        if self.skip_target_info:
            self.skip_target_button.setText("Target Selected")

        self.is_wait = QCheckBox(self)
        self.is_wait.setChecked(click_info.get("is_wait", False))
        self.is_wait.stateChanged.connect(self.update_wait_widgets)

        self.wait_image = QPushButton("이미지 선택", self)
        self.wait_image.clicked.connect(self.select_wait_image)
        self.wait_image_path = click_info.get("wait_image_path", "")
        if self.wait_image_path:
            display_text = self.truncate_path(self.wait_image_path)
            self.wait_image.setText(display_text)

        self.wait_target_button = QPushButton("Wait Target 설정", self)
        self.wait_target_button.clicked.connect(self.select_wait_target)
        if self.wait_target_info:
            self.wait_target_button.setText("Target Selected")

        self.keyboard = QLineEdit(self)
        self.keyboard.setText(click_info.get("keyboard", ""))

        # 폼 레이아웃에 위젯 추가
        form_layout.addRow("Click Type:", self.click_type)
        form_layout.addRow("Window Class:", self.window_class)
        form_layout.addRow("Window Text:", self.window_text)
        form_layout.addRow("Window Title:", self.window_title)
        form_layout.addRow("Depth:", self.depth)
        form_layout.addRow("Program:", self.program)
        form_layout.addRow("Skip:", self.is_skip)
        form_layout.addRow("Skip Image:", self.skip_image)
        form_layout.addRow("Skip Target:", self.skip_target_button)
        form_layout.addRow("Wait:", self.is_wait)
        form_layout.addRow("Wait Image:", self.wait_image)
        form_layout.addRow("Wait Target:", self.wait_target_button)
        form_layout.addRow("Keyboard:", self.keyboard)

        # 저장 및 취소 버튼 (한 줄에 위치)
        self.save_button = QPushButton("저장", self)
        self.cancel_button = QPushButton("취소", self)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        form_layout.addRow(button_layout)

        self.setLayout(form_layout)

        # 설정창 스타일 적용
        self.setStyleSheet(
            """
            QDialog {
                background-color: #FFFFFF;
                border-radius: 10px;
            }
            QComboBox, QLineEdit {
                border: 1px solid #000000;
                padding: 5px;
                font-size: 14px;
            }
            QCheckBox {
                font-size: 14px;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 2px solid #000000;
                padding: 10px;
                font-size: 14px;
                color: #000000;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            """
        )

        # 초기 상태 설정
        self.update_skip_widgets(self.is_skip.checkState())
        self.update_wait_widgets(self.is_wait.checkState())

    def update_skip_widgets(self, state):
        """is_skip 체크박스의 상태에 따라 관련 위젯 활성화/비활성화"""
        is_enabled = state == Qt.Checked
        self.skip_image.setEnabled(is_enabled)
        self.skip_target_button.setEnabled(is_enabled)

    def update_wait_widgets(self, state):
        """is_wait 체크박스의 상태에 따라 관련 위젯 활성화/비활성화"""
        is_enabled = state == Qt.Checked
        self.wait_image.setEnabled(is_enabled)
        self.wait_target_button.setEnabled(is_enabled)

    def select_skip_image(self):
        """Skip 이미지 선택 및 처리"""
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(
            self, "파일 선택", "", "Images (*.png *.xpm *.jpg)"
        )
        if file_path:
            # 복사할 폴더 확인 및 생성
            skip_images_dir = "./.skip_images"
            if not os.path.exists(skip_images_dir):
                os.makedirs(skip_images_dir)

            # 이미지 파일 복사
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(skip_images_dir, file_name)
            shutil.copy(file_path, dest_path)

            # 상대 경로 저장
            self.skip_image_path = os.path.relpath(dest_path)

            # 버튼에 선택된 경로 일부 표시
            display_text = self.truncate_path(self.skip_image_path)
            self.skip_image.setText(display_text)

    def select_wait_image(self):
        """Wait 이미지 선택 및 처리"""
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(
            self, "파일 선택", "", "Images (*.png *.xpm *.jpg)"
        )
        if file_path:
            # 복사할 폴더 확인 및 생성
            wait_images_dir = "./.wait_images"
            if not os.path.exists(wait_images_dir):
                os.makedirs(wait_images_dir)

            # 이미지 파일 복사
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(wait_images_dir, file_name)
            shutil.copy(file_path, dest_path)

            # 상대 경로 저장
            self.wait_image_path = os.path.relpath(dest_path)

            # 버튼에 선택된 경로 일부 표시
            display_text = self.truncate_path(self.wait_image_path)
            self.wait_image.setText(display_text)

    def select_skip_target(self):
        """Skip Target 선택"""
        self.hide()
        self.is_selecting_target = True
        self.mouse_listener = mouse.Listener(on_click=self.on_skip_target_click)
        self.mouse_listener.start()

    def on_skip_target_click(self, x, y, button, pressed):
        if pressed and self.is_selecting_target:
            self.is_selecting_target = False
            self.mouse_listener.stop()
            hwnd = win32gui.WindowFromPoint((x, y))
            # 자신의 윈도우는 제외
            if hwnd == int(self.winId()) or hwnd == int(self.parent().winId()):
                QTimer.singleShot(0, self.show)
                return
            # 윈도우 정보 가져오기
            window_class = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            depth = self.parent().get_window_depth(hwnd)
            program = self.parent().get_program_name_from_hwnd(hwnd)
            window_title = win32gui.GetWindowText(hwnd)
            # 타겟 정보 저장
            self.skip_target_info = {
                "window_class": window_class,
                "window_text": window_text,
                "window_title": window_title,
                "depth": depth,
                "program": program,
            }
            # 시그널 발송하여 GUI 업데이트
            self.skip_target_selected_signal.emit()

    def on_skip_target_selected(self):
        self.skip_target_button.setText("Target Selected")
        self.show()

    def select_wait_target(self):
        """Wait Target 선택"""
        self.hide()
        self.is_selecting_target = True
        self.mouse_listener = mouse.Listener(on_click=self.on_wait_target_click)
        self.mouse_listener.start()

    def on_wait_target_click(self, x, y, button, pressed):
        if pressed and self.is_selecting_target:
            self.is_selecting_target = False
            self.mouse_listener.stop()
            hwnd = win32gui.WindowFromPoint((x, y))
            # 자신의 윈도우는 제외
            if hwnd == int(self.winId()) or hwnd == int(self.parent().winId()):
                QTimer.singleShot(0, self.show)
                return
            # 윈도우 정보 가져오기
            window_class = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            depth = self.parent().get_window_depth(hwnd)
            program = self.parent().get_program_name_from_hwnd(hwnd)
            window_title = win32gui.GetWindowText(hwnd)
            # 타겟 정보 저장
            self.wait_target_info = {
                "window_class": window_class,
                "window_text": window_text,
                "window_title": window_title,
                "depth": depth,
                "program": program,
            }
            # 시그널 발송하여 GUI 업데이트
            self.wait_target_selected_signal.emit()

    def on_wait_target_selected(self):
        self.wait_target_button.setText("Target Selected")
        self.show()

    def truncate_path(self, path, max_length=20):
        """경로가 길 경우 일부만 표시하고 '...'으로 단축"""
        if len(path) > max_length:
            return "..." + path[-(max_length - 3) :]
        else:
            return path

    def accept(self):
        """저장 버튼 클릭 시 변경 사항을 저장하고 다이얼로그 닫기"""
        # 클릭 정보 업데이트
        self.click_info["click_type"] = self.click_type.currentText()
        self.click_info["window_class"] = self.window_class.text()
        self.click_info["window_text"] = self.window_text.text()
        self.click_info["window_title"] = self.window_title.text()
        self.click_info["depth"] = (
            int(self.depth.text()) if self.depth.text().isdigit() else 0
        )
        self.click_info["program"] = self.program.text()
        self.click_info["is_skip"] = self.is_skip.isChecked()
        self.click_info["skip_image_path"] = getattr(self, "skip_image_path", "")
        self.click_info["skip_image_target"] = self.skip_target_info
        self.click_info["is_wait"] = self.is_wait.isChecked()
        self.click_info["wait_image_path"] = getattr(self, "wait_image_path", "")
        self.click_info["wait_image_target"] = self.wait_target_info
        self.click_info["keyboard"] = self.keyboard.text()

        super().accept()


# 애플리케이션 실행
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()
    sys.exit(app.exec_())
