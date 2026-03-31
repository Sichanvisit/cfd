# R0-B Actual Entry Forensic 상세 기준 문서

작성일: 2026-03-29 (KST)

## 1. 목적

이 문서는 `R0-B actual entry forensic`을 별도로 이해하기 위한 상세 기준 문서다.

중요한 점은 R0-B가 새로운 독립 phase가 아니라,
이미 완료된 R0 기준선을
`최근 실제 adverse entry 문제`에 다시 연결하는
현재형 하위 단계라는 것이다.

관련 문서:

- [refinement_r0_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_detailed_reference_ko.md)
- [refinement_r0_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_execution_roadmap_ko.md)
- [external_advice_synthesis_and_master_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\external_advice_synthesis_and_master_roadmap_ko.md)
- [thread_restart_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\thread_restart_handoff_ko.md)
- [consumer_coupled_check_entry_scene_refinement_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_scene_refinement_roadmap_ko.md)


## 2. R0-B를 한 문장으로 말하면

R0-B는
`실제로 들어간 뒤 바로 역행하거나 짧게 손실 청산된 entry`를
R0 언어로 다시 읽어서
어느 gate, guard, wait, consumer stage, 또는 exit timing에서 문제가 시작됐는지
설명 가능한 forensic 단계다.


## 3. 왜 별도 문서가 필요한가

R0 전체 문서는 넓다.
owner separation, non-action taxonomy, key linkage, canary 같은 바닥 규칙을 다룬다.

반면 R0-B는 매우 좁고 실전적이다.

- 최근 체결 기준 adverse entry를 본다
- 실제 진입 row를 다시 읽는다
- display나 체감이 아니라 `체결과 row 연결`을 본다
- 수정 후보를 바로 entry gate/guard 수준까지 내린다

즉 R0는 기준선 문서이고,
R0-B는 그 기준선을 현재 문제에 적용하는 문서다.


## 4. R0-B의 대상과 비대상

### 4-1. 대상

- 자동진입이 실제로 발생한 케이스
- 진입 직후 1~N bar 안에 adverse move가 크게 나온 케이스
- 짧은 보유 후 손실 청산된 케이스
- 사용자가 체감상 "들어가자마자 반대로 간다"고 느낀 케이스

### 4-2. 비대상

- chart 상 READY 과표시 자체의 미관 문제
- must-show / must-hide display 조정 자체
- symbol balance 체감 튜닝 자체
- expectancy/attribution 전체 집계
- drift, health, adaptation 같은 상위 운영 과제

즉 R0-B는
`실제로 잘못 열린 듯한 entry`를 추적하는 데 집중한다.


## 5. R0-B가 답해야 하는 질문

R0-B는 아래 질문에 답하는 단계다.

1. 이 entry는 어떤 `setup_id / observe_reason / consumer_check_stage`에서 열렸는가
2. entry 직전 row는 정말 들어가도 되는 상태였는가
3. `probe -> confirm -> entry`가 너무 빨랐는가
4. `gate/guard 누수`가 있었는가
5. 사실 entry 문제가 아니라 exit timing 문제였는가

핵심은 "손실이 났다"가 아니라
`손실이 난 이유가 entry quality 문제인지`
`wait/guard 누수인지`
`exit timing 착시인지`
를 분리하는 것이다.


## 6. 기본 읽기 순서

R0-B에서 adverse entry 1건을 볼 때 기본 읽기 순서는 아래와 같다.

1. 실제 체결 사실 확인
2. 직전 `entry_decisions.csv` row 매칭
3. `observe_reason / blocked_by / action_none_reason`
4. `quick_trace_state`, `entry_probe_plan_v1`, `consumer_check_stage`
5. `r0_non_action_family`, `r0_semantic_runtime_state`, `r0_row_interpretation_v1`
6. `trade_link_key / decision_row_key / runtime_snapshot_key / replay_row_key`
7. 진입 직후 adverse move와 보유 시간 확인
8. family 가설 작성

즉 R0-B는
바로 "이 전략이 나쁘다"로 가지 않고,
`행동 직전 row의 구조와 실제 체결 사실`을 먼저 묶는다.


## 7. 핵심 입력 데이터

### 7-1. 실제 체결 소스

- closed trade history
- 짧은 보유 후 손실 청산된 trade
- 필요 시 open snapshot / runtime status

### 7-2. 직전 decision row 소스

- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)

### 7-3. 현재 row 해석 보조 필드

- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`
- `replay_row_key`
- `r0_non_action_family`
- `r0_semantic_runtime_state`
- `r0_row_interpretation_v1`

R0-B는 기존 R0 해석 필드에 더해,
이번에 코드에 들어간 `r0_*` 필드를 바로 활용하는 첫 단계다.


## 7-4. 현재 구현 상태와 테스트 기준선

현재까지 구현 완료된 범위:

- `R0-B1 sample extractor`
- `R0-B2 decision row matcher`
- `R0-B3 forensic table normalizer`
- `R0-B4 family clustering`
- `R0-B5 action candidate derivation`

구현 파일:

- [r0_b_actual_entry_forensic_samples.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_samples.py)
- [r0_b_actual_entry_forensic_match_rows.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_match_rows.py)
- [r0_b_actual_entry_forensic_table.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_table.py)
- [r0_b_actual_entry_forensic_families.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_families.py)
- [r0_b_actual_entry_forensic_actions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_actions.py)

최근 보정 구현:

- `runtime_snapshot_key` zero-anchor fallback 보정
- generic runtime exact downgrade
- `detail sidecar history` reader 추가

테스트 파일:

- [test_r0_b_actual_entry_forensic_samples.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_samples.py)
- [test_r0_b_actual_entry_forensic_match_rows.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_match_rows.py)
- [test_r0_b_actual_entry_forensic_table.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_table.py)
- [test_r0_b_actual_entry_forensic_families.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_families.py)
- [test_r0_b_actual_entry_forensic_actions.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_actions.py)

현재 테스트 기준선:

- `R0-B2` 단위 테스트: `9 passed`
- `R0-B3` 단위 테스트: `4 passed`
- `R0-B4` 단위 테스트: `3 passed`
- `entry_service / consumer guard` 타겟 테스트: `97 passed`
- `storage_compaction / entry_engines` 타겟 테스트: `31 passed`
- 전체 unit: `1106 passed`

기존에 남아 있던
[test_energy_observe_engine.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_energy_observe_engine.py)
의 observe/confirm routing 이슈도 해결되어,
현재 unit 기준선은 전부 green 상태다.

현재 실행 결과에서 확인된 중요한 패턴:

- `fallback` 매칭은 coverage 안에서 잘 작동한다.
- 반면 `exact_runtime_snapshot_key` 매칭은
  `runtime_signal_row_v1|...|anchor_value=0.0` 형태의 generic key로 여러 건이 묶이는 패턴이 있다.
- 따라서 B2 결과를 읽을 때는
  `exact`라고 해서 모두 동일 품질로 믿지 말고,
  `generic runtime snapshot linkage` 여부를 함께 봐야 한다.
- 이후 source-side 보정과 matcher-side generic exact downgrade를 적용했다.
- 수정 후 B2 결과는
  `sample 30 / matched 7 / exact 0 / fallback 7 / unmatched 23`이다.
- detail history reader를 붙인 뒤에도
  coverage earliest는 `2026-03-27T15:29:43`에서 더 내려가지 않았다.
- 이후 archive-aware matcher까지 추가해
  향후 parquet archive와 archive manifest time range도
  forensic source로 읽을 수 있게 했다.
- 하지만 현재 workspace에는
  `data/trades/archive/entry_decisions` 아래 실제 parquet source가 없어서,
  coverage earliest는 여전히 `2026-03-27T15:29:43`에 머문다.
- 즉 현재 남은 `unmatched 23`은
  forensic reader 한계라기보다
  현재 source retention/backfill 부재로 해석하는 편이 맞다.
- B3 정규화 결과는
  `coverage_gap 23`,
  `fallback_match 7`,
  `suspicious_exact_runtime_linkage 0`으로 바뀌었다.
- alignment 기준으로는
  `unknown 23`,
  `row_says_not_ready 7`로 정리된다.
- B4 family clustering 결과,
  이 30건은
  `decision_log_coverage_gap 23`,
  `consumer_stage_misalignment 3`,
  `guard_leak 2`,
  `probe_promoted_too_early 2`
  로 묶인다.
- 즉 현재 최우선은
  generic runtime exact를 더 경계하는 것이 아니라
  `decision log coverage retention` 자체를 메우는 것이다.
- 이 coverage 축의 코드 준비는
  active/legacy/detail/archive-aware read와
  rollover manifest time range 기록까지 완료됐다.
- 따라서 남은 일은 구현 부족보다는
  실제 archive 생성/운영과 필요한 경우 historical backfill 확보 쪽이다.
- 별도로 rank 2였던 `consumer_stage_misalignment`에 대해서는
  코드 첫 패스를 이미 적용했다.
  - [consumer_check_state.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
    에 `consumer_open_guard_v1` 계약 추가
  - [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
    에 order submit 직전 hard-stop 추가
  - [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
    에 runtime snapshot trace 보강
- rank 3였던 `guard_leak`에 대해서도
  코드 첫 패스를 적용했다.
  - [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
    에 `entry_blocked_guard_v1` 추가
  - `forecast_guard / outer_band_guard / barrier_guard / middle_sr_anchor_guard`
    및 `observe_state_wait / confirm_suppressed / execution_soft_blocked`
    류 사유가 action과 함께 남아 있으면 submit 직전 차단
  - 단, `probe_promotion_gate` 같은 probe 흐름은
    그대로 유지되도록 strict guard set으로 범위를 제한
- rank 4였던 `probe_promoted_too_early`에 대해서도
  코드 첫 패스를 적용했다.
  - [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
    에 `probe_promotion_guard_v1` 추가
  - `entry_probe_plan_v1.ready_for_entry=false`,
    `probe_not_promoted`,
    `upper_reject_probe_observe / lower_rebound_probe_observe`,
    `quick_trace_state=PROBE` 계열 조합에서
    consumer state가 약해도 order submit 직전 `probe_promotion_gate`로 차단
  - 즉 rank 2가 `consumer contract`, rank 3이 `strict blocked_by`, rank 4가
    `probe promotion not-ready` 자체를 막는 보강 역할을 맡는다
- 즉 현재는 `decision_log_coverage_gap`은 운영/보존 문제로 남고,
  `consumer_stage_misalignment`, `guard_leak`, `probe_promoted_too_early`는
  코드상 기본 hard-stop이 들어간 상태다.
- B5 action candidate 결과,
  실제 수정 우선순위는
  `decision_log_coverage_gap`,
  `consumer_stage_misalignment`,
  `guard_leak`,
  `probe_promoted_too_early`
  순으로 정리된다.
- 즉 현재 단계의 결론은
  "전략을 더 조이자"가 아니라
  "forensic truth를 먼저 믿을 수 있게 만들고,
   그 다음 entry leakage를 고친다"이다.


## 8. 최소 forensic 테이블 컬럼

R0-B 표준 테이블은 최소한 아래 열을 가져야 한다.

| 열 | 의미 |
|---|---|
| `symbol` | 심볼 |
| `time` | decision 또는 entry 시각 |
| `setup_id` | setup naming |
| `action` | 실제 action |
| `outcome` | entered / wait / exit 관련 결과 |
| `observe_reason` | semantic 문맥 |
| `blocked_by` | 즉시 차단 원인 |
| `action_none_reason` | non-action 결과 라벨 |
| `quick_trace_state` | quick state |
| `quick_trace_reason` | quick reason |
| `probe_plan_ready` | probe 승격 준비 여부 |
| `consumer_check_stage` | consumer stage |
| `consumer_check_entry_ready` | consumer entry readiness |
| `r0_non_action_family` | R0 family |
| `r0_semantic_runtime_state` | LIVE/FALLBACK/INACTIVE 등 |
| `decision_row_key` | reason-bearing row key |
| `runtime_snapshot_key` | runtime linkage key |
| `trade_link_key` | 체결 linkage key |

추가 권장 열:

- `entry_price`
- `exit_price`
- `hold_seconds`
- `mae_before_exit`
- `mfe_before_exit`
- `exit_reason`


## 9. R0-B에서 쓰는 대표 family 가설

R0-B는 아직 최종 원인 판정을 자동화하지 않는다.
대신 아래와 같은 가설 family로 묶는다.

| family 가설 | 의미 |
|---|---|
| `probe_promoted_too_early` | probe 단계에서 ready 승격이 너무 빨랐다 |
| `confirm_quality_too_weak` | confirm처럼 보였지만 persistence/quality가 약했다 |
| `guard_leak` | 막혀야 할 장면이 guard를 통과했다 |
| `consumer_stage_misalignment` | consumer check와 실제 entry가 어긋났다 |
| `exit_not_entry_issue` | 문제의 중심이 entry가 아니라 exit timing이었다 |

이 family는 최종 truth가 아니라
코드 수정 후보를 좁히기 위한 forensic 분류다.


## 10. 코드 owner

R0-B와 직접 맞닿는 핵심 파일은 아래와 같다.

- [r0_row_interpretation.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\r0_row_interpretation.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [consumer_check_state.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

역할 구분은 아래처럼 본다.

- `r0_row_interpretation.py`: row 해석 계약
- `storage_compaction.py`: runtime/hot payload surface
- `entry_service.py`: observe/block/non-action source owner
- `entry_try_open_entry.py`: 실제 주문 오픈 시점 행동 owner
- `consumer_check_state.py`: consumer stage 해석 owner
- `chart_painter.py`: display 비교 참고용, forensic truth owner는 아님


## 11. 현재 구현 상태

2026-03-29 기준 현재 상태는 아래와 같다.

- `r0_non_action_family`
- `r0_semantic_runtime_state`
- `r0_row_interpretation_v1`

이 세 필드가 compact/runtime/hot row에 추가되었다.

관련 코드:

- [r0_row_interpretation.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\r0_row_interpretation.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)

테스트 기준:

- targeted R0 인접 테스트 통과
- 전체 unit suite: `1106 passed`

남은 1건 실패는
R0-B 자체를 막는 red test는 현재 없다.

- [test_energy_observe_engine.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_energy_observe_engine.py)


## 12. R0-B 완료 기준

R0-B가 끝났다고 보려면 아래가 가능해야 한다.

1. 최근 adverse entry 3건 이상을 같은 테이블 형식으로 읽을 수 있다
2. 최소 1개 이상의 공통 family를 설명 가능하다
3. "entry gate 문제"와 "exit timing 문제"를 구분할 수 있다
4. 수정해야 할 owner 파일 후보를 1차로 좁힐 수 있다


## 13. 한 줄 결론

R0-B는 새로운 phase가 아니라,
이미 만든 R0 기준선을
`실제로 잘못 열린 entry를 추적하는 현재형 forensic 단계`
로 다시 사용하는 것이다.


## 14. close-out과 다음 단계

R0-B 자체의 close-out 정리는 아래 문서에 고정한다.

- [refinement_r0_b6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b6_close_out_handoff_ko.md)

R0-B 이후 즉시 다음 1순위는 아래 문서군으로 이어진다.

- [decision_log_coverage_gap_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_detailed_reference_ko.md)
- [decision_log_coverage_gap_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_execution_roadmap_ko.md)

즉 현재 단계의 결론은
`forensic family를 더 늘리는 것`이 아니라,
`coverage 바깥 trade를 어떻게 archive/backfill로 다시 coverage 안으로 가져올 것인가`
로 넘어간다는 뜻이다.
