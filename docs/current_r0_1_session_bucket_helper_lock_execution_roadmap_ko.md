# R0-1 Session Bucket Helper 고정 실행 로드맵

## 1. 목적

이 로드맵은 `R1 세션 분해` 전에 공용 `session_bucket helper`를 고정하는 실행 순서를 정의한다.

## 2. 구현 범위

### 포함

- session bucket helper 구현
- runtime row surface 추가
- runtime detail contract export
- 경계 시간 테스트

### 제외

- 세션별 정확도 집계
- annotation contract
- session-aware execution/state25 반영
- transition bucket 분화

## 3. 단계

### R0-1-A. helper contract 고정

고정 내용:

- `ASIA 06:00~15:00`
- `EU 15:00~21:00`
- `EU_US_OVERLAP 21:00~00:00`
- `US 00:00~06:00`
- 서머타임 자동 보정 없음
- transition bucket 없음

완료 기준:

- helper가 항상 이 4구간만 반환

### R0-1-B. runtime row surface

출력:

- `session_bucket_v1`
- `session_bucket_timestamp_source_v1`
- `session_bucket_surface_v1`

완료 기준:

- chart/runtime/entry가 같은 row 기준 세션을 볼 수 있음

### R0-1-C. detail payload contract export

출력:

- `session_bucket_contract_v1`

완료 기준:

- `runtime_status.detail.json`에서 현재 session 계약을 바로 읽을 수 있음

### R0-1-D. boundary test

경계:

- `00:00`
- `05:59`
- `06:00`
- `14:59`
- `15:00`
- `20:59`
- `21:00`
- `23:59`

완료 기준:

- 경계 케이스가 unit test로 잠김

## 4. 완료 기준

1. helper 구현
2. runtime row surface
3. detail contract export
4. 경계 테스트 통과

## 5. 이후 연결

R0-1이 닫히면 다음은 자연스럽게 `R1`이다.

- `correct_rate_by_session`
- `guard_helpful_rate_by_session`
- `promotion_win_rate_by_session`

즉 R0-1은 R1의 바닥을 만드는 단계다.
