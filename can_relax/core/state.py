"""Content identities and invalidation shared by the app and regression tests."""
import hashlib
import json


DERIVED_KEYS = ('active_results', 'kinetics_df', 'master_data', 'spec_config',
                'spec_results', 'selection_id', 'master_config')


def analysis_identity(data, settings):
    digest = hashlib.sha256(data)
    digest.update(json.dumps(settings, sort_keys=True, allow_nan=False).encode('utf-8'))
    return digest.hexdigest()


def clear_analysis(state):
    for key in ('results', 'analysis_id', *DERIVED_KEYS):
        state.pop(key, None)


def clear_derived(state):
    for key in DERIVED_KEYS:
        state.pop(key, None)
