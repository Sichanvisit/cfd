# Teacher-Label Micro-Structure Top10 Step 7 메모

## 메모

- Step 7은 feature를 새로 더 만드는 단계가 아니라, 이미 만든 Top10 micro field를 사람 기준 25개 장세 패턴과 연결하는 단계다.
- 여기서 중요한 건 “이 패턴에는 이 지표 하나”가 아니라 “핵심 2~4개 + 기존 state 보조근거” 구조를 만드는 것이다.
- 그래야 teacher-state가 차트 모양 설명에 머물지 않고 실제 진입/기다림/청산 의사결정과 연결된다.

## 이번 단계 결정

- 모든 25개 pattern에 bridge를 붙인다
- pattern마다 micro Top10 핵심 필드는 2~4개로 제한한다
- micro만으로 부족한 pattern은 `belief / barrier / wait/exit utility / regime` 같은 기존 필드를 보조로 붙인다
- action bias는 `진입 우선`, `기다림 우선`, `청산 우선`, `조건부` 체계를 그대로 유지한다

## 후속 단계

- Step 7 이후에는 이 bridge를 바탕으로 daily compact dataset에서 `teacher_pattern_id`, `teacher_pattern_group`, `teacher_entry_bias`, `teacher_wait_bias`, `teacher_exit_bias`를 어떻게 붙일지 정하면 된다
- 필요하면 이후에는 특정 pattern에 대해 자동 추천 라벨러를 붙일 수 있다
