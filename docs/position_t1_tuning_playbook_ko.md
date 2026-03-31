# T1-1 Position Tuning Playbook

## 목적

이 문서는 `semantic_tuning_roadmap_ko.md`의 `T1-1 Position`을 실제 운영에서 반복 가능하게 수행하기 위한 실무용 플레이북이다.

핵심 목적은 두 가지다.

1. 스크린샷 기반 직관을 버리지 않으면서도
2. 수정 판단은 항상 `T1-1 Position` 기준으로만 내리게 만드는 것

즉 이 문서는:

- 감각 기반 설명
- 로그 기반 확인
- 코드 수정 기준
- 전후 비교

를 한 루프로 묶는다.

---

## 이 플레이북이 다루는 범위

`T1-1 Position`에서 다루는 것은 아래 네 가지뿐이다.

- `zone 경계`
- `bias 판정 규칙`
- `unresolved 허용 범위`
- `conflict 우선순위 / conflict 민감도`

아래는 이 단계에서 하지 않는다.

- `Response` 수정
- `State` 수정
- `Evidence` strength 수정
- `Consumer`로 덮기
- `Energy hint`로 덮기
- symbol별 예외 패치

---

## 현재 코드에서 Position의 수정 지점

### 1. 좌표 생성

파일:
- `backend/trading/engine/position/builder.py`

역할:
- `x_box`
- `x_bb20`
- `x_bb44`
- `x_ma20`
- `x_ma60`
- `x_sr`
- `x_trendline`

를 만들어 `PositionVector`로 묶는다.

이 단계는 주로 입력 좌표 생성 단계이며, `T1-1`에서 가장 자주 직접 수정하는 곳은 아니다.

### 2. zone 경계

파일:
- `backend/trading/engine/position/interpretation.py`

핵심 상수:
- `_POSITION_ZONE_STANDARD_BANDS`
- `_POSITION_ZONE_SPECS`
- `_RAW_FALLBACK_WINDOW`
- `_CONFLICT_AXIS_THRESHOLD`
- `_MIDDLE_NEUTRALITY_SCALE`

이 상수들은 `T1-1`에서 실제로 가장 먼저 건드릴 가능성이 높은 지점이다.

### 3. label 판정

파일:
- `backend/trading/engine/position/interpretation.py`

핵심 함수:
- `_detect_aligned_label`
- `_detect_bias_label`
- `_detect_conflict_kind`
- `_detect_secondary_context_label`
- `build_position_interpretation`

이 함수들이 최종적으로:

- `primary_label`
- `bias_label`
- `secondary_context_label`
- `conflict_kind`
- `dominance_label`

을 만든다.

### 4. energy-style position 압축

파일:
- `backend/trading/engine/position/interpretation.py`

핵심 함수:
- `build_position_energy_snapshot`

핵심 출력:
- `upper_position_force`
- `lower_position_force`
- `middle_neutrality`
- `position_conflict_score`

이 값들은 `T1-1`에서 “왜 이걸 middle/conflict/unresolved처럼 봤는가”를 설명하는 데 중요하다.

---

## 운영 입력 형식

앞으로 `T1-1 Position` 케이스는 아래 입력 묶음으로 다룬다.

### 필수 입력

1. 차트 스크린샷
2. 사용자의 기대 해석
3. 해당 시점의 실제 Position 출력

### 권장 입력

1. `symbol`
2. 대략적인 시각
3. 그 시점에 기대한 행동
- 예: `하단 반전 감각`
- 예: `상단 continuation처럼 보면 안 됨`
- 예: `middle unresolved여야 함`
4. 실제 outcome
- `entered`
- `wait`
- `skipped`

### 기대 해석 작성 템플릿

아래 템플릿으로 적는다.

```text
[기대 해석]
- 이 차트는 LOWER / UPPER / MIDDLE 중 무엇처럼 보여야 하는가
- bias가 필요한가, 필요 없다면 왜 아닌가
- conflict로 봐야 하는가, 아니면 정렬 상태인가
- unresolved가 맞는가, 아니면 과도한 unresolved인가
- 이 해석이 진입/대기 판단에 어떤 영향을 줘야 하는가
```

---

## 관찰 도구

### 1. live runtime 확인

파일:
- `data/runtime_status.json`

여기서 확인할 것:
- `latest_signal_by_symbol`
- `current_entry_context_v1`
- `position_snapshot_v2`

### 2. decision 로그 확인

파일:
- `data/trades/entry_decisions.csv`

여기서 확인할 것:
- `outcome`
- `blocked_by`
- `setup_id`
- `position_snapshot_v2`
- `observe_confirm_v2`

### 3. Position watcher

파일:
- `scripts/position_entry_watch.py`

역할:
- runtime signal
- 새 entry decision

을 같이 보면서 아래를 기록한다.

- `primary_label`
- `bias_label`
- `secondary_context_label`
- `conflict_kind`
- `position_conflict_score`
- `middle_neutrality`
- `action / outcome / blocked_by`

### 실행 예시

짧게 확인:

```bash
python scripts/position_entry_watch.py --interval-sec 3 --max-cycles 5
```

30분 감시:

```bash
python scripts/position_entry_watch.py --interval-sec 5 --duration-min 30
```

산출물:
- `data/analysis/position_entry_watch_*.jsonl`
- `data/analysis/position_entry_watch_summary_*.json`

---

## T1-1 실제 수행 순서

### Step 1. 스크린샷 기준 기대 해석을 먼저 적는다

반드시 먼저 적는다.

이때는 아직 로그를 보지 않는다.

적는 항목:
- `upper/lower/middle`
- `bias 필요 여부`
- `conflict 여부`
- `unresolved 허용 여부`

목적:
- 차트 직관을 먼저 고정해서, 나중에 로그를 본 뒤 설명을 끼워 맞추는 실수를 막기 위함

### Step 2. 실제 Position 출력을 확인한다

확인 필드:
- `primary_label`
- `bias_label`
- `secondary_context_label`
- `position_conflict_score`
- `middle_neutrality`
- `box_zone`
- `bb20_zone`
- `bb44_zone`
- `lower_position_force`
- `upper_position_force`

### Step 3. mismatch를 로드맵 항목으로 매핑한다

#### A. zone 경계 문제

대표 증상:
- 상단인데 `LOWER_*` 느낌
- 하단인데 `UPPER_*` 느낌
- `LOWER_EDGE / UPPER_EDGE / MIDDLE` 경계가 체감과 다름

주 수정 지점:
- `_POSITION_ZONE_STANDARD_BANDS`
- `_POSITION_ZONE_SPECS`
- `_zone_from_axis_coord`

#### B. bias 판정 문제

대표 증상:
- 분명 middle-upper bias인데 그냥 lower/upper로 고정
- bias가 너무 쉽게 붙음
- bias가 거의 안 붙음

주 수정 지점:
- `_detect_bias_label`
- `_primary_side_votes`

#### C. unresolved 문제

대표 증상:
- `UNRESOLVED_POSITION`이 너무 많음
- 애매한 중간 구간인데 너무 쉽게 `LOWER` 또는 `UPPER`로 단정

주 수정 지점:
- zone 경계
- raw fallback 범위
- `primary_label = ... or "UNRESOLVED_POSITION"`으로 가는 판정 흐름

#### D. conflict 문제

대표 증상:
- conflict가 지나치게 많이 뜸
- conflict가 거의 안 뜸
- 실제로는 한쪽 우세인데 balanced conflict처럼 남음

주 수정 지점:
- `_CONFLICT_AXIS_THRESHOLD`
- `_detect_conflict_kind`
- `_dominance_from_composite`
- `build_position_energy_snapshot`

### Step 4. 한 번에 한 축만 수정한다

절대 금지:
- 경계값과 bias 규칙을 한 번에 수정
- conflict와 unresolved를 동시에 수정
- Position 보정과 Response/State 수정 동시 진행

원칙:
- 한 케이스에서 원인이 가장 직접적인 축 하나만 고른다

### Step 5. 같은 유형 차트로 재확인한다

한 장만 맞으면 안 된다.

최소한 아래 3종류를 같이 본다.

1. 수정하려는 대표 실패 케이스
2. 그와 비슷한 정상 케이스
3. 반대편 극단 케이스

예:
- `LOWER_EDGE`가 너무 넓다고 느껴 수정했다면
- `LOWER_EDGE 유지가 맞는 차트`
- `MIDDLE로 넘어가야 하는 차트`
- `반대로 UPPER 쪽 정상 케이스`

를 같이 확인해야 한다.

---

## 수정-판정 매트릭스

| 증상 | 우선 판단 | 수정 레이어 | 건드릴 것 |
| --- | --- | --- | --- |
| 하단인데 middle처럼 읽힘 | zone 경계 문제 | Position | `middle`, `lower_edge` 경계 |
| 상단인데 bias 없이 확정 upper로 읽힘 | bias 판정 문제 | Position | `_detect_bias_label` |
| 애매한 구간인데 conflict가 과하게 뜸 | conflict 과민 | Position | `_CONFLICT_AXIS_THRESHOLD`, conflict 규칙 |
| 애매한 구간인데 unresolved가 너무 적음 | unresolved 과소 | Position | zone 경계, fallback 범위 |
| lower와 upper 압력이 동시에 보이는데 conflict가 안 뜸 | conflict 과소 | Position | conflict 축 threshold |
| middle-neutral인데 lower/upper로 너무 쉽게 결정 | middle neutrality 과소 | Position | `middle` 경계, `_MIDDLE_NEUTRALITY_SCALE` |

---

## 버전 관리 규칙

Position 수정은 항상 버전 태그를 남긴다.

예:
- `position_contract_v3`
- `position_zone_v2_p1`
- `position_zone_v2_p2_middle_widened`
- `position_conflict_v2_c1`

권장 기록 형식:

```text
[version]
position_zone_v2_p2_middle_widened

[change]
- middle 경계 0.18 -> 0.22
- lower_edge / upper_edge 유지

[reason]
- lower/middle 경계에서 하단 반전 케이스가 과도하게 middle로 남음

[expected]
- lower 해석 증가
- unresolved/middle 감소
- conflict 영향은 거의 없음
```

---

## acceptance 기준

`T1-1 Position`의 acceptance는 아래 기준으로 본다.

### 1. 설명 가능성

Position 출력만 봐도 아래 질문에 답할 수 있어야 한다.

- 왜 `upper/lower/middle`인가
- 왜 bias가 붙었는가
- 왜 conflict인가
- 왜 unresolved인가

### 2. 차트 감각 일치

스크린샷을 보고 사람이 느끼는 위치 감각과:

- `primary_label`
- `bias_label`
- `secondary_context_label`

이 대체로 일치해야 한다.

### 3. 과민/과소 반응 감소

아래가 줄어야 한다.

- 과도한 `UNRESOLVED`
- 과도한 `CONFLICT_*`
- 분명 lower인데 middle 처리
- 분명 upper인데 lower 처리

### 4. 후속 레이어 오염 감소

Position이 맞아지면 뒤에서 아래 현상이 줄어야 한다.

- lower reversal setup인데 방향 감각이 흔들림
- upper rejection인데 opposite archetype strength가 과도함
- 같은 차트인데 `setup_id`가 들쭉날쭉함

---

## 세션 운영 템플릿

앞으로 실제 세션은 아래 템플릿으로 진행한다.

```text
[케이스 ID]

[스크린샷 설명]
- 사용자가 보는 기대 해석

[실제 Position 출력]
- primary_label
- bias_label
- secondary_context_label
- conflict_kind
- position_conflict_score
- middle_neutrality

[mismatch 분류]
- zone / bias / unresolved / conflict 중 하나

[수정 대상]
- 상수 또는 함수 이름

[수정 전 가설]
- 왜 현재 오판이 나오는가

[수정 후 기대]
- 어떤 라벨 분포가 어떻게 바뀌어야 하는가

[재검증]
- 같은 유형 차트 3개 이상
- watcher / entry_decisions 결과 확인
```

---

## 지금 당장 실행 순서

### Phase P1. 관찰 수집

- 스크린샷 확보
- `position_entry_watch.py` 로그 축적
- 실제 `entered / skipped / wait` 케이스 분류

### Phase P2. Position acceptance 분류

각 케이스를 아래 넷 중 하나로 분류한다.

- zone
- bias
- unresolved
- conflict

### Phase P3. 단일 축 수정

- 한 번에 하나만 수정
- 반드시 버전 이름 부여

### Phase P4. 전후 비교

비교 항목:
- `primary_label` 분포
- `UNRESOLVED_POSITION` 비율
- `CONFLICT_*` 발생 비율
- lower/upper/middle family 분포
- entered/skipped/wait 시의 Position family

### Phase P5. T1-1 완료 판단

아래가 만족되면 `T1-1 Position` 1차 완료로 본다.

- 주요 스크린샷 케이스에서 위치 해석이 납득 가능
- `UNRESOLVED`와 `CONFLICT`가 과민하지 않음
- 같은 유형 차트에서 라벨 일관성이 높아짐
- 뒤 레이어를 건드리지 않고도 Position 설명력이 올라감

---

## 한 줄 원칙

`T1-1 Position`은 스크린샷으로 증거를 모으고, watcher/log로 실제 출력을 확인하고, 로드맵 기준으로 문제를 분류한 뒤, Position 내부의 한 축만 수정하고, 같은 유형 차트로 다시 검증하는 방식으로 진행한다.
