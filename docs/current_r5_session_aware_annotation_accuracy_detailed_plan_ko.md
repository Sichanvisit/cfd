# R5 Session-Aware Annotation Accuracy 상세 계획

## 1. 목적

R5의 목적은 이제 고정된 annotation 언어와 canonical surface를 세션 기준으로 검증하는 것이다.

다만 첫 버전은 정직하게 간다.

- `direction_accuracy_by_session`는 지금 바로 읽는다
- `phase_accuracy_by_session`는 아직 라벨 부족으로 `HOLD`

즉 R5 v1은 “지금 측정 가능한 것”과 “아직 못 측정하는 것”을 분리해서 보이게 만드는 단계다.

## 2. 입력 축

R5는 아래 세 축을 묶는다.

- `R1`: `ca2_session_split_summary_v1`
- `R3`: `should_have_done_summary_v1`
- `R4`: `canonical_surface_summary_v1`

## 3. v1에서 읽는 것

### 3-1. direction accuracy by session

이 값은 R1의 세션 분해 continuation accuracy를 그대로 사용한다.

- `direction_accuracy_by_session`
- `measured_count_by_session`

### 3-2. annotation candidate load by session

R3에서 생성된 should-have-done 후보 수를 세션별로 본다.

- `annotation_candidate_count_by_session`

이 값은 어디에서 review-worthy 장면이 많이 쌓이는지 보여준다.

### 3-3. runtime/execution divergence by session

R4 canonical surface에서 runtime과 execution이 어긋난 수를 세션별로 센다.

- `runtime_execution_divergence_count_by_session`

## 4. v1에서 아직 못 읽는 것

### 4-1. phase accuracy

지금은 `expected_phase_v1`에 대한 확정 라벨이 충분히 쌓이지 않았다.

그래서 첫 버전은

- `phase_accuracy_by_session = None`
- `phase_accuracy_data_status = INSUFFICIENT_LABELED_ANNOTATIONS`

로 정직하게 surface한다.

## 5. 상태 기준

### READY

- direction accuracy by session이 읽힘
- 세션별 후보/불일치 수가 읽힘
- artifact와 detail payload가 생성됨

### HOLD

- direction은 읽히지만 phase accuracy는 아직 부족

### BLOCKED

- session split, should-have-done, canonical surface 중 하나라도 입력 축이 깨짐

## 6. 의미

R5 v1이 닫혔다는 것은 “세션-aware annotation accuracy가 완성되었다”는 뜻이 아니다.

정확한 의미는 이렇다.

- 세션별 방향 정확도를 annotation 축과 같이 보기 시작했다
- 세션별 review load와 divergence를 같이 읽을 수 있다
- phase accuracy는 아직 보류라는 사실을 정직하게 보여준다

즉 R5 v1은 `완성`보다 `정직한 측정 시작`에 더 가깝다.
