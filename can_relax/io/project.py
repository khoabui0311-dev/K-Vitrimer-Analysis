"""Portable analysis recipes: original input and validated settings, never executable objects."""
import base64
import binascii
import hashlib
import json
import math
from pathlib import PureWindowsPath

from can_relax.core.models import PRONY
from can_relax.version import APP_NAME, VERSION
from can_relax.io.project_options import validate_options

MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_PROJECT_BYTES = 36 * 1024 * 1024
DEFAULT_SETTINGS = {
    'analysis_fit_model': 'Maxwell', 'plateau_mode': 'Zero', 'fixed_plateau': 0.0,
    'tg_input': 50.0, 'g_prime_input': 1.0, 'time_origin': 0.0,
    'time_cutoff': 0.0, 'kinetics_mode': 'Fit Parameter',
}


def _number(value, label, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number.')
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError(f'{label} is outside its allowed range.')
    return float(value)


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object.')
    return value


def _ids(value, label):
    if not isinstance(value, list) or len(value) > 10000 or any(not isinstance(v, str) or len(v) > 200 for v in value):
        raise ValueError(f'Invalid {label}.')
    if len(set(value)) != len(value):
        raise ValueError(f'Duplicate entries in {label}.')
    return value


def validate_recipe(recipe):
    """Return a canonical recipe; reject malformed settings before touching session state."""
    _mapping(recipe, 'Project')
    settings = _mapping(recipe.get('settings'), 'Settings')
    if set(settings) != set(DEFAULT_SETTINGS):
        raise ValueError('Project settings are missing or unsupported.')
    choices = {
        'analysis_fit_model': ('Maxwell', 'Single_KWW', 'Dual_KWW', PRONY),
        'plateau_mode': ('Zero', 'Fit', 'Fixed'),
        'kinetics_mode': ('Fit Parameter', 'Raw 1/e'),
    }
    checked = dict(settings)
    for name, options in choices.items():
        if checked[name] not in options:
            raise ValueError(f'Unsupported setting: {name}.')
    for name in ('tg_input', 'time_origin', 'time_cutoff', 'fixed_plateau', 'g_prime_input'):
        minimum = 0 if name in ('time_cutoff', 'fixed_plateau') else (.01 if name == 'g_prime_input' else None)
        checked[name] = _number(checked[name], name, minimum, 5000 if name == 'g_prime_input' else None)
    if checked['analysis_fit_model'] == 'Dual_KWW' and checked['plateau_mode'] != 'Zero':
        raise ValueError('Dual KWW supports a zero plateau only.')
    timing = _mapping(recipe.get('curve_timing'), 'Curve timing')
    exclusions = _mapping(recipe.get('point_exclusions'), 'Point exclusions')
    _ids(list(timing), 'curve IDs')
    _ids(list(exclusions), 'curve IDs')
    checked_timing = {}
    for cid, values in timing.items():
        _mapping(values, 'Curve timing')
        if set(values) != {'origin', 'cutoff'}:
            raise ValueError('Each curve needs an origin and cutoff.')
        checked_timing[cid] = {'origin': _number(values['origin'], 'Origin'),
                               'cutoff': _number(values['cutoff'], 'Cutoff', 0)}
    for points in exclusions.values():
        if not isinstance(points, list) or any(type(p) is not int or p < 1 for p in points) or len(set(points)) != len(points):
            raise ValueError('Excluded points must be unique positive integers.')
    selected = recipe.get('selected_curves')
    if selected is not None:
        _ids(selected, 'selected curves')
    analysed = recipe.get('analysed')
    if type(analysed) is not bool:
        raise ValueError('Invalid analysis status.')
    return {'settings': checked, 'curve_timing': checked_timing,
            'point_exclusions': exclusions, 'selected_curves': selected, 'analysed': analysed,
            'options': validate_options(recipe.get('options', {}))}


def save_project(source, filename, recipe):
    if not source or len(source) > MAX_SOURCE_BYTES:
        raise ValueError('Projects support source files up to 25 MB.')
    filename = PureWindowsPath(filename).name
    if PureWindowsPath(filename).suffix.lower() not in ('.csv', '.xlsx'):
        raise ValueError('Projects require a CSV or XLSX source.')
    recipe = validate_recipe(recipe)
    document = {
        'format': 'vitrifit-project', 'schema_version': 2,
        'software': {'name': APP_NAME, 'version': VERSION},
        'source': {'filename': filename, 'sha256': hashlib.sha256(source).hexdigest(),
                   'base64': base64.b64encode(source).decode('ascii')},
        **recipe,
    }
    encoded = json.dumps(document, allow_nan=False).encode('utf-8')
    if len(encoded) > MAX_PROJECT_BYTES:
        raise ValueError('Project is too large (maximum 36 MB).')
    return encoded


def load_project(data):
    if len(data) > MAX_PROJECT_BYTES:
        raise ValueError('Project is too large (maximum 36 MB).')
    try:
        document = json.loads(data)
        _mapping(document, 'Project')
        if document.get('format') != 'vitrifit-project' or type(document.get('schema_version')) is not int or document['schema_version'] not in (1, 2):
            raise ValueError('Unsupported project format or version.')
        if document['schema_version'] == 1:
            document['options'] = {}
        elif 'options' not in document:
            raise ValueError('Project analysis options are missing.')
        recipe = validate_recipe(document)
        source = _mapping(document.get('source'), 'Source')
        filename = source['filename']
        if not isinstance(filename, str) or len(filename) > 255 or PureWindowsPath(filename).name != filename or PureWindowsPath(filename).suffix.lower() not in ('.csv', '.xlsx'):
            raise ValueError('Invalid source filename.')
        raw = base64.b64decode(source['base64'], validate=True)
        if not raw or len(raw) > MAX_SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('Project source is damaged or its checksum does not match.')
        software = _mapping(document.get('software'), 'Software')
        version = software.get('version')
        if not isinstance(version, str) or len(version) > 80:
            raise ValueError('Invalid software version.')
        return {**recipe, 'source_bytes': raw, 'filename': filename, 'saved_version': version,
                'schema_version': document['schema_version']}
    except (KeyError, TypeError, UnicodeError, binascii.Error, RecursionError) as exc:
        raise ValueError('Invalid or damaged VitriFit project.') from exc
