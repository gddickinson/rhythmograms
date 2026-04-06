"""Dark theme QSS stylesheet for the rhythmogram simulator."""

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
}

QGroupBox {
    border: 1px solid #3a3a5c;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    color: #b0b0d0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #d0d0ff;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #2a2a4a;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #6060b0;
    border: 1px solid #8080d0;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #8080d0;
}

QDoubleSpinBox, QSpinBox {
    background-color: #2a2a4a;
    border: 1px solid #3a3a5c;
    border-radius: 4px;
    padding: 2px 4px;
    color: #e0e0e0;
    min-width: 65px;
}

QPushButton {
    background-color: #3a3a5c;
    border: 1px solid #4a4a6c;
    border-radius: 5px;
    padding: 6px 14px;
    color: #e0e0e0;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #4a4a7c;
    border-color: #6a6a9c;
}

QPushButton:pressed {
    background-color: #2a2a4a;
}

QPushButton#accent {
    background-color: #5050a0;
    border-color: #6060b0;
}

QPushButton#accent:hover {
    background-color: #6060b0;
}

QCheckBox {
    spacing: 6px;
    color: #d0d0e0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #4a4a6c;
    border-radius: 3px;
    background-color: #2a2a4a;
}

QCheckBox::indicator:checked {
    background-color: #5050a0;
    border-color: #6060b0;
}

QLabel {
    color: #c0c0d0;
}

QLabel#title {
    font-size: 16px;
    font-weight: bold;
    color: #d0d0ff;
    padding: 4px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QSplitter::handle {
    background-color: #2a2a4a;
    width: 3px;
}

QStatusBar {
    background-color: #12122a;
    color: #8080a0;
    font-size: 11px;
}

QMenuBar {
    background-color: #1a1a2e;
    color: #e0e0e0;
}

QMenuBar::item:selected {
    background-color: #3a3a5c;
}

QMenu {
    background-color: #1a1a2e;
    border: 1px solid #3a3a5c;
}

QMenu::item:selected {
    background-color: #3a3a5c;
}

QToolTip {
    background-color: #2a2a4a;
    color: #e0e0e0;
    border: 1px solid #4a4a6c;
    border-radius: 4px;
    padding: 4px;
}

QProgressBar {
    border: 1px solid #3a3a5c;
    border-radius: 3px;
    text-align: center;
    color: #e0e0e0;
    background-color: #2a2a4a;
    height: 10px;
}

QProgressBar::chunk {
    background-color: #5050a0;
    border-radius: 2px;
}
"""
