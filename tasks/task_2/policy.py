"""Task 2 (4 points): decision engine, independent of OpenFlow/Mininet."""
import ipaddress
import math

from common.models import BlockDecision, SourceRate


class PolicyEngine:
    def __init__(self, config: dict):
        """config format: {'rules': [{src_ip, max_pps, block_seconds}, ...]}."""
        if not isinstance(config, dict) or not isinstance(config.get('rules'), list):
            raise ValueError('Config must contain a "rules" list.')

        self._rules: dict[str, tuple[float, int]] = {}
        for rule in config['rules']:
            if not isinstance(rule, dict):
                    raise ValueError('Each rule must be a dict.')

            raw_ip = rule.get('src_ip')
            if not isinstance(raw_ip, str):
                    raise ValueError(f'Invalid src_ip: {raw_ip!r}')
            try:
                    src_ip = str(ipaddress.IPv4Address(raw_ip))
            except ValueError as exc:
                    raise ValueError(f'Invalid IPv4 address: {raw_ip!r}') from exc

            if src_ip in self._rules:
                    raise ValueError(f'Duplicate rule for src_ip: {src_ip}')

            max_pps = rule.get('max_pps')
            if (
                    isinstance(max_pps, bool)
                    or not isinstance(max_pps, (int, float))
                    or math.isnan(max_pps)
                    or math.isinf(max_pps)
                    or max_pps < 0
            ):
                    raise ValueError(f'Invalid max_pps for {src_ip}: {max_pps!r}')

            block_seconds = rule.get('block_seconds')
            if (
                    isinstance(block_seconds, bool)
                    or not isinstance(block_seconds, int)
                    or block_seconds <= 0
            ):
                    raise ValueError(f'Invalid block_seconds for {src_ip}: {block_seconds!r}')

            self._rules[src_ip] = (float(max_pps), block_seconds)

        self._active: dict[int, dict[str, float]] = {}

    def _prune(self, dpid: int, timestamp: float) -> dict[str, float]:
        blocks = self._active.get(dpid)
        if not blocks:
            return {}
        expired = [ip for ip, until in blocks.items() if timestamp >= until]
        for ip in expired:
            del blocks[ip]
        if not blocks:
            self._active.pop(dpid, None)
            return {}
        return blocks

    def evaluate(
        self, dpid: int, timestamp: float, rates: dict[str, SourceRate]
    ) -> list[BlockDecision]:
        """Return NEW blocks only, for sources with pps > configured threshold."""
        blocks = self._prune(dpid, timestamp)
        decisions: list[BlockDecision] = []

        for src_ip, rate in sorted(rates.items()):
                rule = self._rules.get(src_ip)
                if rule is None or src_ip in blocks:
                        continue
                max_pps, block_seconds = rule
                if rate.pps > max_pps:
                    switch_blocks = self._active.setdefault(dpid, {})
                    switch_blocks[src_ip] = timestamp + block_seconds
                    blocks = switch_blocks
                    decisions.append(
                        BlockDecision(
                            dpid=dpid,
                            src_ip=src_ip,
                            block_seconds=block_seconds,
                        )
                    )
        return decisions

    def active(self, dpid: int, timestamp: float) -> list[dict]:
        """Return active blocks as [{'src_ip': ..., 'until': ...}, ...]."""
        blocks = self._prune(dpid, timestamp)
        return [
            {'src_ip': src_ip, 'until': until}
            for src_ip, until in sorted(blocks.items())
        ]

    def reset(self, dpid: int) -> None:
        """Forget blocks after disconnect/reconnect of this switch."""
        self._active.pop(dpid, None)
