# P4-5 상하단 방향 오판 / 캔들-박스 불일치 / 힘 우세 surface

## 목표

NAS100 / XAUUSD / BTCUSD 공통으로 아래 3가지를 기존 관찰-학습 루프에 얹는다.

- 상하단 방향 오판 detector
- 캔들/박스 위치 대비 방향 해석 불일치 detector
- 위/아래 힘 우세 설명 surface

## 이번 단계에서 한 일

### 1. scene-aware detector 확장

- 기존 `scene disagreement` row를 그대로 버리지 않고
- live `upper/lower force`가 강하게 보이는 심볼이면
- summary를 `상하단 방향 오판 가능성 관찰`로 더 직접적으로 surface 하도록 확장

주요 근거:

- `checkpoint_scene_disagreement_audit_latest.json`
- `runtime_status.detail.json`의 `latest_signal_by_symbol`

사용하는 live 축:

- `position_energy_surface_v1.energy.lower_position_force`
- `position_energy_surface_v1.energy.upper_position_force`
- `position_energy_surface_v1.energy.middle_neutrality`
- `position_snapshot_v2.energy.metadata.position_dominance`
- `consumer_check_side`
- `consumer_check_reason`
- `blocked_by`
- `next_action_hint`

### 2. candle/weight detector 확장

- 기존 generic `weight patch preview`는 유지
- 다만 `upper/lower/reject/rebound/reclaim/box/range/mixed/compression/wick/band` 계열이면
- summary를 `캔들/박스 위치 대비 방향 해석 불일치 관찰`로 더 직접적으로 surface
- live force가 있으면 evidence에 `위/아래 힘`과 `현재 체크 이유`를 같이 실음

즉 기존 detector를 새로 갈아엎지 않고,
기존 `candle_weight detector -> feedback -> propose` 루프 위에 더 읽히는 설명을 얹는 방식이다.

### 3. 실시간 DM 설명 확장

실시간 `진입 / 대기 / 반전` DM에 아래 한 줄을 추가했다.

- `위/아래 힘: 상단 우세 (하단 0.05 / 상단 0.34 / 중립 0.00)`

이 줄은 의사결정을 바꾸지 않는다.
오직 현재 런타임이 어떤 위치 에너지/힘 균형을 보고 있는지 surface 한다.

## 의도적으로 하지 않은 것

- 실제 entry/exit/reverse 로직 변경
- detector 결과의 자동 apply
- force dominance만으로 BUY/SELL를 강제 교정

즉 이번 단계는 끝까지 `observe / report / feedback / propose`까지만 간다.

## 학습 루프 연결

이번 slice는 기존 학습 루프에 그대로 연결된다.

1. `/detect`
2. `상하단 방향 오판 가능성 관찰` 또는 `캔들/박스 위치 대비 방향 해석 불일치 관찰` surface
3. `/detect_feedback D번호 맞았음|과민했음|놓쳤음|애매함`
4. feedback-aware narrowing / promotion
5. `/propose`

즉 이번 단계의 목적은
`바로 고치기`가 아니라
`이 오판을 더 정확하게 보고, 더 잘 학습 재료로 쌓기`다.

## 완료 기준

- NAS100 / XAUUSD / BTCUSD 모두 같은 detector surface 규칙을 탐
- `/detect` 결과에 방향 오판/캔들-박스 불일치가 더 직접적인 한국어 문장으로 뜸
- 실시간 DM에 `위/아래 힘` 한 줄이 붙음
- 기존 feedback/propose 루프가 깨지지 않음
