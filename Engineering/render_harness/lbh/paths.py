# -*- coding: utf-8 -*-
"""Where things live in the repo. Every other module imports from here, so the harness can be run from any cwd."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(HERE)                      # Engineering/render_harness
REPO = os.path.dirname(os.path.dirname(HARNESS))     # repo root

GRADES_ENGINE = os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_engine.json')
ENGINE_DIR = os.path.join(REPO, 'Grading', 'Tools~', 'engine')
SCENE_DATA_DIR = os.path.join(REPO, 'Art', 'tools', 'v21')
CUES_JSON = os.path.join(REPO, 'FromLocal', 'cues.json')
CAMERAS_JSON = os.path.join(HARNESS, 'cameras.json')
BUS_JSON = os.path.join(HARNESS, 'bus_shell.json')
FONT = os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf')


def import_engine():
    """Grading/Tools~/engine/ppv2_engine.py: the engine-faithful PPv2 colour grade (single source of truth)."""
    if ENGINE_DIR not in sys.path:
        sys.path.insert(0, ENGINE_DIR)
    import ppv2_engine
    return ppv2_engine


def import_scene_data():
    """Art/tools/v21/scene_data_v21.py: palettes (display targets) and the APL score per phase."""
    if SCENE_DATA_DIR not in sys.path:
        sys.path.insert(0, SCENE_DATA_DIR)
    import scene_data_v21
    return scene_data_v21
