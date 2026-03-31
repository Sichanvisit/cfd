# Semantic Shadow 재기동 체크리스트

## 목적

새 semantic shadow 모델을 [`models/semantic_v1`](/C:/Users/bhs33/Desktop/project/cfd/models/semantic_v1)에 올린 뒤,
실제 앱 재기동 후 첫 30분 동안 무엇을 확인해야 하는지 고정한다.

이 체크리스트의 목적은 두 가지다.

1. `semantic_shadow_loaded=true`가 실제 런타임에서도 유지되는지 확인
2. 새 row에 `semantic_shadow_*`, `semantic_live_*`가 정상 기록되는지 확인

## 지금 기준 상태

- shadow 모델 번들 승격 완료
- preview audit 기준 `shadow_compare_ready=true`
- canary 모드
  - `SEMANTIC_LIVE_ROLLOUT_MODE=threshold_only`
  - `SEMANTIC_LIVE_SYMBOL_ALLOWLIST=BTCUSD`
  - `SEMANTIC_LIVE_ENTRY_STAGE_ALLOWLIST=aggressive`

## 먼저 볼 파일

- [`data/runtime_status.json`](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)
- [`data/manifests/rollout/semantic_live_rollout_latest.json`](/C:/Users/bhs33/Desktop/project/cfd/data/manifests/rollout/semantic_live_rollout_latest.json)
- [`data/trades/entry_decisions.csv`](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
- [`data/analysis/semantic_canary/semantic_canary_rollout_BTCUSD_latest.md`](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/semantic_canary/semantic_canary_rollout_BTCUSD_latest.md)
- [`data/manifests/rollout/semantic_shadow_promotion_latest.json`](/C:/Users/bhs33/Desktop/project/cfd/data/manifests/rollout/semantic_shadow_promotion_latest.json)

## 0~5분 체크

### 1. runtime status 기본 확인

아래가 바로 보여야 정상이다.

- `semantic_shadow_loaded = true`
- `semantic_shadow_config.available_targets = ["timing", "entry_quality", "exit_management"]`
- `semantic_live_config.mode = "threshold_only"`
- `semantic_live_config.symbol_allowlist = ["BTCUSD"]`
- `semantic_live_config.entry_stage_allowlist = ["aggressive"]`

### 2. 오래된 상태 파일인지 확인

[`data/runtime_status.json`](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)의 `updated_at`이
재기동 직후 현재 시각 근처로 갱신돼야 한다.

실패 신호:

- `updated_at`이 예전 시각 그대로
- `semantic_shadow_loaded=false`
- `available_targets=[]`

## 5~15분 체크

### 3. 새 decision row에 semantic 필드가 찍히는지 확인

[`data/trades/entry_decisions.csv`](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)에서
재기동 이후 새 row 기준으로 아래 컬럼이 채워져야 한다.

- `semantic_shadow_available`
- `semantic_shadow_timing_probability`
- `semantic_shadow_entry_quality_probability`
- `semantic_shadow_should_enter`
- `semantic_shadow_compare_label`
- `semantic_shadow_reason`
- `semantic_live_rollout_mode`
- `semantic_live_fallback_reason`
- `semantic_live_threshold_applied`

### 4. BTCUSD canary row가 실제로 잡히는지 확인

최소한 일부 row에서 아래 중 하나는 보여야 정상이다.

- `semantic_live_rollout_mode = threshold_only`
- `semantic_live_fallback_reason = entry_stage_not_in_allowlist`
- `semantic_live_fallback_reason = baseline_no_action`
- `semantic_live_fallback_reason = timing_probability_too_low`
- `semantic_live_fallback_reason = entry_quality_probability_too_low`
- `semantic_live_fallback_reason = semantic_unavailable`

중요한 건 `fallback_reason` 값이 비어 있지 않게 남는 것이다.

## 15~30분 체크

### 5. rollout manifest가 증가하는지 확인

[`data/manifests/rollout/semantic_live_rollout_latest.json`](/C:/Users/bhs33/Desktop/project/cfd/data/manifests/rollout/semantic_live_rollout_latest.json)에서
아래 값이 0에서 움직여야 한다.

- `entry.events_total`
- `entry.alerts_total`
- `entry.fallback_total`
- `entry.threshold_applied_total`

### 6. canary 리포트 재생성

```powershell
python scripts\check_semantic_canary_rollout.py --symbol BTCUSD --hours 48 --max-rows 4000
```

그 다음 [`data/analysis/semantic_canary/semantic_canary_rollout_BTCUSD_latest.md`](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/semantic_canary/semantic_canary_rollout_BTCUSD_latest.md)를 본다.

## 30분 안에 보는 핵심 숫자

### 최소 합격선

- `recent_rows >= 50`
- `runtime_status.semantic_shadow_loaded = true`
- `rollout.entry.events_total > 0`
- `entry_decisions.csv` 새 row에서 `semantic_shadow_*`가 비어 있지 않음

### 계속 관찰 가능

- `fallback_ratio < 0.90`
- `threshold_applied_ratio > 0.00`
- `semantic_unavailable`가 주된 fallback reason이 아님

### 멈춰야 하는 신호

- `semantic_shadow_loaded=false`로 다시 떨어짐
- 새 row에서도 `semantic_shadow_available=0`만 계속 찍힘
- `semantic_live_rollout_mode`가 새 row에서 계속 비어 있음
- `semantic_unavailable`가 주된 reason으로 계속 반복
- `recent_rows`가 쌓이는데 `events_total=0` 유지

## 지금 단계에서 정상으로 볼 수 있는 fallback

아래는 실패가 아니라 초기 canary에서 충분히 나올 수 있는 정상 신호다.

- `entry_stage_not_in_allowlist`
- `baseline_no_action`
- `timing_probability_too_low`
- `entry_quality_probability_too_low`

즉 초반엔 `threshold_applied`가 적더라도, `semantic_unavailable`만 아니면 연결은 살아 있다고 본다.

## 즉시 중단 기준

아래면 canary를 바로 끄는 쪽이 안전하다.

- 에러로 앱이 반복 재기동됨
- `semantic_live_threshold_applied=1`가 급격히 많아짐
- BTCUSD 외 심볼에서 semantic live 적용 흔적이 보임
- `reason`이나 `fallback_reason`가 비정상 공백으로 계속 남음

## 즉시 복귀 방법

`.env` 기준으로 아래처럼 돌리면 된다.

- `SEMANTIC_LIVE_ROLLOUT_MODE=log_only`
- 또는 `SEMANTIC_LIVE_KILL_SWITCH=true`

재기동 후 [`data/runtime_status.json`](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)에서
`mode`, `kill_switch`, `semantic_shadow_loaded`를 다시 확인한다.

## 다음 판단 기준

아래면 `Phase 5-C` 검토 후보로 본다.

- `recent_rows >= 150`
- `fallback_ratio < 0.70`
- `threshold_applied_ratio >= 0.02`
- `semantic_unavailable`가 주된 fallback reason이 아님
- false positive 급증 흔적 없음

그 전까지는 `threshold_only` canary를 유지하면서 row를 더 쌓는다.
