# Share / Previous Box / HTF Trend Context 실행 로드맵

## 목표

`계속 올라갈 가능성`, `늦은 추격`, `상위 추세 역행` 같은 장면을
사람이 보는 기준에 더 가깝게 detector / propose / DM에서 읽게 만든다.


## 현재 상태

- `share`: 부분 구축
  - `cluster_share`, `cluster_symbol_share` 존재
- `previous box`: 미구축
  - 현재는 `box_state`, `box_relative_position` 정도만 있음
- `HTF trend`: 미구축
  - 현재 latest runtime row에는 1H/4H/1D trend context 없음


## CX1. Runtime Audit Baseline

목표:
- upstream runtime이 지금 실제로 어떤 필드를 내보내는지 확정

산출물:
- latest runtime field audit
- 심볼별 사용 가능 필드 목록

완료 기준:
- `share / previous box / htf trend` 중 현재 있는 것과 없는 것이 명확히 분리됨


## CX2. Share Context v1

목표:
- global share + symbol-local share + time-box share 설계

구현 범위:
- semantic cluster candidate
- detector evidence
- registry key 등록

후보 필드:
- `cluster_share_global`
- `cluster_share_symbol`
- `time_box_share_15m`
- `time_box_share_1h`

완료 기준:
- NAS/XAU/BTC 각각에서 “전체로는 작아도 심볼 내부에선 큰 군집”이 detector/propose에 드러남


## CX3. Previous Box Context v1

목표:
- 직전 박스 경계와 현재 위치 관계를 evidence화

구현 범위:
- upstream runtime payload
- detector evidence line
- proposal evidence line

후보 필드:
- `previous_box_high`
- `previous_box_low`
- `previous_box_relation`
- `previous_box_break_state`

완료 기준:
- detector가 `직전 박스 상단 위 유지`, `직전 박스 재돌파 실패` 같은 문장을 만들 수 있음


## CX4. HTF Trend Context v1

목표:
- 15M 판단과 1H/4H/1D 상위 추세의 정합성을 evidence화

구현 범위:
- upstream runtime payload
- detector
- notifier

후보 필드:
- `trend_1h_direction`
- `trend_4h_direction`
- `trend_1d_direction`
- `htf_alignment_state`

완료 기준:
- detector / DM에서 `상위 추세 역행`, `상위 추세 정합`을 직접 표현 가능


## CX5. Detector Surface Integration

목표:
- 새 3축을 detector summary/why_now/evidence에 실제로 연결

대상 파일:
- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

완료 기준:
- NAS continuation-gap 같은 장면에서
  - share
  - previous box
  - HTF trend
  3줄이 같이 evidence로 찍힘


## CX6. Notifier / DM Integration

목표:
- 항상 길게 보여주지 않고, 강한 mismatch일 때만 간단히 노출

대상 파일:
- [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)

정책:
- 기본 DM: 짧게 유지
- mismatch 강함: 1줄 추가

예시:
- `맥락: 직전 박스 상단 위 유지 | 1H/4H 상승 정렬 | NAS100 내부 share 93.8%`


## CX7. Proposal / Hindsight Binding

목표:
- detector에서 본 새 evidence가 proposal과 hindsight까지 이어지게 함

대상 파일:
- [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)
- [learning_parameter_registry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\learning_parameter_registry.py)

완료 기준:
- `/propose`에서 새 3축을 가진 패턴이 별도 review 후보로 올라옴


## 추천 순서

1. `CX1` runtime audit baseline
2. `CX2` share context v1
3. `CX3` previous box context v1
4. `CX4` HTF trend context v1
5. `CX5` detector surface integration
6. `CX6` notifier integration
7. `CX7` proposal / hindsight binding


## 운영 원칙

- 먼저 evidence를 만든다
- 그다음 detector에 싣는다
- 그다음 DM/propose에 노출한다
- 마지막에 feedback/hindsight로 review 우선순위를 조절한다

즉 이 로드맵은
`자동 apply 로드맵`이 아니라
`사람 좌표계 evidence 로드맵`
이다.
