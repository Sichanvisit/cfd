# P4 Log-Only Detector Detailed Plan

## 목표

`scene / candle-weight / reverse` 축에서 반복되는 실패 패턴을 바로 적용하지 않고,
먼저 `관찰(OBSERVE) -> 보고(report topic) -> 체크(check topic)`로 surface한다.

## 이번 버전 범위

- 자동 승인 없음
- 자동 patch apply 없음
- `/detect` 수동 명령으로만 실행
- detector 결과는 모두 `log-only` 관찰 보고서로만 생성

## detector 1. scene-aware

### 입력

- `data/runtime_status.json`
- `semantic_rollout_state.recent`

### 이번 버전 규칙

- `domain=entry`
- `mode=log_only`
- `trace_quality_state in {unavailable, missing, degraded}`
- 동일 `symbol + trace_quality_state + fallback_reason` 반복 3회 이상

### surface 결과

- `summary_ko`
- `why_now_ko`
- `recommended_action_ko`
- evidence line 3개 이내

## detector 2. candle / weight

### 입력

- 최근 closed trade
- 기존 `/propose` 집계 결과

### 이번 버전 규칙

- surfaced problem pattern 중 표본 5건 이상만 detector surface
- raw 변수명 대신 한국어 설명 사용
- `upper/reject/wick` 계열이면 `upper_wick_weight` preview
- `lower/rebound/reclaim` 계열이면 `lower_wick_weight` preview
- `doji` 계열이면 `doji_weight` preview
- 그 외는 `candle_body_weight` preview

### 원칙

- 실제 approval loop로 바로 보내지 않음
- `STATE25_WEIGHT_PATCH_REVIEW`는 preview payload로만 포함

## detector 3. reverse pattern

### 입력

- `runtime_status.pending_reverse_by_symbol`

### 이번 버전 규칙

- 동일 symbol pending reverse에서 `reason_count >= 3`
- pending action / age / expires_in 을 같이 노출

### 원칙

- 단순 blocked 상태는 readiness surface에서 본다
- detector는 반복 pending pattern만 본다

## false positive 제어

- `scene-aware`: 하루 최대 3건
- `candle-weight`: 하루 최대 5건
- `reverse`: 하루 최대 2건
- 총합 최대 10건

## Telegram 흐름

### 명령

- `/detect`
- `/detect 50`

### report topic

- 원문 detector 보고서 1회 발송
- stage / readiness / detector별 상세 내용 포함

### check topic

- 짧은 inbox summary만 발송

## 산출물

- `data/analysis/shadow_auto/improvement_detector_policy_baseline_latest.json`
- `data/analysis/shadow_auto/improvement_log_only_detector_latest.json`

## 완료 조건

- `/detect` 호출 시
  - report topic에 detector 보고서가 간다
  - check topic에 요약이 간다
  - detector별 cap과 최소 표본 기준이 지켜진다
  - approval/apply는 자동으로 일어나지 않는다

## 건드린 파일

- `backend/services/improvement_detector_policy.py`
- `backend/services/improvement_log_only_detector.py`
- `backend/services/telegram_ops_service.py`
- `tests/unit/test_improvement_detector_policy.py`
- `tests/unit/test_improvement_log_only_detector.py`
- `tests/unit/test_telegram_ops_service_p4.py`
