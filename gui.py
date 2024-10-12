import sys
import os
import shutil
import threading  # For threading
import time  # For delays
import win32gui
import win32process
import win32con
import win32api  # For sending messages
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
from pynput import mouse  # For mouse event detection

class CustomWindow(QMainWindow):
    click_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # Window settings
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

        # Main layout
        main_layout = QVBoxLayout()

        # Image label
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(800, 400)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: #F5F5F5; color: #000000;"
        )
        self.image_label.setText("No Image Available")
        main_layout.addWidget(self.image_label)

        # List widget
        self.list_widget = QListWidget(self)
        self.list_widget.setFixedSize(800, 100)
        main_layout.addWidget(self.list_widget)

        # Button layouts
        button_layout_top = QHBoxLayout()
        button_layout_bottom = QVBoxLayout()

        # Up and down buttons
        up_button = QPushButton("▲", self)
        down_button = QPushButton("▼", self)
        up_button.clicked.connect(self.move_item_up)
        down_button.clicked.connect(self.move_item_down)
        button_layout_top.addWidget(up_button)
        button_layout_top.addWidget(down_button)

        # Copy, delete, settings buttons
        copy_button = QPushButton("복제", self)
        delete_button = QPushButton("삭제", self)
        settings_button = QPushButton("설정", self)
        copy_button.clicked.connect(self.duplicate_item)
        delete_button.clicked.connect(self.delete_item)
        settings_button.clicked.connect(self.open_settings)
        button_layout_top.addWidget(copy_button)
        button_layout_top.addWidget(delete_button)
        button_layout_top.addWidget(settings_button)

        # Recording and execution state variables
        self.is_recording = False
        self.is_executing = False

        # Record button
        self.record_button = QPushButton("녹화", self)
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout_bottom.addWidget(self.record_button)

        # Save button
        save_button = QPushButton("저장", self)
        button_layout_bottom.addWidget(save_button)

        # Load button
        load_button = QPushButton("불러오기", self)
        button_layout_bottom.addWidget(load_button)

        # Execute button
        self.execute_button = QPushButton("실행", self)
        self.execute_button.clicked.connect(self.toggle_execution)
        button_layout_bottom.addWidget(self.execute_button)

        main_layout.addLayout(button_layout_top)
        main_layout.addLayout(button_layout_bottom)

        # Main widget
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Excluded hwnds
        self.hwnd = int(self.winId())
        self.excluded_hwnds = [self.hwnd]

        # Click data list
        self.click_data_list = []

        # Connect click signal
        self.click_signal.connect(self.handle_click_signal)

    def toggle_recording(self):
        """Toggle recording state and update UI"""
        if self.is_recording:
            # Stop recording
            self.record_button.setText("녹화")
            self.record_button.setStyleSheet(
                "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
            )
            if hasattr(self, 'mouse_listener'):
                self.mouse_listener.stop()
        else:
            # Start recording
            if self.is_executing:
                self.toggle_execution()
            self.record_button.setText("중지")
            self.record_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
            self.start_listening_for_clicks()
        self.is_recording = not self.is_recording

    def start_listening_for_clicks(self):
        """Start mouse click event listener"""
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()

    def on_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        if self.is_recording and pressed:
            hwnd = win32gui.WindowFromPoint((x, y))
            # Ignore clicks on own GUI or settings dialog
            if hwnd in self.excluded_hwnds:
                return
            self.record_click(hwnd, button, x, y)

    def record_click(self, hwnd, button, x, y):
        """Record click information and add to list"""
        # Relative coordinates
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        relative_x = x - left
        relative_y = y - top

        click_type = "Click" if button == mouse.Button.left else "Right Click"  # Standardize click type
        window_class = win32gui.GetClassName(hwnd)
        window_text = win32gui.GetWindowText(hwnd)
        program = self.get_program_name_from_hwnd(hwnd)
        window_title = win32gui.GetWindowText(win32gui.GetAncestor(hwnd, win32con.GA_ROOT))
        depth = self.get_window_depth(hwnd)
        window_title = window_text  # Added window_title

        click_info = {
            "x": relative_x,
            "y": relative_y,
            "click_type": click_type,
            "window_class": window_class,
            "window_text": window_text,
            "window_title": window_title,
            "창이름": window_title,
            "depth": depth,
            "program": program,
        }

        # Emit click signal (GUI updates in main thread)
        self.click_signal.emit(click_info)

    def handle_click_signal(self, click_info):
        """Process click information in main thread"""
        self.click_data_list.append(click_info)
        summary = self.create_summary(click_info)
        self.list_widget.addItem(summary)

    def create_summary(self, click_info):
        """Create summary for list item"""
        summary = f"({click_info['x']}, {click_info['y']}) {click_info['window_title']} {click_info['program']}"
        max_length = 80
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + '...'
        return summary

    def get_program_name_from_hwnd(self, hwnd):
        """Get program name from hwnd"""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = psutil.Process(pid)
            return process.name()
        except psutil.NoSuchProcess:
            return "Unknown"

    def get_window_depth(self, hwnd):
        """Calculate window depth"""
        depth = 0
        while hwnd:
            hwnd = win32gui.GetParent(hwnd)
            depth += 1
        return depth

    def move_item_up(self):
        """Move selected item up"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            self.click_data_list.insert(current_row - 1, self.click_data_list.pop(current_row))
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentRow(current_row - 1)

    def move_item_down(self):
        """Move selected item down"""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            self.click_data_list.insert(current_row + 1, self.click_data_list.pop(current_row))
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentRow(current_row + 1)

    def duplicate_item(self):
        """Duplicate selected item"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            self.click_data_list.insert(current_row + 1, self.click_data_list[current_row].copy())
            item_text = self.list_widget.item(current_row).text()
            self.list_widget.insertItem(current_row + 1, item_text)

    def delete_item(self):
        """Delete selected item"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            del self.click_data_list[current_row]
            self.list_widget.takeItem(current_row)

    def open_settings(self):
        """Open settings dialog"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            click_info = self.click_data_list[current_row]
            dialog = SettingsDialog(click_info)
            dialog_hwnd = int(dialog.winId())
            self.excluded_hwnds.append(dialog_hwnd)
            if dialog.exec_() == QDialog.Accepted:
                summary = self.create_summary(click_info)
                self.list_widget.item(current_row).setText(summary)
            self.excluded_hwnds.remove(dialog_hwnd)

    def toggle_execution(self):
        """Toggle execution state and update UI"""
        if self.is_executing:
            # Stop execution
            self.execute_button.setText("실행")
            self.execute_button.setStyleSheet(
                "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
            )
            self.is_executing = False
        else:
            # Start execution
            if self.is_recording:
                self.toggle_recording()
            self.execute_button.setText("중지")
            self.execute_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
            self.is_executing = True
            # Start execution thread
            self.execution_thread = threading.Thread(target=self.execute_clicks)
            self.execution_thread.start()

    def execute_clicks(self):
        """Execute recorded clicks"""
        for click_info in self.click_data_list:
            if not self.is_executing:
                break
            hwnd = self.find_matching_hwnd(click_info)
            if hwnd:
                self.send_click(hwnd, click_info)
            else:
                print(f"Could not find hwnd for click_info: {click_info}")
            time.sleep(0.1)  # Small delay between actions

    def find_matching_hwnd(self, click_info):
        """Find hwnd matching the recorded information"""
        all_hwnds = self.get_all_hwnds()
        for hwnd in all_hwnds:
            if not win32gui.IsWindowEnabled(hwnd) or not win32gui.IsWindowVisible(hwnd):
                continue
            window_class = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            window_title = win32gui.GetWindowText(win32gui.GetAncestor(hwnd, win32con.GA_ROOT))
            depth = self.get_window_depth(hwnd)
            program = self.get_program_name_from_hwnd(hwnd)
            if (window_class == click_info['window_class'] and
                window_text == click_info['window_text'] and
                window_title == click_info['window_title'] and
                depth == click_info['depth'] and
                program == click_info['program']):
                return hwnd
        return None

    def send_click(self, hwnd, click_info):
        """Send click message to hwnd at specified coordinates"""
        x = click_info['x']
        y = click_info['y']
        click_type = click_info['click_type']
        lParam = win32api.MAKELONG(x, y)
        if click_type == 'Click':
            # Send WM_LBUTTONDOWN and WM_LBUTTONUP
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, None, lParam)
        elif click_type == 'Right Click':
            # Send WM_RBUTTONDOWN and WM_RBUTTONUP
            win32api.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam)
            win32api.PostMessage(hwnd, win32con.WM_RBUTTONUP, None, lParam)
        elif click_type == 'Double Click':
            # Send WM_LBUTTONDBLCLK and WM_LBUTTONUP
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lParam)
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, None, lParam)

    def get_all_hwnds(self):
        """Get all hwnds in the current session"""
        hwnds = []
        win32gui.EnumWindows(self.enum_windows_callback, hwnds)
        all_hwnds = []
        for hwnd in hwnds:
            all_hwnds.append(hwnd)
            all_hwnds.extend(self.get_all_descendants(hwnd))
        return all_hwnds

    def enum_windows_callback(self, hwnd, hwnds):
        hwnds.append(hwnd)

    def get_all_descendants(self, hwnd):
        """Recursively get all child hwnds"""
        hwnd_list = []
        child_hwnds = []
        def callback(child_hwnd, _):
            child_hwnds.append(child_hwnd)
        win32gui.EnumChildWindows(hwnd, callback, None)
        for child_hwnd in child_hwnds:
            hwnd_list.append(child_hwnd)
            hwnd_list.extend(self.get_all_descendants(child_hwnd))
        return hwnd_list

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
