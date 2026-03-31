# Semantic ML 구조 감사 기준선

## 1. 목적

이 문서는 `Step 1. 구조 감사 기준 고정`의 산출물이다.

용도는 두 가지다.

- 지금 구조를 어떤 기준으로 점검할지 고정
- 이후 변경 작업의 우선순위를 고정

기준 상위 문서:

- `docs/semantic_ml_structure_change_plan_ko.md`
- `data/analysis/semantic_v1_audit_20260321_ko.md`

연결 문서:

- `docs/semantic_ml_key_strategy_ko.md`

---

## 2. 구조 점검 체크리스트

| 점검 층 | 핵심 질문 | 확인 증거 | 합격 기준 | 현재 판정 | 다음 행동 |
| --- | --- | --- | --- | --- | --- |
| Runtime / Logging | 실시간 판단 row가 왜 `wait`, `block`, `fallback`인지 hot row만 봐도 추적 가능한가 | `data/trades/entry_decisions.csv`, `data/runtime_status.json`, `data/runtime_status.detail.json` | early-return row 포함 `semantic_live_*`, `semantic_shadow_*`, trace/quality 요약이 남는다 | 부분 통과 | 새 row 기준으로 `semantic_live_rollout_mode`, `semantic_live_fallback_reason`, `blocked_by`가 빠지지 않는지 다시 확인 |
| Storage / Key | runtime/export/replay/dataset join key가 끊기지 않는가 | `decision_row_key`, `runtime_snapshot_key`, `trade_link_key`, `replay_row_key`, dataset manifest | `joined_rows / max_matchable_rows >= 0.98`, blank key 비율 거의 `0` | 통과 | row-level unique key를 정식 도입할지 결정하고 `join_ordinal` 우회 역할을 문서화 |
| Compact Export / Replay | raw giant csv를 직접 안 읽어도 semantic feature와 replay label이 재생성되는가 | `data/datasets/ml_exports/*.parquet`, `data/datasets/replay_intermediate/*.jsonl`, export/replay manifest | future bars 확보 시 target 생성에 필요한 replay label이 안정적으로 `VALID`로 나온다 | 부분 통과 | future bars를 수동 backfill이 아니라 자동 수집 계층으로 내릴지 결정 |
| Dataset / Target | target이 실제 의미와 같은 방향으로 접히는가 | dataset manifest, preview metrics, sample row review | `timing`, `entry_quality`, `exit_management` 모두 사람이 "왜 1/0인지" 설명 가능 | 실패 | `timing` target부터 재정의 시작 |
| Split Health | train/validation/test가 모두 승격 판단에 쓸 만큼 건강한가 | split counts, symbol/regime/setup slice metrics | validation/test에서 양/음 클래스가 모두 충분하고 특정 symbol/regime 쏠림이 승격을 왜곡하지 않는다 | 실패 | split 규칙과 source window를 다시 잡고 최소 클래스 수 기준을 고정 |
| Leakage / Feature Hygiene | feature가 label을 직접 설명하거나 항상 비어 있지 않은가 | feature list, audit report, missingness summary | direct leakage field `0`, all-missing legacy feature는 자동 제외 | 부분 통과 | legacy source 전용 feature drop policy를 코드에 반영 |
| Training / Shadow / Rollout | 지금 rollout을 넓혀도 되는가 | preview metrics, promotion gates, shadow reports | offline/split/target audit가 먼저 통과해야 함 | 실패 | rollout 확장 중지, target과 split 재설계 우선 |

---

## 3. 표준 합격 기준

### 공통 기준

- `join coverage`: `joined_rows / max_matchable_rows >= 0.98`
- `blank key ratio`: 사실상 `0`
- direct leakage field는 학습 feature에 `0`개
- legacy source에서 all-missing feature는 학습 전에 자동 제외
- 위 기준이 통과되기 전에는 rollout mode를 넓히지 않음

### target / split 기준

- `timing`, `entry_quality`, `exit_management`는 validation/test에서 양/음 클래스가 모두 남아 있어야 함
- 특정 symbol 또는 regime 한 곳만 좋아지고 다른 곳이 무너지면 통과로 보지 않음
- 사람이 sample row를 보고 "왜 1/0인지" 설명할 수 없는 target은 통과 아님

현재 Step 4에서 쓰는 최소 split 기준:

- train minority rows: `64` 이상
- validation minority rows: `32` 이상
- test minority rows: `64` 이상
- test slice(symbol/regime/setup) 점검은 `50` rows 이상 slice만 평가
- slice minority rows는 `8` 미만이면 건강하지 않은 slice로 간주

### 운영 기준

- `semantic_live_*`와 `semantic_shadow_*`가 기록되지 않는 early-return 경로가 있으면 구조 감사 미통과
- future bars가 없어 replay label이 반복적으로 `INSUFFICIENT_FUTURE_BARS`가 되면 compact/replay 경로 미통과

---

## 4. 변경 우선순위 표

| 우선순위 | 작업 | 왜 먼저 하는가 | 대상 파일 | 시작 조건 | 완료 조건 |
| --- | --- | --- | --- | --- | --- |
| P0 | `timing` target 재설계 | 현재 가장 큰 구조 문제다. AUC가 거의 반대 방향이라 정답 정의부터 다시 봐야 한다 | `ml/semantic_v1/dataset_builder.py` | Step 1 기준선 확정 | preview가 최소 무작위보다 의미 있게 동작하고 사례 설명이 가능 |
| P0 | split 건강도 기준 고정 | target이 좋아도 split이 깨지면 metrics를 믿을 수 없다 | `ml/semantic_v1/dataset_splits.py`, `ml/semantic_v1/evaluate.py` | Step 1 기준선 확정 | validation/test 최소 클래스 수와 slice audit 기준이 문서와 코드에 반영 |
| P1 | `entry_quality` target 재설계 | 지금 target이 실제 "좋은 진입"과 어긋날 가능성이 높다 | `ml/semantic_v1/dataset_builder.py` | timing 방향성 재확인 후 | leakage 없이 positive/negative 정의를 사람이 납득 가능 |
| P1 | legacy feature tier 자동화 | 항상 비는 trace/quality feature가 학습과 해석을 흐린다 | `ml/semantic_v1/dataset_builder.py`, `ml/semantic_v1/evaluate.py` | Step 1 기준선 확정 | source generation별 drop policy와 manifest 기록이 붙음 |
| P1 | row-level unique key 전략 결정 | 지금은 복구됐지만 장기적으로 `join_ordinal` 의존을 줄여야 한다 | `scripts/export_entry_decisions_ml.py`, `ml/semantic_v1/dataset_builder.py` | Step 1 기준선 확정 | key 전략이 문서와 코드 기준으로 일치 |
| P2 | `exit_management` split 보강 | target 자체보다 검증 표본 부족이 먼저 문제다 | `ml/semantic_v1/dataset_splits.py`, replay/source build scripts | timing/entry target 재정의 후 | validation/test positive 수가 승격 판단 가능한 수준으로 확보 |
| P2 | future bars 자동 수집 설계 | 지금은 수동 backfill로도 되지만 장기적으로 다시 끊길 수 있다 | `scripts/build_replay_dataset.py`, future bar collection path | compact/replay 경로 안정화 후 | replay label 생성이 수동 backfill 없이 재현 가능 |
| P3 | shadow compare 재개와 rollout 재판정 | 구조와 target이 정상화된 뒤 단계다 | `ml/semantic_v1/shadow_compare.py`, `ml/semantic_v1/promotion_guard.py` | P0~P2 핵심 항목 통과 후 | promotion gate 기준으로 다시 비교 가능 |

---

## 5. Step 1 완료 선언 기준

아래가 만족되면 `Step 1 완료`로 본다.

- 이 문서를 구조 감사 기준선으로 사용
- 이후 변경 작업은 우선순위 표 순서로 진행
- 다음 실작업 1순위를 `timing target 재설계`로 고정
- rollout 확장보다 target/split 재설계가 먼저라는 판단을 팀 기준으로 고정

---

## 6. 다음 실작업 연결

Step 1 다음 작업은 아래 순서로 바로 이어진다.

1. `ml/semantic_v1/dataset_builder.py`에서 `timing` target 접는 규칙 분해
2. `ml/semantic_v1/dataset_splits.py`에서 split 건강도 기준 보강
3. `ml/semantic_v1/evaluate.py`에서 split 기준 위반 시 경고/실패를 더 명확히 표시
