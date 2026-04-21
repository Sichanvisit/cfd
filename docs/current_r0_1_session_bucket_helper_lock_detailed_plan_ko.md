# R0-1 Session Bucket Helper 고정 상세 계획

## 1. 목적

이 문서는 `R1 세션 분해`에 들어가기 전에, 모든 consumer가 같은 세션 경계를 쓰도록 `session_bucket helper`를 고정하는 계획이다.

핵심은 단순하다.

- 집계기마다 다른 시간 경계 사용 금지
- 심볼마다 다른 세션 enum 사용 금지
- 실행 중간에 helper 기준이 흔들리는 것 금지

즉 이 단계의 목적은 `세션 해석`이 아니라 **세션 기준의 단일 원천(single source of truth)** 을 만드는 것이다.

## 2. 왜 지금 필요한가

R1은 세션별 정확도 차이를 보는 단계다.
그런데 세션 helper가 흔들리면 아래 문제가 생긴다.

1. 같은 timestamp가 집계기마다 다른 session으로 분류됨
2. `correct_rate_by_session`가 consumer마다 다름
3. 이후 annotation contract가 세션 축을 신뢰할 수 없게 됨

즉 R1 이전에 먼저 고정해야 하는 건 지표가 아니라 **시간 경계**다.

## 3. v1 계약

### 3-1. 고정 4구간

- `ASIA`
  - `06:00 ~ 15:00 KST`
- `EU`
  - `15:00 ~ 21:00 KST`
- `EU_US_OVERLAP`
  - `21:00 ~ 00:00 KST`
- `US`
  - `00:00 ~ 06:00 KST`

### 3-2. v1 제약

- 서머타임 자동 보정 없음
- 전환 구간 bucket 없음
- 심볼별 예외 없음
- helper 하나만 진실 원천

## 4. 왜 단순하게 시작하나

세션을 너무 정교하게 시작하면 오히려 R1이 흔들린다.

예:

- `ASIA_TO_EU_TRANSITION`
- `EU_TO_US_TRANSITION`
- `US_OPEN`, `US_MID`, `US_CLOSE`

이런 분해는 나중에 의미가 있지만, 지금은 표본을 쪼개고 기준만 흔든다.
따라서 v1은 **고정 4구간 + no DST + no transition**으로 간다.

## 5. 구현 원칙

1. helper 하나만 만든다
2. runtime row가 이 helper를 직접 쓴다
3. detail payload에 contract를 surface한다
4. 경계 시간 unit test로 잠근다

## 6. 완료 기준

- `session_bucket_helper_v1`가 존재
- runtime row에 `session_bucket_v1`가 붙음
- detail payload에 `session_bucket_contract_v1`가 노출됨
- 경계 시간 테스트 통과

## 7. 상태 기준

- `READY`
  - helper 경계와 enum이 고정되고 모든 consumer가 같은 helper를 씀
- `HOLD`
  - helper는 있으나 일부 consumer가 아직 직접 시간을 해석함
- `BLOCKED`
  - helper 기준이 계속 바뀌거나 consumer별로 다른 session 규칙을 씀
