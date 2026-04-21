# Product Acceptance PA4 Teacher Label Release Cut Acceptance Detailed Reference

## 목적

이 문서는 사용자 스크린샷 3장을 기준으로
`여기서는 청산 또는 컷이 맞았던 자리`
를 다시 정의하기 위한 PA4 상세 문서다.

## 핵심 문제

현재 baseline에서 PA4 잔여축은 여전히 남아 있다.
그리고 이번 스크린샷은 그 잔여축을 더 또렷하게 설명해 준다.

핵심은 아래다.

- top maturity 이후 늦은 정리
- regime flip 이후 bounce hold 지속
- countertrend spike fail 뒤 늦은 protect/cut
- weak/no-green adverse 장면에서 release/cut이 늦는 문제

## teacher-label release/cut 정의

이번 스크린샷 기준 release/cut은 아래처럼 정의한다.

- top maturity 이후 상단 reject가 확인된 뒤
- red zone 진입 이후 reclaim 실패가 반복될 때
- countertrend bounce가 lower-high로 끝날 때
- spike fail 이후 direction이 다시 원래 adverse 쪽으로 급히 열릴 때

즉 이번 PA4는
`왜 더 기다렸는가`
보다
`왜 여기서 더 빨리 release/cut하지 못했는가`
를 묻는 축이다.

## symbol reading

### NAS

- top maturity 이후 release/cut 늦음
- spike fail 이후 no-chase / fast cut 필요
- countertrend bounce는 hold보다 release 근거가 강함

### XAU

- upper reject / mixed confirm 이후 늦은 release
- reclaim 실패 반등은 release bias 강화 필요

### BTC

- protect exit / adverse stop 경계가 더 빨라야 함
- range/noise 중 false hold를 줄여야 함

## primary owner

- [backend/services/exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
- [backend/services/exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py)
- [backend/services/exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py)
- [backend/services/exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
- [backend/services/exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_recovery_utility_bundle.py)

## first target question

첫 질문은 이거다.

`teacher label 기준으로는 release/cut가 맞았는데, 현재 로직은 무엇 때문에 hold/defer/late-protect 쪽에 더 오래 머무는가`

이 질문에 답하면
남은 PA4 backlog를 스크린샷 행동 정답 기준으로 줄여갈 수 있다.
