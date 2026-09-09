"""Desktop startup contracts that protect local-only operation and process cleanup."""
import subprocess

from desktop.launcher import LocalServer, resource_root, server_options


def test_desktop_resources_and_local_only_configuration():
    root = resource_root()
    assert (root / 'can_relax/gui/app.py').is_file()
    assert (root / 'examples/toy_data.csv').is_file()
    options = server_options(54321)
    assert options['server.address'] == '127.0.0.1'
    assert options['server.port'] == 54321
    assert options['browser.gatherUsageStats'] is False
    assert options['server.fileWatcherType'] == 'none'


def test_server_cleanup_escalates_after_timeout():
    class Process:
        def __init__(self):
            self.terminated = self.killed = False
        def poll(self):
            return None
        def terminate(self):
            self.terminated = True
        def wait(self, timeout):
            if not self.killed:
                raise subprocess.TimeoutExpired('server', timeout)
            return 0
        def kill(self):
            self.killed = True
    server = LocalServer()
    server.process = Process()
    server.stop()
    assert server.process.terminated and server.process.killed


def test_example_works_when_launched_outside_project(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    app_path = resource_root() / 'can_relax/gui/app.py'
    monkeypatch.chdir(tmp_path)
    app = AppTest.from_file(str(app_path), default_timeout=60).run()
    app.checkbox(key='use_example_data').check().run()
    assert not app.exception
    assert not app.error
