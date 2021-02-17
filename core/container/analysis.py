"""
:author Gaudenz Halter

"""

import cv2
import numpy as np
import bisect
from uuid import uuid4
from typing import List
import traceback

from core.data.enums import ANALYSIS_NODE_SCRIPT, ANALYSIS_JOB_ANALYSIS
from .container_interfaces import IProjectContainer, IHasName, ISelectable, _VIAN_ROOT, deprecation_serialization
from core.data.computation import *
from .hdf5_manager import get_analysis_by_name

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.data.interfaces import TimelineDataset, IAnalysisJob, SpatialOverlayDataset


class AnalysisContainer(IProjectContainer, IHasName, ISelectable):
    """
    This is the BaseClass of all AnalysisContainers in the VIAN Project.

    Member Attributes:
        :self.name : The Name of the Container (not the analysis)
        :self.notes : Additional Notes added in the Inspector
        :self.data : The Generic Data Dict defined by the respective Analysis
    """
    def __init__(self, name = "", data = None, unique_id = -1):
        """
        :param name:
        :param data:
        """
        IProjectContainer.__init__(self, unique_id=unique_id)
        self.name = name
        self.notes = ""
        self.data = data
        self.analysis_job_class = "Generic"

    def set_project(self, project):
        IProjectContainer.set_project(self, project)

        # The data is only set when the container is created,
        # else it should already be in the SQLite Database
        if self.data is not None:
            self.set_adata(self.data)

    def unload_container(self, data=None, sync=False):
        super(AnalysisContainer, self).unload_container(self.get_adata(), sync=sync)
        self.data = None

    def get_adata(self):
        return self.data

    def set_adata(self, d):
        self.data = d

    def get_name(self):
        return self.name

    def get_preview(self):
        pass

    def serialize(self):
        data = dict(
            name=self.name,
            unique_id=self.unique_id,
            notes=self.notes,
            data = self.data,
            vian_serialization_type = self.analysis_job_class
        )

        return data

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']
        self.data = serialization['data']
        self.analysis_job_class = serialization['analysis_job_class']

    def delete(self):
        self.project.remove_analysis(self)


class IAnalysisJobAnalysis(AnalysisContainer): #, IStreamableContainer):
    """
    An analysis result which has been performed on some annotation:

    :var target_container: A IProjectContainer which has been analysed
    :var analysis_job_class: The classname of the analysis which has been performed
    :var target_classification_object: The classification object which has been targeted, if the ClassificationObject has a semantic segmentation defined it has been used during analysis


    """
    def __init__(self, name = "NewAnalysisJobResult", results = None, analysis_job_class = None, parameters = None, container = None, target_classification_object = None):
        super(IAnalysisJobAnalysis, self).__init__(name, results)
        self.target_container = container #type: IProjectContainer
        if analysis_job_class is not None:
            self.analysis_job_class = analysis_job_class.__name__
        else:
            self.analysis_job_class = None

        if parameters is not None:
            self.parameters = parameters
        else:
            self.parameters = []
        self.target_classification_object = target_classification_object
        self.a_class = None

    def get_name(self):
        return "{n} ({c})".format(n=self.name,
                                  c=self.target_classification_object.name if self.target_classification_object is not None else "Default")

    def get_preview(self):
        try:
            return get_analysis_by_name(self.analysis_job_class)().get_preview(self)
        except Exception as e:
            print("Preview:", e)

    def get_visualization(self, main_window):
        try:
            return get_analysis_by_name(self.analysis_job_class)().get_visualization(self,
                 self.project.results_dir,
                 self.project.data_dir,
                 self.project,
                 main_window
            )
        except Exception as e:
            print("Exception in get_visualization()", e)

    def get_timeline_datasets(self):
        return self.get_analysis().get_timeline_datasets(self, self.project)

    def get_spatial_overlays(self):
        return self.get_analysis().get_spatial_overlays(self, self.project)

    def get_type(self):
        return ANALYSIS_JOB_ANALYSIS

    def set_target_container(self, container):
        self.target_container = container
        if self.target_container is not None:
            self.target_container.add_analysis(self)

    def set_target_classification_obj(self, class_obj):
        self.target_classification_object = class_obj

    def get_analysis(self):
        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        return self.a_class()

    def serialize(self):
        if self.target_classification_object is not None:
            class_obj_id = self.target_classification_object.unique_id
        else:
            class_obj_id = -1

        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)

        if self.target_container is not None:
            target_id = self.target_container.unique_id
        else:
            target_id = -1

        hdf5_location = self.project.hdf5_manager.location_of(self.unique_id)

        data = dict(
            name=self.name,
            unique_id=self.unique_id,

            hdf5_location = hdf5_location,

            vian_serialization_type=self.__class__.__name__,
            vian_analysis_type=self.analysis_job_class,
            parameters=self.parameters,

            notes=self.notes,
            container =target_id,
            classification_obj = class_obj_id
        )

        return data

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.analysis_job_class = deprecation_serialization(serialization, ['vian_analysis_type','analysis_job_class'])
        self.notes = serialization['notes']

        try:
            self.target_classification_object = project.get_by_id(serialization['classification_obj'])
        except Exception as e:
            log_error("Exception in IAnalysisContainerAnalysis.deserialize()", e)
            pass
        self.parameters = serialization['parameters']

        self.set_target_container(project.get_by_id(serialization['container']))

        return self

    def unload_container(self, data = None, sync = False):
        if data is not None:
            self.data = data
        if self.data is None:
            return

    def get_adata(self):
        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        return self.a_class().from_hdf5(self.project.hdf5_manager.load(self.unique_id))

    def set_adata(self, d):
        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        self.project.hdf5_manager.dump(self.a_class().to_hdf5(d), self.a_class().dataset_name, self.unique_id)
        self.data = None

    def delete(self):
        super(IAnalysisJobAnalysis, self).delete()
        self.cleanup()

    def cleanup(self):
        if self.target_container is not None:
            self.target_container.remove_analysis(self)


class FileAnalysis(IAnalysisJobAnalysis):
    def __init__(self, name="NewFileAnalysis", results=None, analysis_job_class = None, parameters = None, container = None, target_classification_object = None):
        super(FileAnalysis, self).__init__(name, results, analysis_job_class, parameters, container, target_classification_object)
        self._file_path = None

    def set_adata(self, d):
        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        self._file_path = os.path.join(self.project.data_dir, str(self.unique_id))
        self.a_class().to_file(d, self._file_path)

    def get_adata(self):
        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        self._file_path = os.path.join(self.project.data_dir, str(self.unique_id))
        return self.a_class().from_file(self._file_path)

    def get_file_path(self):
        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        return self.a_class().get_file_path(self._file_path)

    def save(self, file_path):
        if self.a_class is None:
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        return self.a_class().to_file(self.get_adata(), file_path)


class SemanticSegmentationAnalysisContainer(IAnalysisJobAnalysis):
    def __init__(self, name = "NewAnalysisJobResult", results = None, analysis_job_class = None, parameters = None, container = None, target_classification_object = None, dataset = ""):
        super(SemanticSegmentationAnalysisContainer, self).__init__(name, results , analysis_job_class, parameters, container, target_classification_object)
        self.dataset = dataset
        self.entry_shape = None

    def get_adata(self):
        if self.a_class is None:
            # self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        data = self.a_class().from_hdf5(self.project.hdf5_manager.load(self.unique_id))
        return data[0:self.entry_shape[0], 0:self.entry_shape[1]]

    def set_adata(self, d):
        if self.a_class is None:
            # self.a_class = self.project.main_window.eval_class(self.analysis_job_class)
            self.a_class = get_analysis_by_name(self.analysis_job_class)
        d, self.entry_shape = self.a_class().to_hdf5(d)
        self.project.hdf5_manager.dump(d, self.a_class().dataset_name, self.unique_id)
        self.data = None

    def serialize(self):
        d = super(SemanticSegmentationAnalysisContainer, self).serialize()
        d['dataset'] = self.dataset
        d['entry_shape'] = self.entry_shape
        d['vian_serialization_type'] = SemanticSegmentationAnalysisContainer.__name__
        return d

    def deserialize(self, serialization, project):
        super(SemanticSegmentationAnalysisContainer, self).deserialize(serialization, project)
        self.dataset = serialization['dataset']
        try:
            self.entry_shape = serialization['entry_shape']
        except:
            self.entry_shape = (512, 512)
        return self


class ColormetryAnalysis(AnalysisContainer):
    def __init__(self, results = None, resolution = 30):
        super(ColormetryAnalysis, self).__init__(name = "Colormetry", data = results)
        self.curr_location = 0
        self.time_ms = []
        self.frame_pos = []
        self.end_idx = 0

        self.analysis_job_class = "Colormetry"

        print("Colormetry Analysis Constructor", resolution)

        self.resolution = resolution
        self.has_finished = False

        self.current_idx = 0
        self.current_junk_idx = 0

        self.linear_colors = []
        for x in range(16):
            for y in range(16):
                for z in range(16):
                    self.linear_colors.append([x * 16, y * 16, z * 16])
        self.linear_colors = np.array([self.linear_colors] * 2, dtype=np.uint8)
        self.linear_colors = cv2.cvtColor(self.linear_colors, cv2.COLOR_LAB2RGB)[0]

        self.last_idx = 0

    def get_histogram(self):
        return self.project.hdf5_manager.col_histograms()
        pass

    def get_palette(self, time_ms):
        pass

    def get_frame_pos(self):
        times = self.project.hdf5_manager.get_colorimetry_times()
        frames = np.multiply(np.divide(times, 1000), self.project.movie_descriptor.fps).astype(np.int).tolist()
        return frames

    def append_data(self, data):
        try:
            self.current_idx = len(self.time_ms)
            self.time_ms.append(data['time_ms'])
            self.project.hdf5_manager.dump_colorimetry(data, self.current_idx, self.end_idx)
            self.check_finished()

        except Exception as e:
            print("ColormetryAnalysis.append_data() raised ", str(e))

    def get_update(self, time_ms):
        try:
            frame_idx = int(np.floor(ms_to_frames(time_ms, self.project.movie_descriptor.fps) / self.resolution))
            if frame_idx == self.last_idx or frame_idx > self.current_idx:
                return None
            self.last_idx = frame_idx
            d = self.project.hdf5_manager.get_colorimetry_pal(frame_idx)
            hist = self.project.hdf5_manager.get_colorimetry_hist(frame_idx)
            spatial = self.project.hdf5_manager.get_colorimetry_spatial()
            times = self.project.hdf5_manager.get_colorimetry_times()
            layers = [
                d[:, 1].astype(np.int),
                d[:, 2:5].astype(np.uint8),
                d[:, 5].astype(np.int)
            ]
            return dict(palette = layers,
                        histogram=hist,
                        spatial=spatial,
                        times=times,
                        frame_idx = frame_idx,
                        current_idx = self.current_idx
                        )
        except Exception as e:
            print(e)
            pass

    def get_time_palette(self):
        time_palette_data = []
        d = self.project.hdf5_manager.get_colorimetry_pal()
        palette_layers = d[:, :, 1].astype(np.int)
        palette_cols = d[:, :, 2:5].astype(np.uint8)
        palette_bins = d[:, :, 5].astype(np.int)
        for t in range(palette_layers.shape[0] - 1):
            time_palette_data.append([
                np.array(palette_layers[t]),
                np.array(palette_cols[t]),
                np.array(palette_bins[t])
            ])
        return [time_palette_data, self.time_ms]

    def check_finished(self):
        log_info("Status Colorimetry", int(self.current_idx), int(self.end_idx - 1))
        if int(self.current_idx) >= int(self.end_idx - 10):
            self.has_finished = True
        return self.has_finished

    def clear(self):
        log_info("Clearing Colorimetry, Resolution:", self.resolution)
        n_frames = int(np.floor(ms_to_frames(self.project.movie_descriptor.duration, self.project.movie_descriptor.fps) / self.resolution))

        self.project.hdf5_manager.initialize_colorimetry(n_frames)
        self.end_idx = n_frames
        self.curr_location = 0
        self.time_ms = []
        self.frame_pos = []

        self.has_finished = False
        self.current_idx = 0

    def serialize(self):
        serialization = dict(
            name=self.name,
            unique_id=self.unique_id,
            vian_serialization_type=self.__class__.__name__,
            resolution = self.resolution,
            curr_idx = self.current_idx,
            time_ms = self.time_ms,
            end_idx = self.end_idx,
            notes=self.notes,
            has_finished = self.has_finished
        )
        return serialization

    def deserialize(self, serialization, project):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.notes = serialization['notes']

        try:
            self.has_finished = serialization['has_finished']
            self.resolution = serialization['resolution']
            self.time_ms = serialization['time_ms']
            self.current_idx = len(self.time_ms)
            self.end_idx = serialization['end_idx']
        except Exception as e:
            log_error("Exception in Loading Analysis", str(e))
        self.current_idx = project.hdf5_manager.get_colorimetry_length() - 1
        self.time_ms = project.hdf5_manager.get_colorimetry_times()[:self.current_idx + 1].tolist()
        self.check_finished()
        return self

    def __iter__(self):
        """
        Returns a dictionary with all entries from the colorimetry:

        palette = layers,
        histogram=hist,
        spatial=spatial,
        times=times,
        frame_idx = frame_idx,
        current_idx = self.current_idx

        :return:
        """
        _iter_idx  = 0
        while _iter_idx < len(self.time_ms):
            yield self.get_update(self.time_ms[_iter_idx])
            _iter_idx += 1

    def iter_avg_color(self):
        _iter_idx = 0
        while _iter_idx < len(self.time_ms):
            time_ms = self.time_ms[_iter_idx]
            hdf5_idx = _iter_idx
            print(hdf5_idx)
            l,a,b = tuple(self.project.hdf5_manager.get_colorimetry_feat(hdf5_idx)[:3])
            _,c,h = tuple(lab_to_lch([l,a,b]))
            yield dict(
                time_ms=time_ms,
                l = l,
                a=a,
                b=b,
                c=c,
                h=h
            )
            _iter_idx += 1

    def __len__(self):
        return len(self.time_ms)




