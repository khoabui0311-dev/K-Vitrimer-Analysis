"""Portable figure formatting: bounded JSON settings without measurements."""
import json
import math
import re

from can_relax.io.publication_fields import FIELDS
from can_relax.version import VERSION

MAX_STYLE_BYTES = 128 * 1024


def validate_style(value):
    if not isinstance(value, dict) or set(value) - set(FIELDS):
        raise ValueError('The figure format contains unsupported settings.')
    checked = {}
    for key, item in value.items():
        rule = FIELDS[key]
        valid = False
        if rule[0] == 'bool':
            valid = type(item) is bool
        elif rule[0] == 'choice':
            valid = any(type(item) is type(choice) and item == choice for choice in rule[1])
        elif rule[0] == 'text':
            valid = isinstance(item, str) and len(item) <= rule[1]
        elif rule[0] == 'color':
            valid = isinstance(item, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', item) is not None
        elif rule[0] == 'number':
            valid = type(item) in (float, int) and math.isfinite(item) and rule[1] <= item <= rule[2]
            if rule[3]:
                valid = valid and type(item) is int
        if not valid:
            raise ValueError(f'Invalid figure format setting: {key}.')
        checked[key] = item
    for prefix, toggle, log_x, log_y in [
        ('pub_rel_', 'pub_rel_cust_lims', value.get('pub_xscale', 'Log') == 'Log', value.get('pub_yscale') == 'Log'),
        ('pub_kin_', 'pub_kin_cust_lims', False, False),
        ('eyr_', 'eyr_clim', False, False),
        ('vh_', 'vh_clim', False, value.get('vh_yscale') == 'Log'),
    ]:
        if value.get(toggle):
            for axis, logarithmic in [('x', log_x), ('y', log_y)]:
                low, high = value.get(prefix + axis + 'min'), value.get(prefix + axis + 'max')
                if low is None or high is None or low >= high or (logarithmic and low <= 0):
                    raise ValueError(f'Invalid {axis}-axis limits in the figure format ({prefix.rstrip("_")}).')
    return checked


def capture_style(state):
    return validate_style({key: state[key] for key in FIELDS if key in state})


def apply_style(state, settings):
    """Validate completely before replacing only publication display settings."""
    settings = validate_style(settings)
    for key in FIELDS:
        state.pop(key, None)
    state.pop('pub_size_preset', None)
    state.update(settings)
    if 'pub_preset' in settings:
        state['pub_size_preset'] = settings['pub_preset']


def save_style(settings, name):
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise ValueError('Give the figure format a name of 1–80 characters.')
    document = {'format': 'vitrifit-figure-style', 'schema_version': 1,
                'software_version': VERSION, 'name': name.strip(), 'settings': validate_style(settings)}
    encoded = json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')
    if len(encoded) > MAX_STYLE_BYTES:
        raise ValueError('The figure format is too large.')
    return encoded


def load_style(data):
    if len(data) > MAX_STYLE_BYTES:
        raise ValueError('The figure format is too large (maximum 128 KB).')
    try:
        document = json.loads(data)
        if (not isinstance(document, dict) or document.get('format') != 'vitrifit-figure-style'
                or type(document.get('schema_version')) is not int or document['schema_version'] != 1):
            raise ValueError('Unsupported figure format file.')
        # Apply the same limits to imported and locally created files.
        save_style(document['settings'], document['name'])
        return {'name': document['name'].strip(), 'settings': validate_style(document['settings'])}
    except (KeyError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid figure format file.') from exc
