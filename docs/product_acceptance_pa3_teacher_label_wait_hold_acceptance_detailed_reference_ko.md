# Product Acceptance PA3 Teacher Label Wait Hold Acceptance Detailed Reference

## 목적

이 문서는 사용자 스크린샷 3장을 기준으로
`여기서는 더 기다리는 것이 맞았던 자리`
를 다시 정의하기 위한 PA3 상세 문서다.

## 핵심 문제

PA3 수치상 `must_hold = 0`은 이미 닫혔다.
하지만 teacher-label 기준으로는 여전히 확인할 것이 있다.

- 추세 green zone 안에서 hold가 맞았던 자리
- noise만으로 wait가 쉽게 깨지면 안 되는 자리
- 아직 regime flip이 확정되지 않았는데 너무 빨리 정리될 수 있는 자리

즉 이번 PA3는
`수치상 잔여 queue`
보다
`teacher-label hold correctness`
를 보는 단계다.

## teacher-label wait 정의

이번 스크린샷 기준 wait/hold는 아래처럼 정의한다.

- trend continuation 안 눌림 구간
- support reclaim 이후 아직 추세가 살아 있는 구간
- top maturity가 오기 전의 건강한 continuation
- red zone 진입 이후 단순 bounce hold는 제외

## symbol reading

### NAS

- 추세상승 중 눌림에서는 hold가 맞는 자리들이 있다
- 하지만 red zone 이후 bounce hold는 대부분 과한 편이다

### XAU

- 상승 유지 중 hold는 맞지만
- red zone reclaim 실패 이후 hold는 release가 더 맞다

### BTC

- noise/range가 많아 indiscriminate hold는 위험하다
- BTC의 PA3는 `기다려야 할 자리`보다 `기다리면 안 되는 자리` 경계가 더 중요하다

## primary owner

- [backend/services/exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
- [backend/services/wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
- [backend/services/exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_policy.py)

## first target question

첫 질문은 이거다.

`teacher label 기준 hold가 맞았던 자리에서, 현재 시스템은 무엇 때문에 wait를 너무 빨리 깨는가`

이 질문에 답하면
PA3는 runtime close turnover를 많이 기다리지 않고도
hold correctness 기준으로 미세 조정할 수 있다.
