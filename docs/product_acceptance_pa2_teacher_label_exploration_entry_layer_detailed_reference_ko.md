# Product Acceptance PA2 Teacher Label Exploration Entry Layer Detailed Reference

## 목적

이 문서는 `teacher-label entry gap`을 줄이기 위한 1차 구현으로
`exploration entry layer`를 어떻게 넣었는지 설명한다.

핵심 의도는 단순하다.

- 메인 policy를 무너뜨리지 않는다
- 대신 soft guard에 막혀 놓친 entry family만 좁게 연다
- 들어가더라도 작은 size로 샘플을 모은다
- 이후 ML/후속 라벨링이 가능한 로그를 강제로 남긴다

## 왜 메인 threshold를 바로 풀지 않았는가

teacher-label 스크린샷 기준으로는
현재 시스템이 entry를 너무 보수적으로 놓치는 장면이 분명하다.

하지만 threshold를 전역으로 풀면 아래 문제가 생긴다.

- 기존 PA1/PA2 acceptance 체계가 흐려진다
- 좋은 탐색 데이터와 잡음이 섞인다
- BTC 같은 noise/range 심볼에서 false-positive가 급격히 늘 수 있다

그래서 이번 1차 구현은
`global loosen`이 아니라
`soft-guard bypass exploration overlay`
로 설계했다.

## 1차 exploration 대상

이번 1차는 teacher-label과 가장 직접 맞닿는 probe family 두 개만 연다.

### BUY side

- `lower_rebound_probe_observe`
- probe scene:
  - `btc_lower_buy_conservative_probe`
  - `xau_second_support_buy_probe`
  - `nas_clean_confirm_probe`

### SELL side

- `upper_reject_probe_observe`
- probe scene:
  - `btc_upper_sell_probe`
  - `xau_upper_sell_probe`
  - `nas_clean_confirm_probe`

즉 `green-zone continuation / rebound probe`, `top maturity reject probe`
처럼 teacher-label에서 실제 진입 anchor로 볼 수 있는 family만 1차 exploration 대상이다.

## 어떤 guard를 우회하는가

이번 exploration layer는 모든 block를 여는 게 아니다.

1차 우회 대상:

- `probe_promotion_gate`
- `consumer_entry_not_ready`
- soft block reason이
  - `forecast_guard`
  - `barrier_guard`
  - `probe_promotion_gate`
  인 경우

우회하지 않는 것:

- `energy_soft_block`
- broad cluster/pyramid/add-on block
- order block / market closed
- hard no-trade family

즉 `soft teacher-label miss entry`만 연다.

## 진입 방식

exploration이 활성화되면:

- skip 하지 않고 open path를 계속 탄다
- 대신 size를 심볼별 exploration multiplier로 줄인다
- row에는 exploration tag를 남긴다

현재 기본 multiplier:

- `BTCUSD`: `0.30`
- `NAS100`: `0.45`
- `XAUUSD`: `0.40`

그리고 기본적으로:

- `same_dir_count == 0`
- 즉 flat position 상태에서만 exploration을 허용한다

## 로깅

entry row에는 아래가 남는다.

- `teacher_label_exploration_active`
- `teacher_label_exploration_family`
- `teacher_label_exploration_reason`
- `teacher_label_exploration_size_multiplier`
- `teacher_label_exploration_entry_v1`

즉 나중에 ML이나 회고에서
`이 진입이 메인 정책인지 exploration인지`
를 구분할 수 있다.

## owner

- [backend/services/entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [backend/core/config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

## 핵심 판단

이번 1차 구현은
`막 들어간다`
를 코드로 옮긴 게 아니라,
`teacher-label family만 작은 size로 탐색 샘플을 더 모은다`
를 코드로 옮긴 것이다.
