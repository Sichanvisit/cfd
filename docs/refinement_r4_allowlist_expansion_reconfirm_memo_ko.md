# R4 Allowlist Expansion Reconfirm Memo

## 1. 요약

`NAS100 allowlist expansion within threshold_only`는 실제로 반영됐다.

현재 semantic live allowlist는:

- `BTCUSD`
- `NAS100`

이다.

즉 R4 문서에서 정리한
`다음 허용 가능한 변화는 NAS100 allowlist 확장`
은 실제 설정 변경까지 진행된 상태다.

## 2. 반영 위치

- 설정 owner: [config.py](c:\Users\bhs33\Desktop\project\cfd\backend\core\config.py)
- 적용 owner: [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)
- runtime surface: [trading_application.py](c:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- 실제 설정 파일: [\.env](c:\Users\bhs33\Desktop\project\cfd\.env)

변경 내용:

- `SEMANTIC_LIVE_SYMBOL_ALLOWLIST=BTCUSD`
- `SEMANTIC_LIVE_SYMBOL_ALLOWLIST=BTCUSD,NAS100`

## 3. 재시작 후 확인

기준 파일:

- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)

재시작 후 확인된 값:

- `semantic_live_config.symbol_allowlist = ["BTCUSD", "NAS100"]`

최근 runtime recent entry 기준:

### BTCUSD

- fallback: `baseline_no_action`

### NAS100

- fallback: `baseline_no_action`

### XAUUSD

- fallback: `symbol_not_in_allowlist`

핵심 변화:

- NAS100은 더 이상 `symbol_not_in_allowlist`로 막히지 않는다.
- 즉 allowlist gate는 실제로 풀렸고,
  이제 NAS100의 병목은 운영 정책이 아니라 baseline / runtime no-action 쪽이다.

## 4. 운영 해석

이 변경은 `partial_live` 진입이 아니다.

현재 상태는 여전히:

- mode = `threshold_only`
- canary = `hold`
- chart rollout = `hold`

이다.

즉 운영 해석은 아래가 맞다.

- `threshold_only 유지`
- `NAS100 allowlist 확장 완료`
- `다음 확장 후보는 XAUUSD`
- `partial_live는 아직 보류`

## 5. 결론

R4의 다음 상태는 이제 이렇게 읽는다.

- current anchor: `BTCUSD`
- expanded observation symbol: `NAS100`
- next candidate: `XAUUSD`
- current action: `threshold_only 유지 + BTCUSD/NAS100 allowlist`
