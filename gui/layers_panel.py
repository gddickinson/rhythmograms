"""Layer management panel — stack multiple traces with different configurations."""

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSlider, QCheckBox, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QColor, QIcon, QPainter

from core.pendulum import HarmonographConfig
from effects.color import ColorConfig


@dataclass
class LayerItem:
    """A single compositing layer."""
    name: str
    pixmap: QPixmap
    config: HarmonographConfig
    color_config: ColorConfig
    enabled: bool = True
    opacity: float = 1.0


class LayersPanel(QWidget):
    """Panel for managing compositing layers.

    Workflow:
    1. Draw a trace with some config
    2. Click "Save as Layer" to store it
    3. Change pendulum/color params (or use "Random Layer" / "From Preset")
    4. Draw a new trace — previous layers composite underneath
    5. Repeat to build up complex multi-trace compositions
    """

    layers_changed = pyqtSignal()
    flatten_requested = pyqtSignal()
    load_layer_config = pyqtSignal(object, object)  # (HarmonographConfig, ColorConfig)
    random_layer_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layers: List[LayerItem] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        title = QLabel("Layers")
        title.setObjectName("title")
        layout.addWidget(title)

        desc = QLabel(
            "Build complex compositions by stacking traces.\n"
            "Each layer can use a different configuration."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #808098; font-size: 10px;")
        layout.addWidget(desc)

        # --- Add layer actions ---
        add_group = QGroupBox("Add Layer")
        ag = QVBoxLayout(add_group)

        self.save_btn = QPushButton("Save Current Drawing as Layer")
        self.save_btn.setObjectName("accent")
        self.save_btn.setToolTip("Flatten current drawing into a new layer")
        self.save_btn.clicked.connect(self.flatten_requested)
        ag.addWidget(self.save_btn)

        row = QHBoxLayout()
        self.random_btn = QPushButton("New Random Layer")
        self.random_btn.setToolTip(
            "Save current + load a smart random config for next trace")
        self.random_btn.clicked.connect(self._on_random_layer)
        row.addWidget(self.random_btn)

        self.duplicate_btn = QPushButton("Duplicate Layer")
        self.duplicate_btn.setToolTip("Save current drawing and continue with same config")
        self.duplicate_btn.clicked.connect(self._on_duplicate)
        row.addWidget(self.duplicate_btn)
        ag.addLayout(row)

        layout.addWidget(add_group)

        # --- Layer list ---
        list_group = QGroupBox("Layer Stack")
        lg = QVBoxLayout(list_group)

        self.layer_list = QListWidget()
        self.layer_list.setMaximumHeight(180)
        self.layer_list.currentRowChanged.connect(self._on_selection_change)
        lg.addWidget(self.layer_list)

        row = QHBoxLayout()
        self.load_btn = QPushButton("Load Config")
        self.load_btn.setToolTip("Load this layer's config into the editor")
        self.load_btn.clicked.connect(self._on_load_config)
        row.addWidget(self.load_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_selected)
        row.addWidget(self.delete_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._clear_all)
        row.addWidget(self.clear_btn)
        lg.addLayout(row)

        layout.addWidget(list_group)

        # --- Selected layer controls ---
        ctrl_group = QGroupBox("Selected Layer")
        cg = QVBoxLayout(ctrl_group)

        self.enable_check = QCheckBox("Visible")
        self.enable_check.setChecked(True)
        self.enable_check.toggled.connect(self._on_toggle_enabled)
        cg.addWidget(self.enable_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("Opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_change)
        row.addWidget(self.opacity_slider)
        cg.addLayout(row)

        layout.addWidget(ctrl_group)

        self.info_label = QLabel("No layers")
        self.info_label.setStyleSheet("color: #808098;")
        layout.addWidget(self.info_label)

        layout.addStretch()
        self._update_info()

    @property
    def layers(self) -> List[LayerItem]:
        return self._layers

    def add_layer(self, pixmap: QPixmap, config: HarmonographConfig,
                  color_config: ColorConfig):
        """Add a new layer from a rendered pixmap."""
        name = f"Layer {len(self._layers) + 1}"
        layer = LayerItem(
            name=name, pixmap=pixmap.copy(),
            config=config, color_config=color_config,
        )
        self._layers.append(layer)

        item = QListWidgetItem(name)
        icon_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        item.setIcon(QIcon(icon_pixmap))
        self.layer_list.addItem(item)
        self.layer_list.setCurrentRow(len(self._layers) - 1)

        self._update_info()
        self.layers_changed.emit()

    def composite_layers(self, base_pixmap: QPixmap) -> QPixmap:
        """Composite all enabled layers under the base pixmap."""
        if not self._layers:
            return base_pixmap

        w, h = base_pixmap.width(), base_pixmap.height()
        result = QPixmap(w, h)
        result.fill(QColor(0, 0, 0, 0))

        painter = QPainter(result)

        for layer in self._layers:
            if not layer.enabled:
                continue
            painter.setOpacity(layer.opacity)
            scaled = layer.pixmap.scaled(
                w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)

        painter.setOpacity(1.0)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.end()

        return result

    def _on_selection_change(self, row):
        if 0 <= row < len(self._layers):
            layer = self._layers[row]
            self.enable_check.setChecked(layer.enabled)
            self.opacity_slider.setValue(int(layer.opacity * 100))

    def _on_toggle_enabled(self, checked):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self._layers):
            self._layers[row].enabled = checked
            self.layers_changed.emit()

    def _on_opacity_change(self, value):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self._layers):
            self._layers[row].opacity = value / 100.0
            self.layers_changed.emit()

    def _on_load_config(self):
        """Load the selected layer's config into the editor."""
        row = self.layer_list.currentRow()
        if 0 <= row < len(self._layers):
            layer = self._layers[row]
            self.load_layer_config.emit(layer.config, layer.color_config)

    def _on_random_layer(self):
        """Save current + request smart random config for next trace."""
        self.flatten_requested.emit()
        self.random_layer_requested.emit()

    def _on_duplicate(self):
        """Save current drawing as layer without changing config."""
        self.flatten_requested.emit()

    def _delete_selected(self):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self._layers):
            self._layers.pop(row)
            self.layer_list.takeItem(row)
            self._update_info()
            self.layers_changed.emit()

    def _clear_all(self):
        self._layers.clear()
        self.layer_list.clear()
        self._update_info()
        self.layers_changed.emit()

    def _update_info(self):
        n = len(self._layers)
        enabled = sum(1 for l in self._layers if l.enabled)
        if n == 0:
            self.info_label.setText("No layers")
        else:
            self.info_label.setText(
                f"{n} layer{'s' if n != 1 else ''} ({enabled} visible)")
