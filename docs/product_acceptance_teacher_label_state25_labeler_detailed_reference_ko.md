# Teacher-Label State25 Labeler Detailed Reference

## 목적

이 문서는 `teacher_pattern_*` compact schema를 실제 값으로 채우는 첫 번째 룰 기반 라벨러의 기준을 고정한다.

이번 단계의 목적은 다음 3가지다.

1. 이미 문서화한 `state25 최종판 + threshold v2 + QA 기준`을 실제 row attach 로직으로 내린다.
2. `open snapshot -> open row -> closed-history compact row` 경로에서 teacher-pattern 값이 자동으로 채워지게 만든다.
3. Step 8 labeling QA와 Step 9 experiment tuning이 볼 수 있는 최소한의 primary / secondary / bias / confidence surface를 제공한다.

## 이번 단계의 성격

이번 라벨러는 `final execution engine`이 아니라 `rule_v2_draft` 성격의 초안이다.

- execution 룰을 직접 바꾸지 않는다.
- close 결과를 사용하지 않는다.
- look-ahead 정보는 사용하지 않는다.
- 현재 시점 snapshot에서 이미 존재하는 값만 사용한다.

즉 이 단계는 `teacher-label first-pass attach` 단계다.

## owner

- rule owner:
  - [teacher_pattern_labeler.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeler.py)
- attach owner:
  - [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py)

## 입력 범위

이번 초안 라벨러는 아래 입력만 사용한다.

- micro semantic state
  - `micro_breakout_readiness_state`
  - `micro_reversal_risk_state`
  - `micro_participation_state`
  - `micro_gap_context_state`
- micro numeric state
  - `micro_body_size_pct_20`
  - `micro_doji_ratio_20`
  - `micro_same_color_run_current`
  - `micro_same_color_run_max_20`
  - `micro_range_compression_ratio_20`
  - `micro_volume_burst_ratio_20`
  - `micro_volume_burst_decay_20`
  - `micro_gap_fill_progress`
- optional richer micro input when already present in snapshot
  - `micro_upper_wick_ratio_20`
  - `micro_lower_wick_ratio_20`
  - `micro_swing_high_retest_count_20`
  - `micro_swing_low_retest_count_20`
- existing entry context
  - `direction`
  - `entry_setup_id`
  - `entry_session_name`
  - `entry_wait_state`
  - `prediction_bundle`

## attach 규칙

1. snapshot에 이미 `teacher_pattern_id` 또는 `teacher_pattern_name`이 있으면 라벨러는 덮어쓰지 않는다.
2. 명시 teacher 값이 비어 있으면 `rule_v2_draft`가 primary / secondary / bias / confidence를 채운다.
3. attach는 open snapshot 단계에서 수행한다.
4. 이후 open row -> closed row carry는 기존 compact pipeline을 그대로 따른다.

## unlabeled 규칙

- top score가 충분히 높지 않으면 row를 강제로 25개 중 하나에 넣지 않는다.
- 이 경우 `teacher_pattern_*`는 비워 둔다.
- 강제 분류보다 `unlabeled`가 낫다는 원칙을 유지한다.

## primary / secondary 규칙

- `primary`: 최고 점수 패턴
- `secondary`: 2위 점수가 충분히 높고 top1과 차이가 작을 때만 부여

초안 규칙:

- primary minimum score: `0.50`
- secondary minimum score: `0.48`
- top1 - top2 gap: `<= 0.10`

## provenance 규칙

이번 초안 라벨러가 붙인 값은 아래 provenance를 사용한다.

- `teacher_label_version = state25_v2`
- `teacher_label_source = rule_v2_draft`
- `teacher_label_review_status = unreviewed`
- `teacher_lookback_bars = 20`

## 이번 초안에서 우선 잘 잡으려는 패턴

이번 초안은 25개 전체를 커버하되, 특히 아래 계열을 안정적으로 잡는 것을 우선 목표로 한다.

- `12 브레이크아웃 직전`
- `23 삼각수렴 압축`
- `5 Range 반전장`
- `22 더블탑/바텀`
- `21 갭필링 진행장`
- `15 캔들 연속 패턴`
- `17 거래량 폭발장`
- `20 엔진 꺼짐장`

이유는 현재 micro field와 semantic state만으로도 이 축이 상대적으로 판별력이 높기 때문이다.

## 이번 단계 비목표

이번 라벨러는 아직 아래를 하지 않는다.

- confidence calibration 학습
- execution bias 직접 반영
- QA score field의 canonical 저장
- confusion matrix 기반 threshold 재튜닝

그건 Step 8, Step 9에서 다룬다.

## 결론

이번 단계는 `state25 기준 문서 -> compact schema -> rule-based first label attach`로 내려오는 첫 구현이다.

즉 지금부터는

1. schema만 있는 상태가 아니라
2. 실제 row에 teacher-pattern이 붙기 시작하고
3. 그 결과를 QA와 experiment 단계에서 검수하는 구조로 넘어간다.
