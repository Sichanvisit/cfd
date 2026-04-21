# Teacher-Label State25 Threshold Calibration 메모

## 메모

- 외부 조언은 방향성이 좋고, 특히 `절대 %만으로는 BTC / XAU / NAS를 같이 다루기 어렵다`는 지적은 맞다.
- 따라서 state25는 그대로 유지하되, 정량 임계치는 `v2 hybrid threshold`로 보정하는 쪽이 맞다.

## 이번 단계 결정

- `teacher-state 25` 패턴 이름과 그룹 구조는 유지한다.
- 정량 기준은 `고정 절대치 + ATR 정규화 + 구조 확인 강화`로 보정한다.
- 거래량은 단일 burst 기준 대신 `meaningful / strong / explosive` 단계로 나누고, 가능하면 지속 확인을 같이 본다.
- 이 기준은 먼저 `teacher-pattern 라벨링`에 적용하고, 즉시 execution rule로 박지 않는다.

## 채택한 핵심 수정

- `2`, `3`, `14`, `19` -> ATR 정규화 채택
- `5` -> `재시험 2회 + 도지 강화`로 수정 채택
- `12`, `23` -> 재시험/압축 기준 강화 유지
- `15` -> `5봉 기본 / 4봉이면 VB 2.0 이상`으로 수정 채택
- `17` -> `VB 3.0 + 지속 3봉`, 초기에는 `낮은 VD proxy`로 수정 채택
- `1`, `10`, `4` -> 유지 또는 약보정

## 보류한 것

- 자산별 절대 수치를 바로 production rule로 고정하는 것
- `도지` 정의 자체를 너무 느슨하게 바꾸는 것
- teacher-label 검증 전 자동 실행 bias를 같이 바꾸는 것

## 후속 단계

- 다음 자연스러운 단계는 `teacher_pattern_*` compact dataset 스키마에 이 v2 기준을 연결하는 것이다.
- 라벨러 초안은 `primary + secondary pattern` 구조를 유지해야 한다.
- 가능하면 `ATRP helper`를 정식 surface로 올린 뒤 v2를 구현하는 편이 안정적이다.
