"""Publish the latest switch measurements in an atomic JSON file."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


class MetricsPublisher:
    def __init__(self, path):
        self.path = Path(path)
        self._switches = {}

    def reset(self, dpid):
        self._switches.pop(str(dpid), None)
        self._save()

    def update(self, dpid, timestamp, rates, blocked=()):
        sources = {
            ip: {
                'packets': entry.packets,
                'bytes': entry.bytes,
                'pps': round(entry.pps, 3),
                'bps': round(entry.bps, 3),
            }
            for ip, entry in sorted(rates.items())
        }
        leaders = sorted(sources, key=lambda ip: (-sources[ip]['pps'], ip))
        self._switches[str(dpid)] = {
            'monotonic_timestamp': timestamp,
            'sources': sources,
            'top_talkers': [
                {'src_ip': ip, 'pps': sources[ip]['pps']}
                for ip in leaders[:5]
            ],
            'blocked': list(blocked),
        }
        self._save()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'switches': self._switches,
        }
        temp_path = self.path.with_name(self.path.name + '.tmp')
        with temp_path.open('w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.path)
