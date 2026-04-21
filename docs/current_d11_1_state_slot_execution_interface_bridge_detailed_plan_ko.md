# D11-1. state_slot -> execution interface bridge 상세 계획

## 목적

decomposition 결과를 바로 execution에 꽂지 않고,
나중의 lifecycle 레이어로 넘길 최소 전달 인터페이스를 read-only로 고정한다.

## 왜 필요한가

지금 구조는 해석 엔진으로는 충분히 좋아졌지만,
실제 매매 행동으로 연결되려면 아래 lifecycle 축이 필요하다.

- entry timing
- hold decision
- add timing
- reduce timing
- exit timing

그런데 지금 단계에서 execution을 직접 바꾸면 해석과 행동이 섞여버린다.
그래서 bridge만 먼저 만든다.

## 인터페이스 필드

- `entry_bias_v1`
- `hold_bias_v1`
- `add_bias_v1`
- `reduce_bias_v1`
- `exit_bias_v1`

## bias 해석 원칙

### stage 기반 기본값

- `INITIATION`
  - entry 높음
  - hold 중간
  - add 낮음
- `ACCEPTANCE`
  - hold 높음
  - add 중간
- `EXTENSION`
  - entry 낮음
  - reduce 높음
  - exit 준비 강화

### texture / ambiguity 조정

- `WITH_FRICTION`
  - entry/add bias를 낮춤
  - reduce bias를 약간 올림
- `DRIFT`
  - add를 억제
  - reduce를 조금 높임
- `HIGH ambiguity`
  - entry/add를 더 보수적으로 낮춤
  - reduce/exit를 강화

## 핵심 원칙

- bridge는 선언적 인터페이스일 뿐이다.
- execution/state25는 바꾸지 않는다.
- `dominant_side`는 bridge가 바꾸지 않는다.
- XAU pilot에서 먼저 read-only로 시험한다.

## artifact

- `state_slot_execution_interface_bridge_summary_v1`
- `state_slot_execution_interface_bridge_latest.json`
- `state_slot_execution_interface_bridge_latest.md`

## 완료 기준

- decomposition 결과가 미래 execution policy layer로 넘겨질 포맷이 runtime row에 보인다.
- 아직 행동은 바뀌지 않지만 lifecycle bias가 읽힌다.
