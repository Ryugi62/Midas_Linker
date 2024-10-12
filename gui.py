import sys
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
from PyQt5.QtCore import Qt, QTimer


class CustomWindow(QMainWindow):
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
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #F0F0F0;  /* 호버 시 밝은 회색 */
            }
            """
        )

        # 메인 레이아웃
        main_layout = QVBoxLayout()

        # 이미지 라벨 (기본 크기 유지, 이미지가 들어오면 그 크기에 맞춰서 확대/축소)
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(800, 400)  # 기본 사이즈 지정
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: #F5F5F5; color: #000000;"  # 이미지 없을 때 밝은 회색 배경과 블랙 글씨
        )
        self.image_label.setText("No Image Available")  # 기본 텍스트 추가
        main_layout.addWidget(self.image_label)

        # 리스트 박스 (사이즈를 일정하게 유지)
        self.list_widget = QListWidget(self)
        for i in range(15):
            self.list_widget.addItem(f"x, y, window_class, window_text, 창이름")
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

        # 녹화 및 실행 버튼을 위한 토글 기능 추가
        self.is_recording = False  # 녹화 상태 여부
        self.is_executing = False  # 실행 상태 여부

        # 녹화 버튼
        self.record_button = QPushButton("녹화", self)
        self.record_button.clicked.connect(self.toggle_recording)  # 클릭 시 녹화 상태 변경
        button_layout_bottom.addWidget(self.record_button)

        # 저장 버튼
        save_button = QPushButton("저장", self)
        button_layout_bottom.addWidget(save_button)

        # 불러오기 버튼
        load_button = QPushButton("불러오기", self)
        button_layout_bottom.addWidget(load_button)

        # 실행 버튼
        self.execute_button = QPushButton("실행", self)
        self.execute_button.clicked.connect(self.toggle_execution)  # 클릭 시 실행 상태 변경
        button_layout_bottom.addWidget(self.execute_button)

        main_layout.addLayout(button_layout_top)
        main_layout.addLayout(button_layout_bottom)

        # 메인 위젯 설정
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def move_item_up(self):
        """선택된 항목을 위로 이동"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentRow(current_row - 1)

    def move_item_down(self):
        """선택된 항목을 아래로 이동"""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentRow(current_row + 1)

    def duplicate_item(self):
        """선택된 항목을 복제"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            item_text = self.list_widget.item(current_row).text()
            self.list_widget.insertItem(current_row + 1, item_text)

    def delete_item(self):
        """선택된 항목 삭제"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            self.list_widget.takeItem(current_row)

    def open_settings(self):
        """설정 창을 열기"""
        current_row = self.list_widget.currentRow()
        if current_row != -1:
            item_text = self.list_widget.item(current_row).text()
            dialog = SettingsDialog(item_text)
            dialog.exec_()

    def toggle_recording(self):
        """녹화 버튼을 클릭하면 녹화 상태를 토글"""
        if self.is_recording:
            self.record_button.setText("녹화")
            self.record_button.setStyleSheet(
                "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
            )
        else:
            if self.is_executing:
                self.toggle_execution()  # 실행 중지

            self.record_button.setText("중지")
            self.record_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
        self.is_recording = not self.is_recording

    def toggle_execution(self):
        """실행 버튼을 클릭하면 실행 상태를 토글"""
        if self.is_executing:
            self.execute_button.setText("실행")
            self.execute_button.setStyleSheet(
                "background-color: #FFFFFF; color: #000000; border: 2px solid #000000;"
            )
        else:
            if self.is_recording:
                self.toggle_recording()  # 녹화 중지

            self.execute_button.setText("중지")
            self.execute_button.setStyleSheet(
                "background-color: #000000; color: #FFFFFF; border: 2px solid #000000;"
            )
        self.is_executing = not self.is_executing


    def animate_button(self, button):
        """버튼 클릭 시 애니메이션 적용, 중지 상태가 아닐 때만 애니메이션"""
        if button.text() not in ["중지"]:
            original_style = button.styleSheet()
            button.setStyleSheet("background-color: #FF5733; color: #FFFFFF;")
            QTimer.singleShot(200, lambda: button.setStyleSheet(original_style))


class SettingsDialog(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setGeometry(300, 300, 400, 300)

        # 폼 레이아웃 설정
        form_layout = QFormLayout()

        # 설정 창의 필드들
        self.click_type = QComboBox(self)
        self.click_type.addItems(["Click", "Double Click", "Right Click"])

        self.window_class = QLineEdit(self)
        self.window_text = QLineEdit(self)
        self.window_name = QLineEdit(self)
        self.depth = QLineEdit(self)
        self.program = QLineEdit(self)
        self.is_skip = QCheckBox(self)
        self.skip_image = QPushButton("이미지 선택", self)
        self.skip_image.clicked.connect(self.select_image)
        self.is_wait = QCheckBox(self)
        self.wait_image = QPushButton("이미지 선택", self)
        self.wait_image.clicked.connect(self.select_image)
        self.keyboard = QLineEdit(self)

        # 필드 추가
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

        # 저장 및 취소 버튼
        self.save_button = QPushButton("저장", self)
        self.cancel_button = QPushButton("취소", self)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # 버튼 배치
        form_layout.addWidget(self.save_button)
        form_layout.addWidget(self.cancel_button)

        self.setLayout(form_layout)

        # 설정창 디자인 적용
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

    def select_image(self):
        """파일 선택 다이얼로그 열기"""
        file_dialog = QFileDialog(self)
        file_dialog.getOpenFileName(self, '파일 선택', '', 'Images (*.png *.xpm *.jpg)')


# 앱 실행
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()

    sys.exit(app.exec_())
