# Отчет по SDN дз

## Описание алгоритма
1. **Мониторинг (`tasks/tsk_1`)**: контроллер раз в `poll_interval` секунд отправялет коммутатору `OFPFlowStatusRequest` с фильтром по `FORWARD_COOKIE` и уникальным `xid`, собирает составные ответы (`OFPMPF_REPLY_MORE`) и передает счётчики в `FlowRateTracker`. Для каждого `src_ip` вычисляются `pps` и `bps` по положительным дельтам счётчиков за время `dt` (первый замер, новые и удаленные flow не дают ложных скачков).
2. **Детектор и блокировка (`tasks/task_2`)**: `PolicyEngine` валидует конфиг и сравнивает `pps` с порогом `max_pps`. При `pps > max_pps` (если источник еще не заблокирован) контроллер отправляет `OFPFlowMod` с `priority=300`, `eth_type=0x0800`, `ip4_src`, пустыми `instructions=[]` (drop) и `hard_timeout=block_seconds`.  

## pytest
```
.......................                                                  [100%]
23 passed in 0.03s


## metrics.json
```json
{
  "generated_at": "2026-11-27T18:16:24.597673+00:00",
  "switches": {
    "1": {
      "monotonic_timestamp": 15151.773723534,
      "sources": {
        "10.0.0.1": {
          "packets": 56,
          "bytes": 5488,
          "pps": 0.0,
          "bps": 0.0
        },
        "10.0.0.4": {
          "packets": 61,
          "bytes": 5978,
          "pps": 0.0,
          "bps": 0.0
        }
      },
      "top_talkers": [
        {
          "src_ip": "10.0.0.1",
          "pps": 0.0
        },
        {
          "src_ip": "10.0.0.4",
          "pps": 0.0
        }
      ],
      "blocked": []
    }
  }
}
```
`n## dump-flows до блокировки
```
OFPST_FLOW reply (OF1.3) (xid=0x2):
 cookie=0x53444e2026, duration=10.342s, table=0, n_packets=2, n_bytes=196, priority=100,ip,in_port=1,dl_dst=00:00:00:00:00:04,nw_src=10.0.0.1 actions=output:4
 cookie=0x53444e2026, duration=10.339s, table=0, n_packets=2, n_bytes=196, priority=100,ip,in_port=4,dl_dst=00:00:00:00:00:01,nw_src=10.0.0.4 actions=output:1
 cookie=0x0, duration=19.133s, table=0, n_packets=33, n_bytes=2622, priority=0 actions=CONTROLLER:65535
```

## dump-flows после блокировки
```
OFPST_FLOW reply (OF1.3) (xid=0x2):
 cookie=0x0, duration=8.988s, table=0, n_packets=195, n_bytes=19110, hard_timeout=10, priority=300,ip,nw_src=10.0.0.1 actions=drop
 cookie=0x53444e2026, duration=70.729s, table=0, n_packets=56, n_bytes=5488, priority=100,ip,in_port=1,dl_dst=00:00:00:00:00:04,nw_src=10.0.0.1 actions=output:4
 cookie=0x53444e2026, duration=70.726s, table=0, n_packets=61, n_bytes=5978, priority=100,ip,in_port=4,dl_dst=00:00:00:00:00:01,nw_src=10.0.0.4 actions=output:1
 cookie=0x0, duration=79.520s, table=0, n_packets=45, n_bytes=3350, priority=0 actions=CONTROLLER:65535
```
