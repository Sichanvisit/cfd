# P4 Detector Input Broadening

## 목표

기존 `log-only detector`가 `semantic trace missing` 한 종류만 보는 느낌에서 벗어나,
실제로 사용자가 체감하는 이상 징후를 더 넓게 surface하도록 입력선을 보강한다.

## 이번 보강 범위

### 1. scene-aware detector

기존:
- `runtime_status.semantic_rollout_state.recent`
- `trace_quality_state = unavailable/missing/degraded`

추가:
- `checkpoint_scene_disagreement_audit_latest.json`
  - `summary.label_pull_profiles`
  - `watch_state`
  - `top_slices`
- `checkpoint_trend_exhaustion_scene_bias_preview_latest.json`
  - `summary.preview_changed_row_count`
  - `summary.improved_row_count`
  - `summary.worsened_row_count`
  - `summary.top_changed_slices`

이제 scene detector는 아래를 함께 본다.
- semantic trace 누락 반복
- label pull / disagreement 반복
- trend exhaustion preview changed

### 2. reverse detector

기존:
- `runtime_status.pending_reverse_by_symbol`

추가:
- 최근 closed trade의 `shock_score / shock_reason / shock_action`

현재 missed reverse 후보로 읽는 조건:
- `shock_score >= 15`
- `shock_reason`에 `opposite_score_spike` 또는 `adverse_risk`
- 또는 `shock_action`에 `downgrade_to_mid / force_exit_candidate / hold`
- 동일 symbol 반복 3건 이상

즉 이제 reverse detector는
- `pending reverse`
- `shock 기반 missed reverse`
두 축을 함께 본다.

### 3. candle / weight detector

기존:
- `/propose`의 `surfaced_problem_patterns`만 사용

추가:
- `surfaced_problem_patterns`가 비거나 부족할 때
- `problem_patterns`에서 `trade_count >= 5` 및 `net_pnl < 0` 패턴 fallback

즉 이제 candle detector는
- 이미 확실한 문제 패턴
- 아직 observe 단계지만 누적 손실이 있는 overweight 패턴
둘 다 log-only preview로 끌어올린다.

## 운영 원칙

- 여전히 `OBSERVE` 전용이다.
- 자동 승인/자동 반영은 없다.
- check topic / report topic으로만 surface한다.
- detector별 cap과 최소 반복 표본은 그대로 유지한다.

## 현재 live snapshot 기준

- scene surfaced: 3건
  - `trend_exhaustion 장면 불일치 반복 관찰`
  - `BTCUSD scene trace 누락 반복 감지`
  - `trend exhaustion preview changed 관찰`
- reverse surfaced: 2건
  - `XAUUSD missed reverse / shock 패턴 관찰`
  - `BTCUSD missed reverse / shock 패턴 관찰`
- candle surfaced: 0건
  - 최근 50건 기준 즉시 surface할 candle overweight 패턴은 아직 없음

## 해석

이번 보강으로 detector는
`scene disagreement / missed reverse / candle overweight`
를 더 넓게 볼 수 있게 되었고,
여전히 적용은 하지 않은 채 `log-only observation lane`으로만 움직인다.
