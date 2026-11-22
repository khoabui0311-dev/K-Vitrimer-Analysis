from pathlib import Path

from desktop.workflow_check import verify_workflow
from tests import APP_PATH


def test_new_user_import_review_fresh_reopen_and_real_exports():
    source = Path(APP_PATH).parents[2] / 'examples/toy_data.csv'
    app, report = verify_workflow(APP_PATH, source.read_bytes())
    assert not app.exception
    assert report['curves'] == 4
    assert report['reviewed_points'] == 3
    assert report['fresh_session_reopen'] == 'identical fitted parameters'
