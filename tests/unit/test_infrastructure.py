"""Ready-made helpers must remain stable for both tasks."""
import json
from common.metrics import MetricsPublisher
from common.models import SourceRate


def test_exporter_writes_and_sorts_top_talkers(tmp_path):
    path = tmp_path / 'runtime' / 'metrics.json'
    publisher = MetricsPublisher(path)
    publisher.update(1, 123.5, {
        '10.0.0.1': SourceRate(100, 200, 10, 1600),
        '10.0.0.2': SourceRate(1000, 800, 20, 6400),
    }, blocked=[{'src_ip': '10.0.0.1', 'until': 131.5}])
    obj = json.loads(path.read_text())
    assert obj['switches']['1']['top_talkers'][0]['src_ip'] == '10.0.0.2'
    assert obj['switches']['1']['blocked'][0]['src_ip'] == '10.0.0.1'
    assert obj['switches']['1']['sources']['10.0.0.1']['pps'] == 10
    publisher.reset(1)
    assert '1' not in json.loads(path.read_text())['switches']
