import cv2
import numpy as np

from core.data.creation_events import VIANPipeline, vian_pipeline
from core.container.project import *
from core.analysis.analysis_import import *
from core.analysis.analysis_utils import run_analysis

@vian_pipeline
class ERCFilmColorsVIANPipeline(VIANPipeline):
    name = "ERCFilmColors Pipeline"
    version = (1,0,0)
    author = "Gaudenz Halter"

    def __init__(self):
        super(ERCFilmColorsVIANPipeline, self).__init__()

    def on_segment_created(self, project, segment, capture):
        print("Hello Segment")
        pass

    def on_screenshot_created(self, project, screenshot):
        print("Hello Screenshot")
        pass

    def on_svg_annotation_created(self, project, annotation, sub_img):
        print("Hello Annotation")
        pass

    def on_project_finalized(self, project):
        print("Ciao Project")
        pass