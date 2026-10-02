import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QSpinBox,
    QPushButton, QVBoxLayout, QHBoxLayout,
)


class TaskCard(QWidget):
    """点击鱼干打开的临时任务卡；点击外部或按 Esc 收起。"""

    def __init__(self, kitty):
        super().__init__(kitty, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.kitty = kitty
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 265)
        self.setStyleSheet('''
            QLabel { color: #393630; background: transparent; font-size: 14px; }
            QLabel#heading { font-size: 19px; font-weight: 600; }
            QLineEdit, QSpinBox {
                background: #FFFEFA; color: #393630;
                border: 1px solid #B4AEA3; border-radius: 8px;
                padding: 7px; font-size: 15px;
                selection-background-color: #DAD5C9;
                selection-color: #393630;
            }
            QPushButton {
                color: #393630; background: #EEEADF;
                border: 1px solid #777167; border-radius: 10px;
                padding: 8px 14px; font-size: 14px;
            }
            QPushButton:hover { background: #E2DDCF; }
            QPushButton:pressed { background: #D5CEBD; }
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)
        heading = QLabel("今天想完成什么？")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("例如：写完作业第一题")
        self.task_input.setMaxLength(120)
        layout.addWidget(self.task_input)
        row = QHBoxLayout()
        row.addWidget(QLabel("做到哪里啦？"))
        self.progress_input = QSpinBox()
        self.progress_input.setRange(0, 100)
        self.progress_input.setSuffix(" %")
        row.addWidget(self.progress_input)
        layout.addLayout(row)
        hint = QLabel("慢慢来，做一点也算进步。")
        hint.setStyleSheet("color: #857E73; font-size: 12px;")
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        cancel = QPushButton("收起")
        cancel.clicked.connect(self.hide)
        save = QPushButton("更新进度")
        save.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        self.task_input.returnPressed.connect(self.save)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 固定的轻微不规则曲线，避免重绘时边框抖动。
        path = QPainterPath()
        path.moveTo(23, 7)
        path.cubicTo(90, 5, 205, 9, 278, 7)
        path.quadTo(292, 7, 292, 24)
        path.cubicTo(290, 90, 294, 181, 292, 241)
        path.quadTo(292, 257, 276, 257)
        path.cubicTo(190, 255, 99, 260, 23, 257)
        path.quadTo(8, 257, 8, 241)
        path.cubicTo(10, 175, 6, 91, 8, 24)
        path.quadTo(8, 7, 23, 7)
        path.closeSubpath()
        painter.setPen(QPen(QColor("#575148"), 1.6))
        painter.setBrush(QColor("#FAF7EF"))
        painter.drawPath(path)

    def open_near_fish(self):
        self.task_input.setText(self.kitty.task_name)
        self.progress_input.setValue(self.kitty.progress)
        anchor = self.kitty.mapToGlobal(QPoint(145, 65))
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        available = screen.availableGeometry()
        x = anchor.x()
        if x + self.width() > available.right() + 1:
            x = self.kitty.mapToGlobal(QPoint(85, 65)).x() - self.width()
        x = max(available.left(), min(x, available.right() + 1 - self.width()))
        y = max(available.top(), min(anchor.y(), available.bottom() + 1 - self.height()))
        self.move(x, y)
        self.show()
        self.task_input.setFocus()

    def save(self):
        self.progress_input.interpretText()
        self.kitty.task_name = self.task_input.text().strip()
        self.kitty.progress = self.progress_input.value()
        self.kitty.setToolTip(
            f"{self.kitty.task_name or '今天的小任务'} · {self.kitty.progress}%\n"
            "点击鱼干设置任务 · 左键拖动 · Esc 退出"
        )
        self.kitty.update()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class Kitty(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        assets_path = Path(__file__).resolve().parent / "assets"

        # 加载小猫
        cat_path = assets_path / "cat.png"
        cat_pixmap = QPixmap(str(cat_path))

        if cat_pixmap.isNull():
            raise FileNotFoundError(f"无法加载小猫图片：{cat_path}")

        self.cat = cat_pixmap.scaledToWidth(
            240,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 加载鱼干
        fish_path = assets_path / "fish.png"
        fish_pixmap = QPixmap(str(fish_path))

        if fish_pixmap.isNull():
            raise FileNotFoundError(f"无法加载鱼干图片：{fish_path}")

        self.fish = fish_pixmap.scaledToHeight(
            120,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 找到鱼干主体的上下边界，避免透明留白影响进度
        fish_image = self.fish.toImage()
        visible_rows = []

        for y in range(fish_image.height()):
            for x in range(fish_image.width()):
                if fish_image.pixelColor(x, y).alpha() >= 128:
                    visible_rows.append(y)
                    break

        if not visible_rows:
            raise ValueError("鱼干图片中没有可见内容")

        self.fish_top = visible_rows[0]
        self.fish_bottom = visible_rows[-1] + 1

        self.setFixedSize(345, 270)
        self.drag_offset = None

        # 手动设置的任务进度
        self.progress = 0
        self.task_name = ""
        self.press_position = None
        self.pressed_fish = False
        self.dragged = False
        self.card = TaskCard(self)
        self.setToolTip("点击鱼干设置任务 · 左键拖动 · Esc 退出")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 小猫
        cat_x = 95
        cat_y = self.height() - self.cat.height() - 12
        painter.drawPixmap(cat_x, cat_y, self.cat)

        # 鱼竿
        ink = QColor("#35312E")
        pen = QPen(ink, 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        rod = QPainterPath()
        rod.moveTo(70, self.height() - 20)
        rod.quadTo(85, 55, 125, 55)
        painter.drawPath(rod)

        # 鱼线
        painter.setPen(QPen(ink, 1.5))
        painter.drawLine(
            QPointF(125, 55),
            QPointF(125, 75),
        )

        # 鱼干位置
        fish_x = 125 - self.fish.width() // 2
        fish_y = 58

        # 先画整条半透明鱼干
        painter.save()
        painter.setOpacity(0.3)
        painter.drawPixmap(fish_x, fish_y, self.fish)
        painter.restore()

        # 再从下往上覆盖实体部分
        if self.progress > 0:
            painter.save()

            if self.progress < 100:
                body_height = self.fish_bottom - self.fish_top
                filled_height = body_height * self.progress / 100

                fill_start_y = (
                    fish_y + self.fish_bottom - filled_height
                )

                # 只允许分界线下方的图片被画出来
                painter.setClipRect(
                    QRectF(
                        fish_x,
                        fill_start_y,
                        self.fish.width(),
                        fish_y + self.fish.height() - fill_start_y,
                    )
                )

            painter.setOpacity(1.0)
            painter.drawPixmap(fish_x, fish_y, self.fish)
            painter.restore()

    def fish_contains(self, position):
        # 给细小鱼干留少许点击余量，不要求精确点中线条。
        x = 125 - self.fish.width() // 2
        return QRectF(
            x + 12, 58 + self.fish_top - 5,
            self.fish.width() - 24,
            self.fish_bottom - self.fish_top + 10,
        ).contains(position)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_position = event.globalPosition().toPoint()
            self.drag_offset = self.press_position - self.frameGeometry().topLeft()
            self.pressed_fish = self.fish_contains(event.position())
            self.dragged = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.globalPosition().toPoint() - self.press_position).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self.dragged = True
            if self.dragged:
                self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            open_card = (
                self.pressed_fish and not self.dragged
                and self.fish_contains(event.position())
            )
            self.drag_offset = None
            self.press_position = None
            self.pressed_fish = False
            self.dragged = False
            event.accept()
            if open_card:
                self.card.open_near_fish()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kitty = Kitty()
    kitty.show()
    sys.exit(app.exec())
