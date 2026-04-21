# Product Acceptance PA4 Release Seed Teacher-Label Narrowing Detailed Reference

## 목적

`must_release`가 실제 late release family보다 넓게 잡히는 문제를 줄인다.

이번 축의 핵심 질문은 이것이다.

- runtime release/cut 로직이 늦은가
- 아니면 closed-trade label이 `must_release`를 과대추정하는가

## 관찰

latest baseline에서 `must_release=10`이 유지됐지만, 상위 seed를 다시 보면 두 층이 섞여 있었다.

- 진짜 late release:
  - `Exit Context + meaningful giveback`
  - `non_loss + no_wait + giveback > 0.5`
- 과대추정:
  - `bad_loss + no_wait`
  - `peak_profit_at_exit ~= 0`
  - `giveback_usd = 0`

후자 row는 `release를 더 빨리 했어야 하는가`보다 `애초에 no-green bad loss trade`에 더 가깝다.

## 결정

이번 하위축은 runtime owner를 더 공격적으로 바꾸지 않는다.

대신 baseline freeze의 `must_release` seed를 아래처럼 좁힌다.

- `non_loss / neutral_loss`:
  - 기존처럼 `meaningful giveback`이 있을 때 유지
- `bad_loss`:
  - `peak_profit_at_exit >= meaningful peak`
  - 그리고 `giveback > 0` 또는 `post_exit_mfe > 0.5` 또는 `wait_quality_label=bad_wait`
  - 를 만족할 때만 `must_release` seed 유지

즉 `no green bad_loss`는 `must_release`에서 빼고, 이후 `bad_exit` family로 본다.

## 기대 효과

- `must_release`가 진짜 late release backlog만 더 잘 대표
- `bad_exit`와 `must_release`의 역할 분리
- 다음 PA4 메인축이 `protect/adverse bad_exit`로 더 또렷해짐
