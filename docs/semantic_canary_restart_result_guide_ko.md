# Semantic Canary 재시작 후 결과 해석표

## 목적

`main.py` 재시작 후 BTC canary 결과를 빠르게 해석하기 위한 기준표다.

주로 아래 2개를 같이 본다.

- [`data/analysis/semantic_canary/semantic_canary_rollout_BTCUSD_latest.md`](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/semantic_canary/semantic_canary_rollout_BTCUSD_latest.md)
- [`data/trades/entry_decisions.csv`](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)

## 먼저 볼 값

### canary 요약

- `recent_rows`
- `shadow_available_rows`
- `fallback_ratio`
- `threshold_applied_ratio`
- `Fallback Reasons`

### decision row

- `semantic_shadow_available`
- `semantic_live_fallback_reason`
- `semantic_live_threshold_applied`
- `blocked_by`
- `action`
- `outcome`

## 해석표

### 1. 가장 좋은 시작 신호

- `shadow_available_rows > 0`
- `entry_stage_not_in_allowlist`가 사라짐
- `threshold_applied_rows > 0`

뜻:

- semantic 모델 연결 정상
- canary gate가 실제 평가 시작
- 이제 threshold 보정이 실제로 작동 중

다음 행동:

- BTC row를 더 쌓고 false positive가 늘지 않는지 관찰

### 2. 연결은 됐지만 아직 보정은 안 됨

- `shadow_available_rows > 0`
- `threshold_applied_rows = 0`
- fallback reason이 `timing_probability_too_low` 또는 `entry_quality_probability_too_low`

뜻:

- semantic은 붙었지만 확률 컷이 아직 높음
- 이건 정상적인 초기 상태일 수 있음

다음 행동:

- 바로 더 풀지 말고 20~50 row 더 관찰
- 계속 0이면 그때 확률 컷 완화 검토

### 3. semantic이 붙었지만 baseline이 후보를 거의 안 냄

- `semantic_live_fallback_reason = baseline_no_action` 비중 큼
- `action`이 대부분 빈값
- `outcome`이 대부분 `wait`

뜻:

- semantic이 나쁜 게 아니라 baseline이 BUY/SELL 후보를 거의 안 내는 상태
- 지금 진입 부족의 주범은 semantic보다 baseline guard일 가능성이 큼

다음 행동:

- `blocked_by` 상위 원인을 본다
- 특히 `forecast_guard`, `middle_sr_anchor_guard`, `range_lower_buy_*` 계열 확인

### 4. trace 품질 때문에 아직 막힘

- fallback reason이 `trace_quality_unknown`, `trace_quality_incomplete`, `trace_quality_fallback_heavy`

뜻:

- semantic 입력 품질이 아직 불안정
- 하지만 이번 설정에서는 `fallback_heavy`는 어느 정도 허용했으므로,
  계속 이게 뜨면 실제 trace 품질 보강이 필요

다음 행동:

- `runtime_status.json`과 detail 저장 흐름을 같이 확인
- trace/quality row가 왜 비는지 점검

### 5. 위험 신호

- `semantic_unavailable` 반복
- `shadow_available_rows = 0` 유지
- `semantic_shadow_available = 0`만 계속 찍힘

뜻:

- 모델 로드 또는 runtime 연결 문제

다음 행동:

- [`data/runtime_status.json`](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)에서
  `semantic_shadow_loaded`, `available_targets` 재확인
- 필요하면 `main.py` 재기동

### 6. 진입은 생기는데 너무 과하면 위험

- `threshold_applied_ratio`가 갑자기 큼
- `semantic_live_threshold_applied = 1`이 빠르게 늘어남
- `outcome=skipped`나 이상 진입이 급증

뜻:

- canary 완화가 너무 세게 먹었을 가능성

다음 행동:

- 즉시 `log_only` 또는 kill switch 검토

## 지금 단계에서 정상으로 볼 fallback

아래는 실패가 아니라 충분히 나올 수 있는 값이다.

- `baseline_no_action`
- `timing_probability_too_low`
- `entry_quality_probability_too_low`
- `trace_quality_fallback_heavy`

## 지금 단계에서 비정상으로 보는 값

- `entry_stage_not_in_allowlist`
  - 이번엔 allowlist를 비웠으니 이제 계속 나오면 이상
- `semantic_unavailable`
  - 새 shadow 모델이 붙은 상태라 반복되면 이상

## 아주 짧은 결론 기준

### 좋은 방향

- `shadow_available_rows` 증가
- `entry_stage_not_in_allowlist` 소멸
- fallback reason이 더 다양한 실제 판정 이유로 바뀜

### 다음 보정이 필요한 방향

- `baseline_no_action` 우세
  - baseline 진입 가드가 문제
- `timing_probability_too_low` 우세
  - timing 컷이 문제
- `entry_quality_probability_too_low` 우세
  - entry quality 컷이 문제

### 바로 중단할 방향

- `semantic_unavailable` 반복
- `threshold_applied` 급증과 이상 진입 동반

## 권장 확인 명령

```powershell
python scripts\check_semantic_canary_rollout.py --symbol BTCUSD --hours 12 --max-rows 4000
```

```powershell
Get-Item data\runtime_status.json, data\trades\entry_decisions.csv |
  Select-Object Name, LastWriteTime, Length
```
