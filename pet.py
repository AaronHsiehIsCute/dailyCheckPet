import sys
import os
import random
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, 
                             QInputDialog, QMessageBox, QSystemTrayIcon, QMenu, QListWidget, QDialog,
                             QHBoxLayout, QTimeEdit, QGraphicsDropShadowEffect)
from PyQt6.QtCore import (QTimer, QDateTime, Qt, QRect, QTime, QPropertyAnimation, QEasingCurve, 
                          QPoint, QRectF)
from PyQt6.QtGui import (QPixmap, QPainter, QIcon, QColor, QPainterPath)
from collections import deque

class ScreenPet(QWidget):
    def __init__(self):
        super().__init__()
        self.pet_size = 66
        self.reminders = []
        self.dragging = False
        self.offset = None
        self.direction = 1
        self.y_counter = 0
        self.step_counter = 0

        self.load_images()
        self.initUI()
        self.load_reminders()

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.move_pet)
        self.move_timer.start(100)

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(60000)

        self.create_tray_icon()

        self.speech_bubble = SpeechBubble(self)
        self.speech_bubble.hide()

        self.start_button = QPushButton("开始任务", self)
        self.delay_button = QPushButton("延后", self)
        self.start_button.hide()
        self.delay_button.hide()

        self.start_button.clicked.connect(self.start_task)
        self.delay_button.clicked.connect(self.delay_task)

        debug_timer = QTimer(self)
        debug_timer.timeout.connect(lambda: print(f"当前时间: {QDateTime.currentDateTime()}"))
        debug_timer.start(60000)  # 每分钟触发一次
        self.animation_counter = 0
        self.animation_speed = 5  # 每5次移动才切换一次图片

        self.reminder_queue = deque()
        self.current_reminder_dialog = None

        self.move_timer.timeout.connect(self.update_reminder_position)

    def update_reminder_position(self):
        if self.current_reminder_dialog:
            self.current_reminder_dialog.update_position()

    def load_images(self):
        self.images = {
            'left': [self.load_and_scale('pet_go_left.png'), self.load_and_scale('pet_go_left2.png')],
            'right': [self.load_and_scale('pet_go_right.png'), self.load_and_scale('pet_go_right2.png')]
        }
        self.current_image = self.images['right'][0]

    def load_and_scale(self, image_path):
        original = QPixmap(image_path)
        return original.scaled(self.pet_size, self.pet_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def update_image(self):
        if self.direction == 1:  # 向右
            self.current_image = self.images['right'][self.step_counter % 2]
        else:  # 向左
            self.current_image = self.images['left'][self.step_counter % 2]
        self.label.setPixmap(self.current_image)

    def initUI(self):
        self.setGeometry(100, 100, self.pet_size, self.pet_size)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.label = QLabel(self)
        self.label.setPixmap(self.current_image)
        self.label.resize(self.pet_size, self.pet_size)

        self.show()

    def view_schedule(self):
        dialog = ScheduleDialog(self.reminders, self)
        dialog.exec()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()
        event.ignore()


    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.offset)
            self.update_reminder_position()
        event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
        event.ignore()


    def create_menu(self):
        menu = QMenu(self)
        add_reminder_action = menu.addAction("添加提醒")
        add_reminder_action.triggered.connect(self.add_reminder)
        view_schedule_action = menu.addAction("查看排程")
        view_schedule_action.triggered.connect(self.view_schedule)
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)
        return menu

    def contextMenuEvent(self, event):
        menu = self.create_menu()
        menu.exec(event.globalPos())

    def move_pet(self):
        if not self.dragging:
            screen = QApplication.primaryScreen().geometry()
            current_pos = self.pos()
            
            # X轴移动
            new_x = current_pos.x() + (random.randint(1, 3) * self.direction)
            
            # 随机改变方向
            if random.random() < 0.02:  # 2% 的概率改变方向
                self.direction *= -1
            
            # Y轴移动
            self.y_counter += 1
            if self.y_counter >= 20:  # 每20次X轴移动才进行一次Y轴移动
                new_y = current_pos.y() + random.randint(-2, 2)
                self.y_counter = 0
            else:
                new_y = current_pos.y()
            
            # 确保宠物不会移出屏幕
            new_x = max(0, min(new_x, screen.width() - self.width()))
            new_y = max(0, min(new_y, screen.height() - self.height()))
            
            self.move(new_x, new_y)

            # 更新图片
            self.animation_counter += 1
            if self.animation_counter >= self.animation_speed:
                self.step_counter += 1
                self.update_image()
                self.animation_counter = 0

            if hasattr(self, 'reminder_dialog') and self.reminder_dialog.isVisible():
                self.update_reminder_position()

    def check_reminders(self):
        now = QDateTime.currentDateTime()
        for reminder in self.reminders:
            if isinstance(reminder['next_time'], str):
                reminder['next_time'] = QDateTime.fromString(reminder['next_time'], Qt.DateFormat.ISODate)
            if reminder['next_time'] <= now:
                print(f"触发提醒: {reminder['task']}")  # 调试输出
                self.show_reminder(reminder)

    def update_pet_size(self):
        self.setGeometry(self.x(), self.y(), self.pet_size, self.pet_size)
        self.label.setGeometry(0, 0, self.pet_size, self.pet_size)

    def show_reminder(self, reminder):
        print(f"显示提醒: {reminder['task']}")  # 调试输出
        self.reminder_queue.append(reminder)
        if not self.current_reminder_dialog:
            self.show_next_reminder()

    def show_next_reminder(self):
        if self.reminder_queue:
            reminder = self.reminder_queue.popleft()
            self.current_reminder = reminder
            self.current_reminder_dialog = ReminderDialog(reminder, self)
            self.current_reminder_dialog.show()
            self.current_reminder_dialog.update_position()

    def start_task(self):
        if self.current_reminder['type'] == 'periodic':
            self.current_reminder['next_time'] = QDateTime.currentDateTime().addSecs(self.current_reminder['frequency'] * 60)
        else:  # daily
            self.current_reminder['next_time'] = self.calculate_next_daily_time(self.current_reminder['time'])
        self.save_reminders()
        if hasattr(self, 'reminder_dialog'):
            self.reminder_dialog.close()
        self.close_current_reminder()

    def delay_task(self):
        self.current_reminder['next_time'] = QDateTime.currentDateTime().addSecs(self.current_reminder['delay'] * 60)
        self.save_reminders()
        if hasattr(self, 'reminder_dialog'):
            self.reminder_dialog.close()
        self.close_current_reminder()

    def close_current_reminder(self):
        if self.current_reminder_dialog:
            self.current_reminder_dialog.close()
            self.current_reminder_dialog = None
        self.show_next_reminder()

    def close_all_reminders(self):
        self.reminder_queue.clear()
        self.close_current_reminder()

    def hide_reminder(self):
        self.speech_bubble.hide()
        self.start_button.hide()
        self.delay_button.hide()
        self.setGeometry(self.x(), self.y(), self.pet_size, self.pet_size)  # 重置大小


    def add_reminder(self):
        items = ("定期", "每天排程")
        item, ok = QInputDialog.getItem(self, "选择提醒类型", "提醒类型:", items, 0, False)
        
        if ok and item:
            if item == "定期":
                self.add_periodic_reminder()
            else:
                self.add_daily_reminder()
            self.save_reminders()  # 确保保存新添加的提醒

    def add_periodic_reminder(self):
        task, ok1 = QInputDialog.getText(self, "添加提醒", "提醒事项:")
        if ok1 and task:
            frequency, ok2 = QInputDialog.getInt(self, "添加提醒", "提醒频率(分钟):", 60, 1, 1440)
            if ok2:
                delay, ok3 = QInputDialog.getInt(self, "添加提醒", "延后时间(分钟):", 5, 1, 60)
                if ok3:
                    reminder = {
                        'type': 'periodic',
                        'task': task,
                        'frequency': frequency,
                        'delay': delay,
                        'next_time': QDateTime.currentDateTime().addSecs(frequency * 60)
                    }
                    self.reminders.append(reminder)
                    print(f"添加了定期提醒: {task}, 下次提醒时间: {reminder['next_time']}")  # 添加这行来调试
                    QMessageBox.information(self, "提醒添加成功", f"已添加定期提醒: {task}")

    def add_daily_reminder(self):
        task, ok1 = QInputDialog.getText(self, "添加提醒", "提醒事项:")
        if ok1 and task:
            time_dialog = TimeSelectDialog(self)
            if time_dialog.exec() == QDialog.DialogCode.Accepted:
                time = time_dialog.get_time()
                delay, ok3 = QInputDialog.getInt(self, "添加提醒", "延后时间(分钟):", 5, 1, 60)
                if ok3:
                    reminder = {
                        'type': 'daily',
                        'task': task,
                        'time': time,
                        'delay': delay,
                        'next_time': self.calculate_next_daily_time(time)
                    }
                    self.reminders.append(reminder)
                    print(f"添加了每日提醒: {task}, 下次提醒时间: {reminder['next_time']}")  # 添加这行来调试
                    QMessageBox.information(self, "提醒添加成功", f"已添加每日提醒: {task}")

    def save_reminders(self):
        reminders_data = []
        for reminder in self.reminders:
            reminder_copy = reminder.copy()
            reminder_copy['next_time'] = reminder_copy['next_time'].toString(Qt.DateFormat.ISODate)
            reminders_data.append(reminder_copy)
        
        with open('reminders.json', 'w') as f:
            json.dump(reminders_data, f)

    def calculate_next_daily_time(self, time_str):
        current_date = QDateTime.currentDateTime().date()
        time = QTime.fromString(time_str, "HH:mm")
        next_time = QDateTime(current_date, time)
        if next_time <= QDateTime.currentDateTime():
            next_time = next_time.addDays(1)
        return next_time

    def load_reminders(self):
        try:
            with open('reminders.json', 'r') as f:
                reminders_data = json.load(f)
            
            for reminder_data in reminders_data:
                reminder_data['next_time'] = QDateTime.fromString(reminder_data['next_time'], Qt.DateFormat.ISODate)
                self.reminders.append(reminder_data)
            print(f"加载了 {len(self.reminders)} 个提醒")  # 添加这行来调试
        except FileNotFoundError:
            print("没有找到保存的提醒文件")  # 添加这行来调试
            pass  # 如果文件不存在,就不加载任何提醒

    def closeEvent(self, event):
        self.save_reminders()
        event.accept()
        event.ignore()

    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        icon = QIcon(self.images['right'][0])  # 使用右侧图像作为托盘图标
        self.tray_icon.setIcon(icon)
        
        self.tray_icon.setContextMenu(self.create_menu())
        self.tray_icon.show()

class ReminderWidget(QWidget):
    def __init__(self, reminder, parent=None):
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.reminder = reminder
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, self.pet_size, self.pet_size)
        layout = QVBoxLayout(self)
        
        task_label = QLabel(f"提醒: {self.reminder['task']}")
        layout.addWidget(task_label)

        button_layout = QHBoxLayout()
        start_button = QPushButton("开始任务")
        start_button.clicked.connect(self.start_task)
        delay_button = QPushButton("延后")
        delay_button.clicked.connect(self.delay_task)

        button_layout.addWidget(start_button)
        button_layout.addWidget(delay_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.adjustSize()

        # 将提醒窗口放在屏幕中央
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.center() - self.rect().center())

        self.show()

class SpeechBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        
        self.setStyleSheet("""
            background-color: rgba(255, 255, 255, 180);
            border-radius: 10px;
            padding: 5px;
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
    
    def setFixedSize(self, width, height):
        super().setFixedSize(width, height)
        self.label.setWordWrap(True)  # 允许文本换行
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 文本居中

    def setText(self, text):
        self.label.setText(text)
        self.label.setWordWrap(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        
        painter.fillPath(path, QColor(255, 255, 255, 180))
        painter.drawPath(path)

class ScheduleDialog(QDialog):
    def __init__(self, reminders, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.reminders = reminders
        self.setWindowTitle("当前排程")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.update_list()
        layout.addWidget(self.list_widget)

        delete_button = QPushButton("删除选中项")
        delete_button.clicked.connect(self.delete_selected)
        layout.addWidget(delete_button)

        self.setLayout(layout)

    def update_list(self):
        self.list_widget.clear()
        for i, reminder in enumerate(self.reminders):
            if reminder['type'] == 'periodic':
                item_text = f"{reminder['task']} - 每 {reminder['frequency']} 分钟"
            else:  # daily
                item_text = f"{reminder['task']} - 每天 {reminder['time']}"
            self.list_widget.addItem(item_text)

    def delete_selected(self):
        selected_items = self.list_widget.selectedItems()
        for item in selected_items:
            index = self.list_widget.row(item)
            del self.reminders[index]
        self.update_list()
        self.parent.save_reminders()  # 保存更改

class TimeSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择时间")
        layout = QVBoxLayout()
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        
        layout.addWidget(QLabel("请选择提醒时间："))
        layout.addWidget(self.time_edit)
        
        confirm_button = QPushButton("确认")
        confirm_button.clicked.connect(self.accept)
        layout.addWidget(confirm_button)
        
        self.setLayout(layout)

    def get_time(self):
        return self.time_edit.time().toString("HH:mm")
    
class ReminderDialog(QDialog):
    def __init__(self, reminder, parent=None):
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.reminder = reminder
        self.parent = parent
        self.initUI()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

    def initUI(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        
        background = QWidget(self)
        background.setStyleSheet("""
            background-color: rgba(255, 255, 255, 220);
            border-radius: 10px;
            padding: 10px;
        """)
        background_layout = QVBoxLayout(background)

        task_label = QLabel(f"提醒: {self.reminder['task']}")
        task_label.setWordWrap(True)
        background_layout.addWidget(task_label)

        button_layout = QHBoxLayout()
        start_button = QPushButton("开始任务")
        start_button.clicked.connect(self.start_task)
        delay_button = QPushButton("延后")
        delay_button.clicked.connect(self.delay_task)
        close_all_button = QPushButton("全部关闭")
        close_all_button.clicked.connect(self.close_all)

        button_layout.addWidget(start_button)
        button_layout.addWidget(delay_button)
        button_layout.addWidget(close_all_button)
        background_layout.addLayout(button_layout)

        layout.addWidget(background)
        self.setLayout(layout)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        background.setGraphicsEffect(shadow)

        self.adjustSize()

    def start_task(self):
        self.parent.start_task()

    def delay_task(self):
        self.parent.delay_task()

    def close_all(self):
        self.parent.close_all_reminders()

    def update_position(self):
        if self.parent:
            pet_pos = self.parent.pos()
            pet_size = self.parent.size()
            dialog_size = self.size()
            
            # 计算X轴位置，使提醒框与猫咪中心对齐
            x = pet_pos.x() + (pet_size.width() - dialog_size.width()) // 2
            y = pet_pos.y() - dialog_size.height()
            
            self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ScreenPet()
    sys.exit(app.exec())