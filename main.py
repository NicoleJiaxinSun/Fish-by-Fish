import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget, QInputDialog


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

        self.setToolTip("左键拖动 · 右键设置进度 · Esc 退出")

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

    def edit_progress(self):
        value, confirmed = QInputDialog.getInt(
            self,
            "任务进度",
            "现在完成了多少？（%）",
            self.progress,
            0,
            100,
            1,
        )

        if confirmed:
            self.progress = value
            self.setToolTip(
                f"当前进度：{self.progress}%\n"
                "左键拖动 · 右键设置进度 · Esc 退出"
            )

            # 通知窗口重新绘制鱼干
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.edit_progress()
            event.accept()

        elif event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self.drag_offset is not None
        ):
            self.move(
                event.globalPosition().toPoint() - self.drag_offset
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = None
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


app = QApplication(sys.argv)
kitty = Kitty()
kitty.show()
sys.exit(app.exec())
