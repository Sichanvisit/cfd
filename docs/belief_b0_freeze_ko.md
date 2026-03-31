# Belief B0 Freeze

## 목표

- `Belief`의 역할을 더 이상 흔들지 않는다.

고정 문장:

`Belief는 thesis의 지속성과 재확인을 나타내는 누적 확신 레이어다.`

---

## Belief가 하는 일

- 현재 `BUY thesis`가 몇 봉째 유지되는가
- 현재 `SELL thesis`가 몇 봉째 유지되는가
- 방금 나온 근거가 반짝 신호인지, 누적 확신으로 바뀌는 중인지
- 기존 thesis가 유지되는가, 약해지는가, 반대로 넘어가는가

즉:

- `Evidence = 순간 근거`
- `Belief = 시간 누적 확신`

---

## Belief가 하지 않는 일

Belief는 다음 owner를 가져가면 안 된다.

- `Position`
  - 위치 identity
- `Response`
  - 사건 identity
- `State`
  - 시장 성격 / 신뢰도 / 인내심 identity
- `BUY/SELL`
  - 직접 방향 action identity

즉:

- Belief는 `side generator`가 아니다
- Belief는 `action generator`가 아니다
- Belief는 `thesis persistence tracker`다

---

## 코드 계약

현재 freeze 계약은 [belief_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/belief_engine.py)에 metadata로 고정한다.

핵심 metadata:

- `semantic_owner_contract = belief_thesis_persistence_only_v1`
- `belief_freeze_phase = B0`
- `canonical_belief_identity_fields_v1`
- `owner_boundaries_v1`

canonical field:

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`

owner boundary:

- `direct_side_identity_allowed = false`
- `direct_action_identity_allowed = false`

---

## 완료 기준

- Position / Response / State와 owner 충돌 없음
- Belief는 `근거의 지속성`만 말함
- direct side/action identity를 가져가지 않음
- 테스트로 freeze 계약이 고정됨
