# ST0 Current State Audit 상세 계획

## 1. 왜 ST0가 먼저인가

지금 문제는 detector를 더 복잡하게 만드는 것보다,
이미 코드 어딘가에서 계산되거나 계산 재료가 있는 정보가
`runtime latest state contract`까지 어떻게 올라오지 못하고 있는지를 먼저 분해하는 데 있다.

즉 ST0의 목적은:

- 무엇이 이미 latest state에 직접 보이는지
- 무엇이 이미 다른 레이어에서 계산되지만 아직 state contract로 승격되지 않았는지
- 무엇은 아직 계산 자체가 없는지

를 구분하는 것이다.


## 2. ST0가 만들어야 하는 답

ST0 audit는 각 target field마다 아래 중 하나로 분류해야 한다.

- `DIRECT_PRESENT`
  - 최신 runtime row에 이미 직접 보인다
- `DECLARED_BUT_EMPTY`
  - 필드 자리는 있지만 최신 샘플에 값이 비어 있다
- `ALREADY_COMPUTED_BUT_NOT_PROMOTED`
  - 관련 runtime proxy나 upstream source token이 이미 있다
  - 하지만 target field 자체는 latest state contract에 없다
- `NOT_COMPUTED_YET`
  - 관련 proxy도, source token도 뚜렷하지 않다


## 3. ST0가 보는 입력

### 3-1. latest runtime state

기준 파일:

- [runtime_status.detail.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.detail.json)

여기서 실제 분석 기준 row는 top-level `symbols`가 아니라:

- `latest_signal_by_symbol`

이다.

즉 ST0는 `latest_signal_by_symbol.<symbol>` row를 기준으로
실제 latest contract field가 무엇인지 본다.

### 3-2. upstream source hints

기준 파일:

- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- [context_classifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_classifier.py)
- [mt5_snapshot_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\mt5_snapshot_service.py)
- [semantic_baseline_no_action_cluster_candidate.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\semantic_baseline_no_action_cluster_candidate.py)
- [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)

여기서 ST0는 특정 token / proxy가 존재하는지를 확인해
field가 완전히 없는지, 아니면 이미 계산 재료가 있는지를 본다.


## 4. ST0 field catalog

ST0는 아래 5개 group을 본다.

- `HTF`
- `PREVIOUS_BOX`
- `CONFLICT`
- `SHARE`
- `META`

각 field마다 최소 아래 메타를 가진다.

- `context_group`
- `state_layer`
  - `raw`
  - `interpreted`
  - `meta`
- `target_field`
- `direct_runtime_fields`
- `related_proxy_fields`
- `source_refs`
- `recommended_next_action`
- `notes_ko`


## 5. ST0가 특별히 구분해야 하는 것

### 5-1. direct field와 related proxy는 다르다

예:

- `trend_1h_direction`
  - direct field는 아직 없을 수 있다
- 하지만
  - `TIMEFRAME_H1`
  - `copy_rates_from_pos(...)`
  - `mtf_ma_big_map_v1`
  같은 단서가 있으면
  이는 `ALREADY_COMPUTED_BUT_NOT_PROMOTED`로 봐야 한다

즉 ST0는 "정확히 그 field가 있나"만 보지 않고,
"그 field를 만들 재료가 이미 살아 있나"도 같이 본다.

### 5-2. share는 runtime state보다 downstream에서 먼저 계산될 수 있다

예:

- `cluster_share_global`
- `cluster_share_symbol`

은 semantic cluster candidate / propose에서는 이미 계산될 수 있다.
따라서 이 경우도 ST0는
`runtime missing but downstream already computed`
로 분류해야 한다.


## 6. ST0 output

### 6-1. JSON artifact

경로:

- [state_first_context_contract_gap_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\state_first_context_contract_gap_audit_latest.json)

포함 내용:

- summary
- group_summary
- field_rows
- already_computed_but_not_promoted
- not_computed_yet
- direct_present

### 6-2. Markdown artifact

경로:

- [state_first_context_contract_gap_audit_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\state_first_context_contract_gap_audit_latest.md)

운영자는 이 markdown으로
"지금 무엇이 이미 있고, 무엇이 다음 step(ST1/ST2/ST3/ST6) 대상인지"
빠르게 볼 수 있어야 한다.


## 7. ST0 완료 기준

- `latest_signal_by_symbol` 기준 direct field 존재 여부를 확인할 수 있다
- field별로 `DIRECT_PRESENT / DECLARED_BUT_EMPTY / ALREADY_COMPUTED_BUT_NOT_PROMOTED / NOT_COMPUTED_YET` 분류가 된다
- group summary가 나온다
- `recommended_next_step`이 나온다
- ST1 / ST2 / ST3 / ST6 우선순위를 실제 artifact로 설명할 수 있다


## 8. ST0 이후 기대 효과

ST0가 끝나면 다음 구현은 감으로 가지 않는다.

예:

- HTF raw는 source token이 충분하지만 latest state엔 없음
  - → `ST1`
- previous box는 runtime proxy는 있지만 contract field가 없음
  - → `ST2`
- conflict / late chase는 runtime proxy만 있고 interpreted contract는 없음
  - → `ST3`
- share는 downstream 계산은 있으나 latest contract엔 없음
  - → `ST6`

즉 ST0는
**state-first 로드맵의 실제 출발점이 되는 gap map**이다.
