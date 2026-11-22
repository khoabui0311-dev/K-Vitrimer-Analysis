"""Validated downstream choices shared by project persistence and the UI."""
import math

DEFAULT_OPTIONS = {
    'kinetic_component': 'Slow (tau2)', 'kinetics_model_type': 'Arrhenius',
    'kinetics_exclusions': [], 'time_axis_type': 'Log', 'curves_y_axis_scale': 'Linear',
    'mod_plot_type': 'Normalized', 'show_fits': True,
    'opt_alpha': True, 'alpha_reg': .1, 'sub_G_eq': True, 'n_modes': 50,
    'tts_reference_temp': None, 'tts_reference_curve': None,
    'tts_normalization': 'observed', 'tts_generated': False,
    'report_title': 'Relaxation analysis', 'report_notes': '',
}
CHOICES = {
    'kinetic_component': ('Slow (tau2)', 'Fast (tau1)'),
    'kinetics_model_type': ('Arrhenius', 'VFT', 'Eyring (Transition State)',
                            "Van 't Hoff (Decrosslinking)", 'Coupled WLF-Arrhenius'),
    'time_axis_type': ('Log', 'Linear'), 'curves_y_axis_scale': ('Linear', 'Log'),
    'mod_plot_type': ('Normalized', 'Absolute'),
    'tts_normalization': ('observed', 'model_initial', 'absolute'),
}


def validate_options(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT_OPTIONS):
        raise ValueError('Unsupported project analysis options.')
    options = {**DEFAULT_OPTIONS, **value}
    for key, choices in CHOICES.items():
        if options[key] not in choices:
            raise ValueError(f'Invalid analysis option: {key}.')
    for key in ('show_fits', 'opt_alpha', 'sub_G_eq', 'tts_generated'):
        if type(options[key]) is not bool:
            raise ValueError(f'{key} must be true or false.')
    for key, low, high in [('alpha_reg', 1e-5, 10.), ('n_modes', 20, 200)]:
        number = options[key]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f'Invalid spectrum option: {key}.')
    if type(options['n_modes']) is not int:
        raise ValueError('Spectrum bins must be an integer.')
    reference = options['tts_reference_temp']
    if reference is not None and (isinstance(reference, bool) or not isinstance(reference, (int, float)) or not math.isfinite(reference) or reference <= -273.15):
        raise ValueError('Invalid reference temperature.')
    curve = options['tts_reference_curve']
    if curve is not None and (not isinstance(curve, str) or len(curve) > 200):
        raise ValueError('Invalid reference curve.')
    ids = options['kinetics_exclusions']
    if not isinstance(ids, list) or len(ids) > 10000 or any(not isinstance(cid, str) or len(cid) > 200 for cid in ids) or len(set(ids)) != len(ids):
        raise ValueError('Invalid kinetics exclusions.')
    for key, limit in [('report_title', 200), ('report_notes', 4000)]:
        if not isinstance(options[key], str) or len(options[key]) > limit:
            raise ValueError(f'{key} exceeds its text limit.')
    return options
