from threading import Lock
from vian.core.data.interfaces import IAnalysisJob
from vian.core.container.container_interfaces import BaseProjectEntity
from typing import List, Dict
from vian.core.container.project import ClassificationObject, VIANProject

PROJECT_LOCK = Lock()

def progress_dummy(args, **kwargs):
    pass

def run_analysis(project:VIANProject, analysis: IAnalysisJob, targets: List[BaseProjectEntity],
                 class_objs: List[ClassificationObject]=None):
    fps = project.movie_descriptor.fps
    if not isinstance(class_objs, list):
        class_objs = [class_objs]

    for clobj in class_objs:
        args = analysis.prepare(project, targets, fps, clobj)

        res = []
        if analysis.multiple_result:
            for i, arg in enumerate(args):
                res.append(analysis.process(arg, progress_dummy))
        else:
            res = analysis.process(args, progress_dummy)

        if isinstance(res, list):
            for r in res:
                if r is not None:
                    with PROJECT_LOCK:
                        analysis.modify_project(project, r)
                        project.add_analysis(r)
        else:
            if res is not None:
                with PROJECT_LOCK:
                    analysis.modify_project(project, res)
                    project.add_analysis(res)
