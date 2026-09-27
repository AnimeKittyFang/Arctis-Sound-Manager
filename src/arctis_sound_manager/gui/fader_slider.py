# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Vertical slider whose handle is painted as a mixing-desk fader cap
(silver body, concave face, drop shadow) instead of the QSS round dot.

The QSS still sizes the handle (hit area + groove geometry); it just has to
leave it transparent — see FADER_HANDLE_QSS.
"""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider

CAP_W = 26
CAP_H = 24

# Drop-in replacements for the `QSlider::handle` rule. The negative margin is
# relative to the 6px groove: 6 + 2 * 10 = CAP_W across a vertical groove.
FADER_HANDLE_QSS = f"""
    QSlider::handle:vertical {{
        background: transparent;
        border: none;
        height: {CAP_H}px;
        margin: 0 -{(CAP_W - 6) // 2}px;
    }}
"""

# Horizontal: the cap is painted upright, so it is CAP_W along the groove
# and CAP_H across it.
FADER_HANDLE_QSS_H = f"""
    QSlider::handle:horizontal {{
        background: transparent;
        border: none;
        width: {CAP_W}px;
        margin: -{(CAP_H - 6) // 2}px 0;
    }}
"""


def _pinched_rect(r: QRectF, pinch: float, radius: float) -> QPainterPath:
    """Rounded rect whose left/right sides curve inward by *pinch* px."""
    path = QPainterPath()
    l, t, rt, b = r.left(), r.top(), r.right(), r.bottom()
    cy = r.center().y()
    path.moveTo(l + radius, t)
    path.lineTo(rt - radius, t)
    path.quadTo(rt, t, rt, t + radius)
    path.quadTo(rt - pinch, cy, rt, b - radius)
    path.quadTo(rt, b, rt - radius, b)
    path.lineTo(l + radius, b)
    path.quadTo(l, b, l, b - radius)
    path.quadTo(l + pinch, cy, l, t + radius)
    path.quadTo(l, t, l + radius, t)
    path.closeSubpath()
    return path


def paint_fader_cap(painter: QPainter, rect: QRectF, enabled: bool = True) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    body = rect.adjusted(0.5, 0.5, -0.5, -2.5)  # leave room for the shadow

    # Soft drop shadow: a few stacked, offset, translucent shapes
    painter.setPen(Qt.PenStyle.NoPen)
    for offset, alpha in ((2.5, 40), (1.5, 60), (0.8, 80)):
        painter.setBrush(QColor(0, 0, 0, alpha))
        painter.drawPath(_pinched_rect(body.translated(0, offset), 1.2, 4))

    # Body: bright rim, lit from above
    body_path = _pinched_rect(body, 1.2, 4)
    grad = QLinearGradient(body.topLeft(), body.bottomLeft())
    grad.setColorAt(0.0, QColor("#ffffff"))
    grad.setColorAt(0.5, QColor("#ececec"))
    grad.setColorAt(1.0, QColor("#d2d2d2"))
    painter.setBrush(grad)
    painter.setPen(QPen(QColor(0, 0, 0, 70), 1))
    painter.drawPath(body_path)

    # Concave face: darker towards the bottom, as if the dish catches the shade
    face = body.adjusted(3, 2.5, -3, -3.5)
    face_path = _pinched_rect(face, 1.6, 2.5)
    grad = QLinearGradient(face.topLeft(), face.bottomLeft())
    grad.setColorAt(0.0, QColor("#f4f4f4"))
    grad.setColorAt(0.55, QColor("#dcdcdc"))
    grad.setColorAt(1.0, QColor("#b9b9b9"))
    painter.setBrush(grad)
    painter.setPen(QPen(QColor(0, 0, 0, 35), 0.8))
    painter.drawPath(face_path)

    # Bottom lip highlight under the face
    painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
    painter.drawLine(QPointF(face.left() + 2, face.bottom() + 1.5),
                     QPointF(face.right() - 2, face.bottom() + 1.5))

    if not enabled:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 90))
        painter.drawPath(body_path)
    painter.restore()


class FaderSlider(QSlider):
    """QSlider that paints a fader cap over its (transparent) QSS handle.

    Pair it with FADER_HANDLE_QSS (vertical) or FADER_HANDLE_QSS_H (horizontal).
    """

    def handle_rect(self) -> QRectF:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        r = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self)
        # Center the cap on the handle whatever the widget's cross size
        cx = r.center().x() + 0.5
        cy = r.center().y() + 0.5
        return QRectF(cx - CAP_W / 2, cy - CAP_H / 2, CAP_W, CAP_H)

    def _fit_cap(self, size: QSize) -> QSize:
        # Leave room for the whole cap and its shadow across the groove
        if self.orientation() == Qt.Orientation.Horizontal:
            size.setHeight(max(size.height(), CAP_H + 4))
        else:
            size.setWidth(max(size.width(), CAP_W + 2))
        return size

    def sizeHint(self) -> QSize:
        return self._fit_cap(super().sizeHint())

    def minimumSizeHint(self) -> QSize:
        return self._fit_cap(super().minimumSizeHint())

    def paint_under_cap(self, painter: QPainter) -> None:
        """Subclass hook: extra decorations (ticks, bars) the cap must cover."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.save()
        self.paint_under_cap(painter)
        painter.restore()
        paint_fader_cap(painter, self.handle_rect(), self.isEnabled())
        painter.end()
