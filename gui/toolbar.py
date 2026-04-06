"""Toolbar with transport controls (play/pause/reset) and file actions."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QProgressBar, QLabel,
)
from PyQt6.QtCore import pyqtSignal


class Toolbar(QWidget):
    """Top toolbar with play/pause, reset, export, save/load buttons."""

    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    export_png_clicked = pyqtSignal()
    export_svg_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    load_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Transport
        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("accent")
        self.play_btn.setFixedWidth(70)
        self.play_btn.clicked.connect(self.play_clicked)
        layout.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setFixedWidth(70)
        self.pause_btn.clicked.connect(self.pause_clicked)
        layout.addWidget(self.pause_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFixedWidth(70)
        self.reset_btn.clicked.connect(self.reset_clicked)
        layout.addWidget(self.reset_btn)

        layout.addSpacing(20)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setFixedHeight(14)
        self.progress.setFixedWidth(200)
        layout.addWidget(self.progress)

        self.progress_label = QLabel("0%")
        self.progress_label.setFixedWidth(40)
        layout.addWidget(self.progress_label)

        layout.addStretch()

        # File actions
        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_clicked)
        layout.addWidget(save_btn)

        load_btn = QPushButton("Load Config")
        load_btn.clicked.connect(self.load_clicked)
        layout.addWidget(load_btn)

        layout.addSpacing(10)

        png_btn = QPushButton("Export PNG")
        png_btn.setObjectName("accent")
        png_btn.clicked.connect(self.export_png_clicked)
        layout.addWidget(png_btn)

        svg_btn = QPushButton("Export SVG")
        svg_btn.clicked.connect(self.export_svg_clicked)
        layout.addWidget(svg_btn)

    def set_progress(self, fraction: float):
        """Update progress bar (0.0 to 1.0)."""
        self.progress.setValue(int(fraction * 1000))
        self.progress_label.setText(f"{int(fraction * 100)}%")
