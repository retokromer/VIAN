from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from core.visualization.image_plots import ImagePlotTime, ImagePlotPlane, ImagePlotCircular
import numpy as np

class ColorDTWidget(QWidget):
    def __init__(self, parent):
        super(ColorDTWidget, self).__init__(parent)
        self.fg_view = ImagePlotTime(self)
        self.bg_view = ImagePlotTime(self)
        self.gl_view = ImagePlotTime(self)
        self.setLayout(QVBoxLayout(self))

        self.tab = QTabWidget(self)
        self.tab.addTab(self.fg_view, "Foreground")
        self.tab.addTab(self.bg_view, "Background")
        self.tab.addTab(self.gl_view, "Global")

        self.layout().addWidget(self.tab)

    def update_view(self, stills_glob = None, stills_fg = None, stills_bg = None):

        if stills_glob is not None:
            indices = range(len(stills_glob))
            sat = np.array([s.sat for s in stills_glob])
            np.nan_to_num(sat)

            imgs = [s.pixmap for s in stills_glob]
            self.plot(self.gl_view, np.array(indices), np.array(sat), imgs)

        if stills_fg is not None:
            indices = range(len(stills_fg))
            sat = np.array([s.sat for s in stills_fg])
            np.nan_to_num(sat)
            imgs = [s.pixmap for s in stills_fg]
            self.plot(self.fg_view, np.array(indices), np.array(sat), imgs)

        if stills_bg is not None:
            indices = range(len(stills_bg))
            sat = np.array([s.sat for s in stills_bg])
            np.nan_to_num(sat)
            imgs = [s.pixmap for s in stills_bg]
            self.plot(self.bg_view, np.array(indices), np.array(sat), imgs)


    def plot(self, view, time, channel, imgs, is_liminance=True, y_max = None):
        view.clear_view()
        # view.x_scale = 1.0
        # view.y_scale = 1.0

        view.create_scene(len(imgs), 100, pixel_size_x=4000, pixel_size_y=1000)
        print(np.amax(channel))

        for i, img in enumerate(imgs):
            view.add_image(time[i], channel[i], img, convert=False)

        view.update_grid()
        view.sort_images()


class ColorSpacePlots(QWidget):
    def __init__(self, parent, visualizer):
        super(ColorSpacePlots, self).__init__(parent)
        self.fg_view = ImagePlotCircular(self)
        self.bg_view = ImagePlotCircular(self)
        self.gl_view = ImagePlotCircular(self)
        self.setLayout(QVBoxLayout(self))

        visualizer.onImagePosScaleChanged.connect(self.fg_view.scale_pos)
        visualizer.onImagePosScaleChanged.connect(self.bg_view.scale_pos)
        visualizer.onImagePosScaleChanged.connect(self.gl_view.scale_pos)

        self.tab = QTabWidget(self)
        self.tab.addTab(self.fg_view, "Foreground")
        self.tab.addTab(self.bg_view, "Background")
        self.tab.addTab(self.gl_view, "Global")

        self.layout().addWidget(self.tab)

    def update_view(self, stills_glob = None, still_fg = None, still_bg = None):

        self.gl_view.clear_view()
        self.bg_view.clear_view()
        self.fg_view.clear_view()

        self.gl_view.add_grid()
        self.bg_view.add_grid()
        self.fg_view.add_grid()

        for still in stills_glob:
            self.gl_view.add_image(still.col[1],still.col[2], still.pixmap)

        for still in still_fg:
            self.fg_view.add_image(still.col[1],still.col[2], still.pixmap)

        for still in still_bg:
            self.bg_view.add_image(still.col[1], still.col[2], still.pixmap)

        self.bg_view.frame_default()
        self.fg_view.frame_default()
        self.gl_view.frame_default()


class ColorSpaceLPlanePlots(QWidget):
    def __init__(self, parent, visualizer):
        super(ColorSpaceLPlanePlots, self).__init__(parent)
        self.fg_view = ImagePlotPlane(self)
        self.bg_view = ImagePlotPlane(self)
        self.gl_view = ImagePlotPlane(self)
        self.setLayout(QVBoxLayout(self))

        visualizer.onImagePosScaleChanged.connect(self.fg_view.scale_pos)
        visualizer.onImagePosScaleChanged.connect(self.bg_view.scale_pos)
        visualizer.onImagePosScaleChanged.connect(self.gl_view.scale_pos)

        self.tab = QTabWidget(self)
        self.tab.addTab(self.fg_view, "Foreground")
        self.tab.addTab(self.bg_view, "Background")
        self.tab.addTab(self.gl_view, "Global")

        self.layout().addWidget(self.tab)

    def update_view(self, stills_glob = None, still_fg = None, still_bg = None):

        self.gl_view.clear_view()
        self.bg_view.clear_view()
        self.fg_view.clear_view()

        self.gl_view.add_grid()
        self.bg_view.add_grid()
        self.fg_view.add_grid()

        for still in stills_glob:
            self.gl_view.add_image(still.col[1],still.col[0], still.pixmap)

        for still in still_fg:
            self.fg_view.add_image(still.col[1],still.col[0], still.pixmap)

        for still in still_bg:
            self.bg_view.add_image(still.col[1], still.col[0], still.pixmap)

        self.bg_view.frame_default()
        self.fg_view.frame_default()
        self.gl_view.frame_default()