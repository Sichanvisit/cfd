# R2 최소 Annotation Contract 상세 계획

## 1. 목적

이 문서는 `R2. 최소 annotation contract 정의`를 실제로 시작하기 위한 기준 문서다.

현재 R1 결과를 보면 세션 차이 자체는 읽힌다.

- `EU`: measured 84 / correct_rate 0.4167
- `EU_US_OVERLAP`: measured 61 / correct_rate 0.5574
- `US`: measured 42 / correct_rate 0.6429
- `EU|US gap`: 22.62%p / `SIGNIFICANT`

즉 `세션 차이를 read-only로 읽을 수 있는 상태`까지는 왔다.
하지만 동시에 아래도 사실이다.

- `ASIA` 표본은 아직 0
- `guard_helpful_rate_by_session`은 hindsight 부족
- `promotion_win_rate_by_session`도 hindsight 부족

그래서 지금 가능한 R2는 **최소 계약 정의**까지다.
세션 bias를 execution/state25에 올리는 것은 아직 아니다.

## 2. 지금 R2에 들어갈 수 있는 이유

R2 최소 계약은 아래 조건만 만족하면 시작 가능하다.

1. `R1`이 `READY`
2. 세션 분해 artifact가 읽힘
3. 세션 차이가 실제로 있는지 숫자로 설명 가능
4. session을 direction rule로 쓰지 않는다는 원칙이 고정됨

현재 이 조건은 만족한다.

## 3. 지금 R2에서 하면 안 되는 것

아래는 아직 금지다.

- `session = BUY/SELL` 직접 규칙
- session 기반 execution bias
- session 기반 state25 weight/threshold 변경
- phase 세분화 7단계 확장
- should-have-done 자동 영향력 확대

즉 R2는 `언어 정의`까지만 한다.

## 4. 최소 contract

R2 v1 계약은 아래 다섯 필드만 고정한다.

- `direction_annotation`
  - `UP / DOWN / NEUTRAL`
- `continuation_annotation`
  - `CONTINUING / NON_CONTINUING / UNCLEAR`
- `continuation_phase_v1`
  - `CONTINUATION / BOUNDARY / REVERSAL`
- `session_bucket_v1`
  - `ASIA / EU / EU_US_OVERLAP / US`
- `annotation_confidence_v1`
  - `MANUAL_HIGH / AUTO_HIGH / AUTO_MEDIUM / AUTO_LOW`

## 5. 핵심 원칙

### 5-1. session은 bias layer

`session_bucket_v1`는 context field다.

- 허용: annotation 해석 참고
- 금지: 직접 BUY/SELL 결정

### 5-2. phase는 3단계로 시작

지금은 표본이 더 중요하다.

- `CONTINUATION`
- `BOUNDARY`
- `REVERSAL`

세분화는 이후 annotation accuracy가 쌓인 뒤에만 한다.

### 5-3. confidence는 데이터 품질 게이트

`annotation_confidence_v1`는 should-have-done 품질 관리를 위한 필수 필드다.

## 6. 상태 기준

### READY

- contract enum과 필드가 고정됨
- runtime/detail에서 contract를 읽을 수 있음
- session direct bias 금지가 명시됨

### HOLD

- contract는 있으나 enum 정의가 흔들리거나 일부 consumer가 다른 이름을 씀

### BLOCKED

- R1이 다시 무너지거나
- session bias를 execution에 바로 넣으려는 설계가 섞임

## 7. 산출물

- `session_direction_annotation_contract_v1`
- runtime detail payload export
- R2 상세/로드맵 문서

## 8. R2가 닫혔다는 뜻

R2가 닫혔다는 것은 annotation을 실행에 태운다는 뜻이 아니다.

정확한 의미는 이렇다.

- 같은 장면을 같은 언어로 기록할 최소 schema가 생김
- R3 should-have-done 축이 이 schema를 따라 확장될 수 있음
- 이후 R4 canonical surface가 이 schema를 공유 언어로 삼을 수 있음
