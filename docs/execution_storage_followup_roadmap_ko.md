# Execution Storage Follow-up Roadmap

## 1. 목적

이 문서는 최근 `hot/detail 저장 분리`, `semantic trace 복구`, `runtime key 보강` 이후에도
실제로 남아 있는 후속 작업을 정리한 로드맵이다.

핵심 목적은 세 가지다.

- 지금 **확실하게 확인된 병목**과 **아직 후속 점검이 필요한 영역**을 분리한다.
- `XAU / BTC / NAS` 실행 문제를 **storage 문제**와 **execution tuning 문제**로 구분한다.
- 다음 작업을 `실행층 -> 조인키/데이터셋 -> semantic runtime` 순서로 정렬한다.

---

## 2. 현재 상태 요약

### 2-1. 이미 복구된 것

아래 연결은 현재 기준으로 복구되었다.

- hot runtime에 다시 보이는 trace
  - `forecast_assist_v1`
  - `entry_default_side_gate_v1`
  - `entry_probe_plan_v1`
  - `edge_pair_law_v1`
  - `probe_candidate_v1`
  - `entry_decision_context_v1`
  - `entry_decision_result_v1`
- `runtime_snapshot_key` 품질
  - 예전처럼 `symbol=`가 비지 않고
  - 현재는 `symbol=XAUUSD|anchor_field=time|...` 형태로 생성됨
- hot slim runtime 가독성
  - `timestamp`
  - `observe_action`
  - `observe_side`
  - `observe_reason`
  가 top-level에서 바로 보임

즉 지금은 “저장이 안 된다”보다
“읽고도 왜 entry-ready로 못 올라가는가”가 더 핵심이다.

### 2-2. 현재 확인된 실제 병목

최신 `XAUUSD`, `BTCUSD` row 기준 공통 패턴:

- `edge_pair_law_v1.winner_side = BUY`
- `probe_candidate_v1.active = true`
- `observe_reason = lower_rebound_probe_observe`
- `entry_probe_plan_v1.active = false`
- 최종 `blocked_by = lower_rebound_probe_observe`

즉:

`probe candidate 인식은 되는데, 실제 probe entry plan으로 승격되지 못한다`

### 2-3. 아직 남은 데이터 쪽 문제

- `decision_row_key` 중복이 심함
  - 같은 `signal_bar_ts`에서 skipped/wait row가 반복되면 같은 key를 공유함
- `entry_decisions.detail.jsonl`가 다시 매우 커짐
  - hot는 가벼워졌지만 detail sidecar가 재비대화됨
- `semantic_shadow_available = 0`
- `semantic_live_threshold_applied = 0`
  - semantic runtime은 구조는 있으나 실전 영향은 아직 거의 없음
- replay/export 최신화가 완전히 끝난 건 아님

---

## 3. 분류

## 3-1. 지금 바로 손봐야 하는 것

1. `probe -> entry_probe_plan` 승격
2. `observe`와 `block` 이유 분리
3. `XAU/BTC/NAS` 심볼별 probe/confirm 민감도 분리
4. `decision_row_key` 유니크화

## 3-2. 곧 이어서 손봐야 하는 것

5. detail sidecar 보존/압축/회전 정책
6. replay/export가 최신 key 구조를 제대로 타는지 재검증
7. semantic shadow/live가 실제 unavailable인지, 단순 비활성인지 명시화

## 3-3. 나중에 정리해도 되는 것

8. symbol-aware tuning map 통합
9. runtime trace top-level 추가 승격
10. 자동 acceptance report 강화

---

## 4. 실행 로드맵

## Phase EX1. Probe Promotion Gate

### 목표

`probe_candidate_v1.active=true`인 장면이
어떤 조건에서 `entry_probe_plan_v1.active=true`로 올라가는지 명확히 만든다.

### 손볼 곳

- [observe_confirm_router.py](C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/observe_confirm_router.py)
- [entry_service.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)
- [entry_try_open_entry.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)

### 할 일

- `probe candidate`와 `entry-ready probe`를 분리된 규칙으로 재정의
- `winner_side`, `pair_gap`, `forecast_assist`, `barrier`, `belief`를 기준으로 probe 승격 문턱 설정
- 현재처럼 `lower_rebound_probe_observe`가 곧바로 `blocked_by`처럼 보이지 않게 정리

### 완료 기준

- `probe_candidate_v1.active=true`인데 `entry_probe_plan_v1.active=false`인 이유가 trace로 설명 가능
- XAU/BTC에서 적어도 일부 lower-edge 후보가 실제 probe entry-ready로 승격됨

### 리스크

- 승격을 너무 쉽게 열면 premature probe가 늘 수 있음

---

## Phase EX2. Observe vs Block Separation

### 목표

`관찰 중`과 `실제 차단`을 다른 상태로 분리한다.

### 손볼 곳

- [observe_confirm_router.py](C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/observe_confirm_router.py)
- [entry_service.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)
- [wait_engine.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)

### 할 일

- `observe_reason`
- `blocked_by`
- `action_none_reason`

세 필드가 서로 다른 의미를 가지게 정리

예:

- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`

처럼 분리

### 완료 기준

- 같은 row에서 “왜 관찰인지”와 “왜 진입 못 했는지”를 구분 가능
- 차트와 CSV를 같이 봤을 때 해석이 쉬워짐

### 리스크

- 분리만 하고 실제 규칙을 안 바꾸면 로그만 복잡해질 수 있음

---

## Phase EX3. Symbol-aware Probe Temperament

### 목표

같은 semantic이라도 `XAU / BTC / NAS`가 서로 다른 속도와 민감도로 반응하게 만든다.

### 손볼 곳

- [observe_confirm_router.py](C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/observe_confirm_router.py)
- [wait_engine.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
- [entry_service.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)
- [exit_profile_router.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_profile_router.py)

### 할 일

- `XAU`
  - upper sell probe 더 빠르게
  - second-support buy도 더 적극적으로
- `BTC`
  - lower buy는 덜 자주
  - 잡았으면 더 오래
- `NAS`
  - 상대적으로 clean confirm / clean exit 성향 유지

### 완료 기준

- 같은 `lower_rebound_probe_observe`라도 심볼별로 probe 승격률이 달라짐
- XAU는 상단 SELL, BTC는 하단 hold가 체감상 더 맞아짐

### 리스크

- 심볼 분기가 늘수록 유지보수와 튜닝 난도가 올라감

---

## Phase EX4. Decision Row Key Uniqueness

### 목표

`decision_row_key`와 `replay_row_key`가 skipped/wait row에서 과도하게 중복되지 않게 한다.

### 현재 문제

같은 `signal_bar_ts`, 빈 `action/setup_id/ticket` 조합이면
한 심볼에서 수십~수백 row가 같은 key를 공유할 수 있다.

### 손볼 곳

- [storage_compaction.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- [entry_try_open_entry.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [entry_engines.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [replay_dataset_builder.py](C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/offline/replay_dataset_builder.py)
- [dataset_builder.py](C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_builder.py)

### 할 일

- `decision_row_key`에 row-level uniqueness를 더 반영
  - 예: `decision_ts`, `observe_reason`, `probe_state`, `sequence`
- replay builder와 dataset builder가 새 key 규칙을 따라가게 수정
- 기존 key와의 하위 호환 여부 정리

### 완료 기준

- 최근 hot rows에서 `decision_row_key` 대량 중복이 사라짐
- replay/export 조인 품질이 안정화됨

### 리스크

- 기존 intermediate/dataset과 join 규칙이 달라져 재생성이 필요할 수 있음

---

## Phase EX5. Detail Sidecar Control

### 목표

detail sidecar가 다시 비대해지는 문제를 통제한다.

### 손볼 곳

- [storage_compaction.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- [entry_engines.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- 필요하면 별도 rotation/archival script

### 할 일

- detail row retention 기간 정의
- gzip/jsonl rotation 또는 일자별 shard
- contract/comment/shadow raw 중 정말 필요한 것만 남기고 나머지 보관 정책 분리

### 완료 기준

- `entry_decisions.detail.jsonl` 단일 파일 비대화가 멈춤
- forensic 필요성은 유지하면서 저장 폭증을 줄임

### 리스크

- 지나치게 줄이면 사후 디버깅 품질이 떨어질 수 있음

---

## Phase EX6. Semantic Runtime Activation Check

### 목표

semantic shadow/live가 단순 구조만 있는 상태인지, 실제로 활성화 가능한 상태인지 명확히 한다.

### 손볼 곳

- [entry_try_open_entry.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [trading_application.py](C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)
- [ml/semantic_v1/runtime_adapter.py](C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/runtime_adapter.py)

### 할 일

- `semantic_shadow_available=0`의 이유를 더 세분화
  - 모델 없음
  - 로드 실패
  - 심볼 비허용
  - stage 비허용
- `semantic_live_threshold_applied=0`도 같은 방식으로 세분화

### 완료 기준

- runtime row만 봐도 semantic runtime이 왜 비활성인지 즉시 설명 가능

### 리스크

- 설명 trace만 늘고 실제 모델 운영은 아직 안 붙을 수 있음

---

## Phase EX7. Replay / Export Refresh

### 목표

최신 hot/detail/key 구조를 offline 경로가 제대로 따라가게 만든다.

### 손볼 곳

- [export_entry_decisions_ml.py](C:/Users/bhs33/Desktop/project/cfd/scripts/export_entry_decisions_ml.py)
- [replay_dataset_builder.py](C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/offline/replay_dataset_builder.py)
- [dataset_builder.py](C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_builder.py)

### 할 일

- 최신 compact trace 필드 반영 여부 점검
- replay export가 비어 있는 경로 보강
- manifest/missingness report를 최신 구조 기준으로 다시 정리

### 완료 기준

- `ml_exports/replay/*.parquet` 생성 경로 정상화
- manifest에서 `export_kind`, `selected_columns`, `missing_columns`를 안정적으로 확인 가능

### 리스크

- schema 변경 시 구버전 export와 호환 이슈 가능

---

## Phase EX8. Runtime Acceptance

### 목표

차트 체감과 live runtime 이유가 실제로 맞는지 다시 본다.

### 체크포인트

#### XAU

- second-support buy가 probe/confirm으로 실제 승격되는가
- upper sell probe가 너무 늦지 않은가

#### BTC

- lower hold bias가 실제로 exit churn을 줄이는가
- duplicate-edge reentry가 줄었는가

#### NAS

- confirm/exit 속도가 지나치게 느려지지 않았는가

#### 공통

- hot runtime에서 이유가 바로 읽히는가
- offline key/join이 깨지지 않는가

### 완료 기준

- 차트와 row를 같이 봤을 때
  - 왜 probe였는지
  - 왜 승격됐는지
  - 왜 막혔는지
  - 왜 hold/exit였는지
  설명 가능

---

## 5. 우선순위

### 바로 시작

1. `EX1 Probe Promotion Gate`
2. `EX2 Observe vs Block Separation`
3. `EX3 Symbol-aware Probe Temperament`

### 이어서

4. `EX4 Decision Row Key Uniqueness`
5. `EX5 Detail Sidecar Control`

### 그 다음

6. `EX6 Semantic Runtime Activation Check`
7. `EX7 Replay / Export Refresh`
8. `EX8 Runtime Acceptance`

---

## 6. 한 줄 결론

지금은 저장 연결 자체보다
`probe candidate를 entry-ready로 어떻게 올리고, 그 이유를 hot/runtime/offline에서 모두 일관되게 보이게 만들 것인가`
가 핵심이다.

그래서 다음 로드맵은
`실행층 승격 -> 조인키 정리 -> sidecar 정리 -> semantic runtime / offline 최신화`
순서로 가는 것이 맞다.
