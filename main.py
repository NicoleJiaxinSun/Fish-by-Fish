import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget


class Kitty(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        assets_path = Path(__file__).resolve().parent / "assets"

        # 小猫：保持缩小后的尺寸
        cat_path = assets_path / "cat.png"
        cat_pixmap = QPixmap(str(cat_path))

        if cat_pixmap.isNull():
            raise FileNotFoundError(f"无法加载小猫图片：{cat_path}")

        self.cat = cat_pixmap.scaledToWidth(
            240,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 鱼干：保持放大后的尺寸
        fish_path = assets_path / "fish.png"
        fish_pixmap = QPixmap(str(fish_path))

        if fish_pixmap.isNull():
            raise FileNotFoundError(f"无法加载鱼干图片：{fish_path}")

        self.fish = fish_pixmap.scaledToHeight(
            120,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 场景收窄，上方留出悬挂鱼干的空间
        self.setFixedSize(345, 270)
        self.drag_offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 小猫在右下方
        cat_x = 95
        cat_y = self.height() - self.cat.height() - 12
        painter.drawPixmap(cat_x, cat_y, self.cat)

        ink = QColor("#35312E")
        pen = QPen(ink, 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # 鱼竿顶部降低，竿尖稍向左移
        rod = QPainterPath()
        rod.moveTo(70, self.height() - 20)
        rod.quadTo(85, 55, 125, 55)
        painter.drawPath(rod)

        # 鱼线跟随新的竿尖位置
        painter.setPen(QPen(ink, 1.5))
        painter.drawLine(
            QPointF(125, 55),
            QPointF(125, 75),
        )

        # 鱼干悬在猫鼻子前上方
        fish_x = 125 - self.fish.width() // 2
        fish_y = 58

        painter.save()
        painter.setOpacity(0.3)
        painter.drawPixmap(fish_x, fish_y, self.fish)
        painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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
