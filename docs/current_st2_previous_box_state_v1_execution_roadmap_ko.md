# ST2 Previous Box State v1 실행 로드맵

## 목표

`previous box state v1` 계산기를 만들어,
이후 `context_state_builder`와 `runtime payload`가 읽을 공통 계약을 준비한다.


## ST2-1. 계약 확정

할 일:

- previous box raw/interpreted/meta 필드 확정
- lifecycle 최소 rule 확정
- `MECHANICAL / STRUCTURAL`
- `LOW / MEDIUM / HIGH`
  기준 확정

완료 기준:

- 문서상 previous box state v1 계약이 고정됨


## ST2-2. previous_box_calculator.py 구현

할 일:

- shifted range 계산
- consolidation 판단
- retest count 계산
- confidence/mode 계산
- relation 계산
- break_state 계산
- lifecycle 계산

완료 기준:

- standalone 함수/클래스로 previous box state 계산 가능


## ST2-3. 테스트

할 일:

- insufficient bars
- confirmed structural box
- breakout held
- invalidated box
- proxy retest 반영

완료 기준:

- focused pytest 통과
- `py_compile` 통과


## ST2 이후 연결

다음 단계:

1. `ST3 context_state_builder.py`
2. `ST4 runtime payload 합류`
3. `ST7 detector bridge`

즉 `ST2`는 계산기와 계약을 먼저 닫고,
실제 runtime latest state 반영은 후속 단계에서 붙인다.
