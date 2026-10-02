import sys
import math
from pathlib import Path

from PySide6.QtCore import (
    Qt, QPoint, QPointF, QRectF, QVariantAnimation, QEasingCurve,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QTransform
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
        if self.kitty.state == "feeding":
            return
        self.task_input.setText("" if self.kitty.state == "completed" else self.kitty.task_name)
        self.progress_input.setValue(0 if self.kitty.state == "completed" else self.kitty.progress)
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
        if self.kitty.state == "feeding":
            return
        if self.kitty.state == "completed":
            self.kitty.state = "active"
            self.kitty.display_progress = 0.0
        self.progress_input.interpretText()
        self.kitty.task_name = self.task_input.text().strip()
        self.kitty.progress = self.progress_input.value()
        self.kitty.setToolTip(
            f"{self.kitty.task_name or '今天的小任务'} · {self.kitty.progress}%\n"
            "点击鱼干设置任务 · 左键拖动 · Esc 退出"
        )
        self.kitty.animate_progress()
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
        self.state = "active"
        self.swing_angle = 0.0
        self.feed_time = 0.0
        self.pressed_cat = False
        self.swing_animation = QVariantAnimation(self)
        self.swing_animation.setDuration(1100)
        self.swing_animation.setStartValue(0.0)
        self.swing_animation.setEndValue(1.0)
        self.swing_animation.valueChanged.connect(self.on_swing_frame)
        self.feed_animation = QVariantAnimation(self)
        self.feed_animation.setDuration(1500)
        self.feed_animation.setStartValue(0.0)
        self.feed_animation.setEndValue(1.0)
        self.feed_animation.valueChanged.connect(self.on_feed_frame)
        self.feed_animation.finished.connect(self.finish_feeding)
        self.progress = 0
        self.display_progress = 0.0
        self.progress_animation = QVariantAnimation(self)
        self.progress_animation.setDuration(450)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.progress_animation.valueChanged.connect(self.on_progress_frame)
        self.task_name = ""
        self.press_position = None
        self.pressed_fish = False
        self.dragged = False
        self.card = TaskCard(self)
        self.setToolTip("点击鱼干设置任务 · 左键拖动 · Esc 退出")

    def swing_transform(self):
        transform = QTransform()
        transform.translate(125, 55)
        transform.rotate(self.swing_angle)
        transform.translate(-125, -55)
        return transform

    def cat_offset(self):
        if self.state != "feeding":
            return QPointF(0, 0)
        t = self.feed_time
        # 先蓄力，再扑起，叼住后落回原位。
        if t < 0.18:
            return QPointF(0, 3 * math.sin(math.pi * t / 0.18))
        if t < 0.52:
            u = (t - 0.18) / 0.34
            lift = math.sin(u * math.pi / 2)
            return QPointF(-12 * lift, -50 * lift)
        if t < 0.82:
            u = (t - 0.52) / 0.30
            lift = (1 + math.cos(math.pi * u)) / 2
            return QPointF(-12 * lift, -50 * lift)
        return QPointF(0, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        offset = self.cat_offset()
        cat_y = self.height() - self.cat.height() - 12
        painter.drawPixmap(QPointF(95, cat_y) + offset, self.cat)

        ink = QColor("#35312E")
        pen = QPen(ink, 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        # 底端固定，竿尖跟随轻摆。
        transform = self.swing_transform()
        tip = transform.map(QPointF(125, 55))
        end = transform.map(QPointF(125, 75))
        rod = QPainterPath()
        rod.moveTo(70, self.height() - 20)
        rod.quadTo(85 + self.swing_angle * 0.7, 55, tip.x(), tip.y())
        painter.drawPath(rod)
        painter.setPen(QPen(ink, 1.5))
        painter.drawLine(tip, end)

        if self.state == "feeding":
            self.draw_feeding_fish(painter, cat_y, offset)
        elif self.state != "completed":
            painter.save()
            painter.setTransform(transform, True)
            fish_x = 125 - self.fish.width() // 2
            fish_y = 58
            painter.setOpacity(0.3)
            painter.drawPixmap(fish_x, fish_y, self.fish)
            if self.display_progress > 0:
                painter.setOpacity(1.0)
                if self.display_progress < 100:
                    body_height = self.fish_bottom - self.fish_top
                    start = fish_y + self.fish_bottom - body_height * self.display_progress / 100
                    painter.setClipRect(QRectF(fish_x, start, self.fish.width(), fish_y + self.fish.height() - start))
                painter.drawPixmap(fish_x, fish_y, self.fish)
            painter.restore()

        text = ""
        if self.state == "completed":
            text = "完成啦！点我开始新任务"
        elif self.state == "active" and self.progress == 100 and self.display_progress >= 99.9:
            text = "拍拍我，开饭啦"
        if text:
            painter.setPen(QPen(QColor("#81796C"), 1))
            painter.setBrush(QColor("#FAF7EF"))
            rect = QRectF(155, 112, 184, 32)
            painter.drawRoundedRect(rect, 12, 12)
            painter.setPen(ink)
            font = painter.font()
            font.setPixelSize(12)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def draw_feeding_fish(self, painter, cat_y, offset):
        t = self.feed_time
        mouth = QPointF(123, cat_y + self.cat.height() * 0.68) + offset
        start = QPointF(125, 58 + self.fish_top)
        travel = max(0.0, min(1.0, (t - 0.30) / 0.22))
        travel = travel * travel * (3 - 2 * travel)
        anchor = start * (1 - travel) + mouth * travel
        disappear = max(0.0, min(1.0, (t - 0.82) / 0.18))
        painter.save()
        painter.translate(anchor)
        painter.rotate(-65 * travel)
        size = (1 - 0.40 * travel) * (1 - disappear)
        painter.scale(size, size)
        painter.setOpacity(1 - disappear)
        painter.drawPixmap(QPointF(-self.fish.width() / 2, -self.fish_top), self.fish)
        painter.restore()

    def on_swing_frame(self, value):
        t = float(value)
        self.swing_angle = 6 * math.sin(4 * math.pi * t) * (1 - t) ** 2
        self.update()

    def on_feed_frame(self, value):
        self.feed_time = float(value)
        self.update()

    def start_feeding(self):
        if self.state != "active" or self.progress != 100 or self.display_progress < 99.9:
            return
        self.card.hide()
        self.progress_animation.stop()
        self.swing_animation.stop()
        self.swing_angle = 0.0
        self.state = "feeding"
        self.feed_time = 0.0
        self.feed_animation.start()

    def finish_feeding(self):
        self.state = "completed"
        self.setToolTip("任务完成啦！点击小猫开始新任务 · 左键拖动")
        self.update()

    def cat_contains(self, position):
        y = self.height() - self.cat.height() - 12
        return QRectF(105, y + 20, 225, self.cat.height() - 25).contains(position)

    def animate_progress(self):
        # 连续更新时，从当前画面进度继续过渡。
        self.progress_animation.stop()
        self.progress_animation.setStartValue(float(self.display_progress))
        self.progress_animation.setEndValue(float(self.progress))
        self.progress_animation.start()
        self.swing_animation.stop()
        self.swing_animation.start()

    def on_progress_frame(self, value):
        self.display_progress = float(value)
        self.update()

    def fish_contains(self, position):
        # 给细小鱼干留少许点击余量，不要求精确点中线条。
        if self.state != "active":
            return False
        inverse, valid = self.swing_transform().inverted()
        if valid:
            position = inverse.map(position)
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
            self.pressed_cat = self.cat_contains(event.position())
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
            tap_cat = self.pressed_cat and not self.dragged and self.cat_contains(event.position())
            self.pressed_cat = False
            self.drag_offset = None
            self.press_position = None
            self.pressed_fish = False
            self.dragged = False
            event.accept()
            if self.state != "feeding":
                if tap_cat and self.state == "completed":
                    self.card.open_near_fish()
                elif tap_cat and self.progress == 100:
                    self.start_feeding()
                elif open_card:
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
