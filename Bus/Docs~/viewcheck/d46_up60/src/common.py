# shared helpers for the D-46 OSL renders (Bus/Docs~/viewcheck/d46_up60/src; outputs and the compiled .oso go to /tmp/bus/d46)
import os
import sys

sys.dont_write_bytecode = True
import bpy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..'))
OSL = os.path.join(HERE, 'erode.osl')
OUT = '/tmp/bus/d46'
sys.path.insert(0, os.path.join(REPO, 'Cabin', 'Tools~'))
sys.path.insert(0, os.path.join(REPO, 'Bus', 'Source'))


def cycles_osl(scene, samples=1, threads=0):
    scene.render.engine = 'CYCLES'
    cy = scene.cycles
    cy.device = 'CPU'
    cy.shading_system = True
    cy.samples = samples
    cy.use_adaptive_sampling = False
    cy.max_bounces = 0
    cy.diffuse_bounces = 0
    cy.glossy_bounces = 0
    cy.transmission_bounces = 0
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 64
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.use_light_tree = False
    scene.render.threads_mode = 'FIXED' if threads else 'AUTO'
    if threads:
        scene.render.threads = threads
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.display_settings.display_device = 'sRGB'


IN_PARAMS = [('fade', 0.0), ('hole_open', 0.0), ('resist', 0.0), ('zen_on', 1.0), ('door_bias', 0.0), ('form', 0.0),
             ('erode_enable', 1.0)]
OUT_PARAMS = ['s', 'removed', 'n_uniform']
_COMPILED = []


def script_node(nt):
    """the erode.osl script node. The bpy wheel has no 'oslquery' module (cycles.osl.update_script_node fails), so the
    .osl is compiled here with _cycles.osl_compile and the sockets are made by hand with the shader's parameter names."""
    import _cycles
    os.makedirs(OUT, exist_ok=True)
    oso = os.path.join(OUT, 'erode.oso')
    if not _COMPILED:
        assert _cycles.osl_compile(OSL, oso), 'oslc failed'
        _COMPILED.append(oso)
    node = nt.nodes.new('ShaderNodeScript')
    node.mode = 'EXTERNAL'
    node.filepath = oso
    for k, v in IN_PARAMS:
        sk = node.inputs.new('NodeSocketFloat', k, identifier=k)
        sk.default_value = v
    for k in OUT_PARAMS:
        node.outputs.new('NodeSocketFloat', k, identifier=k)
    return node
