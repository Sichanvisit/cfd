# PA0 Refreeze After PA4 Countertrend Topdown Exit Context Fast-Exit Bias Fresh Close Watch Follow-Up

## watch 결과

`2026-04-01 20:49:28`부터 약 3분 동안 closed history를 지켜본 결과 fresh close는 실제로 더 들어왔다.

변화:

- start: `row_count=8446`, `max_close_time=2026-04-01 20:48:19`
- end: `row_count=8448`, `max_close_time=2026-04-01 20:52:06`

대표 fresh row:

- `104268596 / XAUUSD / 2026-04-01 20:44:40 / Protect Exit ... hard_guard=adverse | adverse_peak=weak`
- `104270815 / NAS100 / 2026-04-01 20:50:36 / Protect Exit ... hard_guard=adverse | adverse_peak=weak`
- `104271356 / XAUUSD / 2026-04-01 20:52:06 / Protect Exit ... hard_guard=adverse`

## refreeze 결과

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T20:52:46`

summary:

- `must_hold = 0`
- `must_release = 10`
- `bad_exit = 10`

즉 이번 watch 이후에도 exit queue 총량은 그대로다.

## 해석

중요한 점은 이번 fresh close들이 queue 안에 직접 잡히지 않았다는 것이다.

확인한 fresh ticket:

- `104268596`
- `104270815`
- `104271356`

이 ticket들은 latest `must_release / bad_exit` seed queue에 나타나지 않았다.

즉:

- 새 weak-peak adverse row는 current policy 기준으로 이미 queue 밖으로 빠지고 있고
- 현재 `must_release / bad_exit 10`은 여전히 오래된 backlog 비중이 크다

## 결론

- `watch + refreeze`는 유효했다
- immediate numeric drop은 아직 없었다
- 하지만 fresh-close 쪽에선 새 패치가 queue 확산을 막고 있다는 근거가 추가됐다
- 다음 확인은 backlog turnover가 더 진행된 뒤 같은 `10`이 실제로 줄기 시작하는지 보는 단계다
