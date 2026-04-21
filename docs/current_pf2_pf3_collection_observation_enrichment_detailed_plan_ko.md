# Current PF2 PF3 Collection Observation Enrichment Detailed Plan

## 목적

이 문서는 `PA6` 다음 단계에서 진행한

- `PF2 Exit-Manage Collection Enrichment`
- `PF3 Observation Upgrade`

구현 내용을 정리한 기록이다.

이번 턴의 목적은
규칙을 더 복잡하게 만드는 것이 아니라,
`open_loss`와 `runner_secured` family를 더 잘 수집하고
그 family가 실제로 늘고 있는지 observation에서 바로 보이게 만드는 것이었다.

---

## 이번에 실제로 바꾼 것

## 1. checkpoint context schema 확장

대상:

- [path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)

추가 필드:

- `giveback_from_peak`
- `giveback_ratio`
- `checkpoint_rule_family_hint`
- `exit_stage_family`

의도:

- 단순 score만으로는 안 보이는 `family 문맥`과 `giveback 문맥`을 row에 같이 남기기 위함

### 핵심 구현

- `build_exit_position_state(...)`
  - `giveback_usd` optional 인자 추가
  - explicit 값이 0이면 derived fallback을 사용
- `_resolve_exit_stage_family(...)`
  - `protective / runner / hold / backfill` 계열 분류
- `_resolve_checkpoint_rule_family_hint(...)`
  - `flat_checkpoint`
  - `runner_secured_continuation`
  - `open_loss_protective`
  - `active_open_loss`
  - `profit_hold_bias`
  - `active_flat_profit`

---

## 2. exit_manage final-stage row에 family hint 직접 주입

대상:

- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)

추가한 것:

- `_resolve_checkpoint_stage_family(...)`
- `_resolve_checkpoint_rule_family_hint(...)`

실제 반영:

- `_record_exit_manage_checkpoint(...)`에서
  - `exit_stage_family`
  - `checkpoint_rule_family_hint`
  를 runtime row에 직접 넣은 뒤 `record_checkpoint_context(...)`로 넘기게 변경

의도:

- `exit_manage_runner`, `exit_manage_hold`, `exit_manage_protective`가
  나중에 동일한 `management action` family로 해석되도록 연결하기 위함

---

## 3. open-trade backfill도 같은 family 체계로 정렬

대상:

- [path_checkpoint_open_trade_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_open_trade_backfill.py)

추가한 것:

- `_infer_backfill_stage_family(...)`
- `_infer_backfill_rule_family_hint(...)`

실제 반영:

- `exit_wait_decision_family`
- `exit_wait_bridge_status`
- `giveback_usd`
- `shock_at_profit`

를 이용해서 backfill row에도

- `exit_stage_family`
- `checkpoint_rule_family_hint`
- `giveback_from_peak`
- `giveback_ratio`

가 같이 남도록 변경

의도:

- live loop가 당장 비어도 open-trade snapshot만으로
  `open_loss / runner / hold-bias` family를 최대한 읽어오기 위함

---

## 4. observation artifact 강화

대상:

- [path_checkpoint_position_side_observation.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_position_side_observation.py)

새 summary/row 항목:

- `hold_candidate_row_count`
- `full_exit_candidate_row_count`
- `giveback_heavy_row_count`
- `family_counts`
- `latest_rule_family_hint`

새 recommended focus logic:

- `open_loss`가 없으면 `collect_more_*_open_loss_rows`
- `runner_secured`가 없으면 `collect_more_*_runner_secured_rows`
- hold candidate가 없으면 `inspect_*_hold_candidate_gap`

의도:

- “row 수”만이 아니라
  실제로 어떤 family가 부족한지 바로 보이게 만들기 위함

---

## 5. resolver / dataset이 새 메타데이터를 읽게 정렬

대상:

- [path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)
- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

반영:

- resolver feature builder가
  - `checkpoint_rule_family_hint`
  - `exit_stage_family`
  - `giveback_from_peak`
  - `giveback_ratio`
  를 직접 읽게 정렬

- dataset export에도
  - `giveback_from_peak`
  - `giveback_ratio`
  - `checkpoint_rule_family_hint`
  - `exit_stage_family`
  를 포함

의도:

- 다음 `HOLD / FULL_EXIT` refinement 때
  새 필드를 다시 연결하지 않아도 되게 하기 위함

---

## 테스트

실행:

- `python -m pytest tests/unit/test_path_checkpoint_context.py tests/unit/test_exit_manage_checkpoint_runtime.py tests/unit/test_path_checkpoint_open_trade_backfill.py tests/unit/test_path_checkpoint_position_side_observation.py tests/unit/test_build_checkpoint_position_side_observation.py tests/unit/test_build_checkpoint_open_trade_backfill.py tests/unit/test_path_checkpoint_action_resolver.py tests/unit/test_path_checkpoint_dataset.py`
- `python -m pytest tests/unit/test_entry_try_open_entry_policy.py tests/unit/test_exit_service.py`

결과:

- `27 passed`
- `17 passed`

즉 collection / observation / resolver / dataset / 기존 entry-exit 영향권까지 모두 통과했다.

---

## 실제 artifact 재생성 결과

실행:

- `python scripts/build_checkpoint_open_trade_backfill.py`
- `python scripts/build_checkpoint_dataset.py`
- `python scripts/build_checkpoint_eval.py`
- `python scripts/build_checkpoint_management_action_snapshot.py`
- `python scripts/build_checkpoint_position_side_observation.py`

---

## 최신 backfill 결과

- `open_trade_count = 2`
- `appended_count = 2`
- `position_side_row_count_after = 5`
- `recommended_next_action = rebuild_pa5_dataset_after_position_side_backfill`

즉 이번 변경 덕분에 실제 open trade 2건이 새 position-side row로 붙었다.

---

## 최신 dataset 결과

- `dataset_row_count = 8`
- `resolved_row_count = 8`
- `position_side_row_count = 5`
- `manual_exception_count = 5`
- `non_wait_hindsight_row_count = 2`
- `hindsight_label_counts = WAIT 6 / PARTIAL_EXIT 1 / PARTIAL_THEN_HOLD 1`
- `recommended_next_action = proceed_to_pa6_best_action_resolver`

해석:

- position-side row는 늘었다
- 하지만 hindsight는 아직 `WAIT`가 많다
- 특히 새로 들어온 `open_loss` family는 아직 rule이 충분히 닫히지 않았다

---

## 최신 eval 결과

- `resolved_row_count = 8`
- `position_side_row_count = 5`
- `manual_exception_count = 5`
- `runtime_proxy_match_rate = 0.75`
- `premature_full_exit_rate = 1.0`
- `runner_capture_rate = 1.0`
- `partial_then_hold_quality = 1.0`

해석:

- `runner_capture` 쪽은 괜찮다
- 하지만 이번에 `open_loss` 계열이 들어오면서 `FULL_EXIT` precision 쪽이 새 병목으로 드러났다
- 즉 다음 refinement는 정말 `FULL_EXIT`를 precision 우선으로 다듬어야 한다

---

## 최신 observation 결과

- `row_count = 8`
- `position_side_row_count = 5`
- `open_profit_row_count = 1`
- `open_loss_row_count = 2`
- `runner_secured_row_count = 0`
- `hold_candidate_row_count = 1`
- `full_exit_candidate_row_count = 2`
- `giveback_heavy_row_count = 2`

`family_counts`

- `open_loss_protective = 1`
- `active_open_loss = 1`

해석:

- `open_loss` family는 드디어 잡히기 시작했다
- `runner_secured` family는 아직도 비어 있다
- 따라서 다음 우선순위는 분명하다

1. `runner_secured` row 확보
2. `FULL_EXIT` precision refinement
3. 그 다음 `HOLD` refinement

---

## 이번 턴에서 얻은 가장 중요한 판단

외부 조언과 실제 artifact를 합치면,
지금 가장 의미 있는 해석은 아래다.

### 1. `open_loss` family는 이제 rule refinement 대상으로 들어왔다

전에는 row가 없어서 추상 논의에 가까웠다.
지금은 실제로 `open_loss_protective`, `active_open_loss`가 보인다.

즉 이제 `FULL_EXIT` 규칙을
진짜 데이터 위에서 다듬을 수 있다.

### 2. `runner_secured`는 여전히 수집이 먼저다

`runner_secured_row_count = 0`이라
`HOLD`를 공격적으로 다듬기엔 아직 이르다.

즉 `HOLD` refinement는
지금 당장 score를 더 만지기보다
runner-preservation row를 더 확보하는 쪽이 우선이다.

### 3. `FULL_EXIT`는 지금 precision gate가 필요하다

`premature_full_exit_rate = 1.0`은
지금 runtime proxy에서 `FULL_EXIT`가 먼저 잡히는 row가 있지만,
hindsight는 아직 그걸 fully support하지 않는다는 뜻이다.

즉 다음 refinement는
무작정 `FULL_EXIT`를 늘리는 게 아니라

- `open_loss`
- `protective_source`
- `full_exit_risk`
- `reversal dominance`
- `giveback_ratio`

를 같이 보는 precision gate로 가야 한다.

---

## 다음 구현 순서 추천

이제 다음 턴에서 바로 들어갈 순서는 이게 맞다.

1. `runner_secured` collection 강화
   - `exit_manage_runner` 쪽 row가 실제로 남도록 추가 보강

2. `FULL_EXIT precision refinement`
   - `open_loss_protective` family 전용 gate 추가

3. `open_loss` / `runner_secured` golden row 추가
   - resolver / dataset hindsight fixture 확장

4. artifact 재생성
   - `premature_full_exit_rate`
   - `runner_secured_row_count`
   - `hold_candidate_row_count`
   를 다시 확인

---

## 최종 한 줄 결론

이번 PF2/PF3의 핵심 성과는
`open_loss` family를 실제 dataset에 등장시키고,
`FULL_EXIT` 병목이 이제 추상이 아니라 구체적인 precision 문제라는 것을 드러낸 것이다.

반면 `runner_secured`는 아직 비어 있으므로,
다음 단계는 **`FULL_EXIT`는 precision gate로 다듬고, `HOLD`는 먼저 runner row를 더 모으는 방향**이 맞다.
