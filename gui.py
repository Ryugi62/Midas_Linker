import sys
import os
import shutil
import win32gui
import win32process
import win32con
import psutil
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
)
from PyQt5.QtCore import Qt, pyqtSignal
from pynput import mouse  # 마우스 이벤트 감지를 위한 라이브러리

class CustomWindow(QMainWindow):
    click_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # 윈도우 설정
        self.setWindowTitle("Minimal White & Black UI")
        self.setGeometry(100, 100, 800, 600)  # 윈도우 크기 조정
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #FFFFFF;  /* 전체 배경을 화이트로 */
                border-radius: 10px;
            }
            QLabel {
                border-radius: 5px;
                background-color: #F5F5F5;  /* 라벨 배경은 아주 연한 그레이 */
                padding: 15px;
                border: 1px solid #000000;  /* 검은색 테두리 */
                font-size: 16px;
                color: #000000;  /* 글자 색은 블랙 */
            }
            QListWidget {
                border-radius: 5px;
                border: 1px solid #000000;  /* 검은색 테두리 */
                background-color: #FFFFFF;  /* 리스트 위젯은 화이트 */
                padding: 10px;
                color: #000000;  /* 리스트 아이템 글자는 블랙 */
                font-size: 14px;
            }
            QPushButton {
                background-color: #FFFFFF;  /* 버튼은 화이트 */
                border-radius: 5px;
                padding: 10px;
                border: 2px solid #000000;  /* 검은 테두리 */
                font-size: 14px;
                color: #000000;  /* 글자는 블랙 */
            }
            QPushButton:hover {
                background-color: #F0F0F0;  /* 호버 시 밝은 회색 */
            }
            """
        )

        # 메인 레이아웃
        main_layout = QVBoxLayout()

        # 이미지 라벨 설정
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(800, 400)  # 기본 사이즈 지정
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: #F5F5F5; color: #000000;"  # 이미지 없을 때 배경 및 글자 색상
        )
        self.image_label.setText("No Image Available")  # 기본 텍스트 추가
        main_layout.addWidget(self.image_label)

        # 리스트 위젯 설정
        self.list_widget = QListWidget(self)
        self.list_widget.setFixedSize(800, 100)  # 리스트 크기 지정
        main_layout.addWidget(self.list_widget)

        # 버튼 레이아웃
        button_layout_top = QHBoxLayout()
        button_layout_bottom = QVBoxLayout()

        # 상단 화살표 버튼
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
        self.is_recording = False  # 녹화 상태 여부
        self.is_executing = False  # 실행 상태 여부

        # 녹화 버튼
        self.record_button = QPushButton("녹화", self)
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout_bottom.addWidget(self.record_button)

        # 저장 버튼
        save_button = QPushButton("저장", self)
        button_layout_bottom.addWidget(save_button)

        # 불러오기 버튼
        load_button = QPushButton("불러오기", self)
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

        # 자신의 윈도우 핸들(hWnd) 저장
        self.hwnd = int(self.winId())
        self.excluded_hwnds = [self.hwnd]  # 제외할 hWnd 목록

        # 클릭 데이터 저장 리스트
        self.click_data_list = []

        # 클릭 신호 연결
        self.click_signal.connect(self.handle_click_signal)

    def toggle_recording(self):
        """녹화 상태를 토글하고 UI 업데이트"""
        if self.is_recording:
            # 녹화 중지
            self.record_button.setText("녹화")
            self.record_button.setStyleSheet(
                "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
            )
            if hasattr(self, 'mouse_listener'):
                self.mouse_listener.stop()  # 마우스 리스너 중지
        else:
            # 녹화 시작
            if self.is_executing:
                self.toggle_execution()  # 실행 중지

            self.record_button.setText("중지")
            self.record_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
            self.start_listening_for_clicks()
        self.is_recording = not self.is_recording

    def start_listening_for_clicks(self):
        """마우스 클릭 이벤트 리스너 시작"""
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()

    def on_click(self, x, y, button, pressed):
        """마우스 클릭 이벤트 처리"""
        if self.is_recording and pressed:
            hwnd = win32gui.WindowFromPoint((x, y))
            # 자신의 GUI나 설정 다이얼로그를 클릭한 경우 처리하지 않음
            if hwnd in self.excluded_hwnds:
                return
            self.record_click(hwnd, button, x, y)

    def record_click(self, hwnd, button, x, y):
        """클릭 정보 기록 및 리스트에 추가"""
        # 상대 좌표 계산
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        relative_x = x - left
        relative_y = y - top

        click_type = "Left Click" if button == mouse.Button.left else "Right Click"
        window_class = win32gui.GetClassName(hwnd)
        window_text = win32gui.GetWindowText(hwnd)
        program = self.get_program_name_from_hwnd(hwnd)
        window_name = win32gui.GetWindowText(win32gui.GetAncestor(hwnd, win32con.GA_ROOT))
        depth = self.get_window_depth(hwnd)
        window_title = window_text  # window_title 추가

        # 클릭 정보 딕셔너리 생성
        click_info = {
            "x": relative_x,
            "y": relative_y,
            "click_type": click_type,
            "window_class": window_class,
            "window_text": window_text,
            "window_title": window_title,
            "창이름": window_name,
            "depth": depth,
            "program": program,
        }

        # 클릭 신호 발행 (GUI 업데이트는 메인 스레드에서)
        self.click_signal.emit(click_info)

    def handle_click_signal(self, click_info):
        """메인 스레드에서 클릭 정보를 처리"""
        self.click_data_list.append(click_info)
        summary = self.create_summary(click_info)
        self.list_widget.addItem(summary)

    def create_summary(self, click_info):
        """클릭 정보를 기반으로 리스트 항목 요약 생성"""
        summary = f"({click_info['x']}, {click_info['y']}) {click_info['window_title']} {click_info['program']}"
        # 길이가 길 경우 '...'으로 표시
        max_length = 80
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + '...'
        return summary

    def get_program_name_from_hwnd(self, hwnd):
        """hwnd를 통해 프로그램 이름 가져오기"""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = psutil.Process(pid)
            return process.name()
        except psutil.NoSuchProcess:
            return "Unknown"

    def get_window_depth(self, hwnd):
        """창의 깊이 계산"""
        depth = 0
        while hwnd:
            hwnd = win32gui.GetParent(hwnd)
            depth += 1
        return depth

    def move_item_up(self):
        """선택된 항목을 위로 이동"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            # 클릭 데이터 리스트에서도 위치 변경
            self.click_data_list.insert(current_row - 1, self.click_data_list.pop(current_row))
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentRow(current_row - 1)

    def move_item_down(self):
        """선택된 항목을 아래로 이동"""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            # 클릭 데이터 리스트에서도 위치 변경
            self.click_data_list.insert(current_row + 1, self.click_data_list.pop(current_row))
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentRow(current_row + 1)

    def duplicate_item(self):
        """선택된 항목 복제"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            # 클릭 데이터 리스트에서도 복제
            self.click_data_list.insert(current_row + 1, self.click_data_list[current_row].copy())
            item_text = self.list_widget.item(current_row).text()
            self.list_widget.insertItem(current_row + 1, item_text)

    def delete_item(self):
        """선택된 항목 삭제"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            # 클릭 데이터 리스트에서도 삭제
            del self.click_data_list[current_row]
            self.list_widget.takeItem(current_row)

    def open_settings(self):
        """설정 다이얼로그 열기"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            # 클릭 데이터 가져오기
            click_info = self.click_data_list[current_row]
            dialog = SettingsDialog(click_info)
            dialog_hwnd = int(dialog.winId())  # 다이얼로그의 hWnd 가져오기
            self.excluded_hwnds.append(dialog_hwnd)  # 제외할 hWnd 목록에 추가
            if dialog.exec_() == QDialog.Accepted:
                # 다이얼로그에서 변경된 click_info가 이미 업데이트 되었음
                # 리스트 항목 업데이트
                summary = self.create_summary(click_info)
                self.list_widget.item(current_row).setText(summary)
            # 다이얼로그 종료 후 hWnd 목록에서 제거
            self.excluded_hwnds.remove(dialog_hwnd)

    def toggle_execution(self):
        """실행 상태를 토글하고 UI 업데이트"""
        if self.is_executing:
            # 실행 중지
            self.execute_button.setText("실행")
            self.execute_button.setStyleSheet(
                "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
            )
            # 실행 중지 로직 추가 가능
        else:
            # 실행 시작
            if self.is_recording:
                self.toggle_recording()  # 녹화 중지

            self.execute_button.setText("중지")
            self.execute_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
            # 실행 로직 추가 가능
        self.is_executing = not self.is_executing

class SettingsDialog(QDialog):
    def __init__(self, click_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setGeometry(300, 300, 400, 300)

        self.click_info = click_info  # 클릭 정보 저장

        # 폼 레이아웃 설정
        form_layout = QFormLayout()

        # 설정 필드들 초기화
        self.click_type = QComboBox(self)
        self.click_type.addItems(["Click", "Double Click", "Right Click"])
        self.click_type.setCurrentText(click_info.get('click_type', 'Click'))

        self.window_class = QLineEdit(self)
        self.window_class.setText(click_info.get('window_class', ''))

        self.window_text = QLineEdit(self)
        self.window_text.setText(click_info.get('window_text', ''))

        self.window_name = QLineEdit(self)
        self.window_name.setText(click_info.get('창이름', ''))

        self.depth = QLineEdit(self)
        self.depth.setText(str(click_info.get('depth', 0)))

        self.program = QLineEdit(self)
        self.program.setText(click_info.get('program', ''))

        self.is_skip = QCheckBox(self)
        self.is_skip.setChecked(click_info.get('is_skip', False))
        self.is_skip.stateChanged.connect(self.update_skip_image_button)

        self.skip_image = QPushButton("이미지 선택", self)
        self.skip_image.clicked.connect(self.select_skip_image)
        self.skip_image_path = click_info.get('skip_image_path', '')
        if self.skip_image_path:
            display_text = self.truncate_path(self.skip_image_path)
            self.skip_image.setText(display_text)
        self.update_skip_image_button(self.is_skip.checkState())

        self.is_wait = QCheckBox(self)
        self.is_wait.setChecked(click_info.get('is_wait', False))
        self.is_wait.stateChanged.connect(self.update_wait_image_button)

        self.wait_image = QPushButton("이미지 선택", self)
        self.wait_image.clicked.connect(self.select_wait_image)
        self.wait_image_path = click_info.get('wait_image_path', '')
        if self.wait_image_path:
            display_text = self.truncate_path(self.wait_image_path)
            self.wait_image.setText(display_text)
        self.update_wait_image_button(self.is_wait.checkState())

        self.keyboard = QLineEdit(self)
        self.keyboard.setText(click_info.get('keyboard', ''))

        # 폼 레이아웃에 위젯 추가
        form_layout.addRow("Click Type:", self.click_type)
        form_layout.addRow("Window Class:", self.window_class)
        form_layout.addRow("Window Text:", self.window_text)
        form_layout.addRow("창이름:", self.window_name)
        form_layout.addRow("Depth:", self.depth)
        form_layout.addRow("Program:", self.program)
        form_layout.addRow("Skip:", self.is_skip)
        form_layout.addRow("Skip Image:", self.skip_image)
        form_layout.addRow("Wait:", self.is_wait)
        form_layout.addRow("Wait Image:", self.wait_image)
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

    def update_skip_image_button(self, state):
        """is_skip 체크박스의 상태에 따라 skip_image 버튼 활성화/비활성화"""
        self.skip_image.setEnabled(state == Qt.Checked)

    def update_wait_image_button(self, state):
        """is_wait 체크박스의 상태에 따라 wait_image 버튼 활성화/비활성화"""
        self.wait_image.setEnabled(state == Qt.Checked)

    def select_skip_image(self):
        """Skip 이미지 선택 및 처리"""
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, '파일 선택', '', 'Images (*.png *.xpm *.jpg)')
        if file_path:
            # 복사할 폴더 확인 및 생성
            skip_images_dir = './.skip_images'
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
        file_path, _ = file_dialog.getOpenFileName(self, '파일 선택', '', 'Images (*.png *.xpm *.jpg)')
        if file_path:
            # 복사할 폴더 확인 및 생성
            wait_images_dir = './.wait_images'
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

    def truncate_path(self, path, max_length=20):
        """경로가 길 경우 일부만 표시하고 '...'으로 단축"""
        if len(path) > max_length:
            return '...' + path[-(max_length - 3):]
        else:
            return path

    def accept(self):
        """저장 버튼 클릭 시 변경 사항을 저장하고 다이얼로그 닫기"""
        # 클릭 정보 업데이트
        self.click_info['click_type'] = self.click_type.currentText()
        self.click_info['window_class'] = self.window_class.text()
        self.click_info['window_text'] = self.window_text.text()
        self.click_info['창이름'] = self.window_name.text()
        self.click_info['depth'] = int(self.depth.text()) if self.depth.text().isdigit() else 0
        self.click_info['program'] = self.program.text()
        self.click_info['is_skip'] = self.is_skip.isChecked()
        self.click_info['skip_image_path'] = self.skip_image_path
        self.click_info['is_wait'] = self.is_wait.isChecked()
        self.click_info['wait_image_path'] = self.wait_image_path
        self.click_info['keyboard'] = self.keyboard.text()

        super().accept()

# 애플리케이션 실행
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()
    sys.exit(app.exec_())
