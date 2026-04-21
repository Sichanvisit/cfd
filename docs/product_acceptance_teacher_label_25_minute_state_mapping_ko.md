# 1분봉 25개 Teacher-State 최종판 정리

## 목적

사용자가 정리한 25개 1분봉 장세 패턴을 모두 유지한 채, 현재 프로젝트의 `teacher-state` 기준으로 바로 사용할 수 있게 최종판으로 재정리한다.

이 문서는 다음을 목표로 한다.

1. 25개 패턴을 하나도 버리지 않는다.
2. 사람이 차트를 보고 붙이는 정답 라벨 구조를 만든다.
3. `진입 / 기다림 / 청산` 행동 바이어스까지 함께 붙인다.
4. 기존 시스템이 이미 기록하는 `indicator -> regime -> forecast -> decision -> wait -> exit -> close result` 흐름과 결합 가능하게 만든다.

## 핵심 원칙

### 1. 한 구간에는 주패턴 1개

한 샘플에는 `teacher_pattern_id`를 반드시 하나 고른다.

### 2. 겹치는 경우 보조패턴 허용

패턴이 실제로 겹치는 경우 `teacher_pattern_secondary_name`을 추가한다.

예:

- `12 브레이크아웃 직전` + `23 삼각수렴 압축`
- `11 눌림목 반등장` + `24 플래그 패턴장`
- `4 추세 지속장` + `6 점진적 추세장`
- `2 변동성 큰 장` + `7 변동성 확대장`

### 3. 이 25개는 입력이 아니라 teacher-state

이 25개는 메인 학습 입력이 아니라 사람 기준의 정답 state다.

메인 학습 입력은 계속 기존 시스템이 이미 만드는 값으로 유지한다.

### 4. 정량 라벨링은 v2 threshold 기준을 따른다

패턴 이름과 그룹 구조는 이 문서를 따른다.
다만 실제 compact dataset에 패턴을 붙일 때의 수치 기준은 아래 v2 문서를 함께 본다.

- [product_acceptance_teacher_label_state25_threshold_calibration_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_threshold_calibration_detailed_reference_ko.md)

핵심은 다음과 같다.

- 절대 %만으로 강제하지 않는다.
- `고정 절대치 + ATR 정규화 + 구조 확인`을 같이 본다.
- `primary pattern 1개 + secondary pattern 1개` 구조를 유지한다.

## 저장 권장 컬럼

compact 학습 row 기준으로 아래 teacher-state 컬럼을 권장한다.

- `teacher_pattern_id`
- `teacher_pattern_name`
- `teacher_pattern_group`
- `teacher_pattern_secondary_name`
- `teacher_direction_bias`
- `teacher_entry_bias`
- `teacher_wait_bias`
- `teacher_exit_bias`
- `teacher_transition_risk`
- `teacher_label_confidence`
- `teacher_lookback_bars`

권장값 의미:

- `teacher_direction_bias`: `buy_prefer`, `sell_prefer`, `both`, `neutral`
- `teacher_entry_bias`: `early`, `confirm`, `breakout`, `fade`, `avoid`
- `teacher_wait_bias`: `hold`, `short_wait`, `tight_wait`, `avoid_wait`
- `teacher_exit_bias`: `fast_cut`, `trail`, `scale_out`, `range_take`, `hold_runner`
- `teacher_transition_risk`: `low`, `mid`, `high`

## 최종 그룹 구조

### A. 조용한 장

순서:

- `1 쉬운 루즈장`
- `10 공허한 횡보장`
- `14 모닝 컨솔리데이션`
- `13 변동성 컨트랙션`
- `23 삼각수렴 압축`

설명:

- 방향성보다 정리가 우선인 구간
- 대체로 진입보다 관찰과 대기가 우선
- 돌파 전 준비구간인 경우가 많음

### B. 추세장

순서:

- `4 추세 지속장`
- `6 점진적 추세장`
- `15 캔들 연속 패턴`
- `19 속도감 추세장`
- `24 플래그 패턴장`

설명:

- 이미 한 방향 우위가 형성된 장
- 되돌림 이후 재진입이나 추세 추종이 핵심
- 기다림보다 방향 추종이 중요함

### C. 발산장

순서:

- `12 브레이크아웃 직전`
- `7 변동성 확대장`
- `17 거래량 폭발장`
- `3 갑자기 발작장`

설명:

- 압축 해소 혹은 폭발 직전/직후 구간
- 잘 맞으면 크게 먹지만 잘못 추격하면 손실도 큼
- 확인 후 진입이 핵심

### D. 반전·되돌림장

순서:

- `5 Range 반전장`
- `11 눌림목 반등장`
- `16 페이크아웃 반전`
- `22 더블탑/바텀`
- `25 데드캣 바운스`
- `21 갭필링 진행장`

설명:

- 추세 지속보다 되돌림/실패/보정 성격이 강한 장
- 반전과 재진입을 섞어 보되, 항상 확인이 필요함
- `21 갭필링 진행장`은 전환·위험보다 보정/되돌림 성격이 강하므로 이 그룹에 둔다

### E. 전환·위험장

순서:

- `2 변동성 큰 장`
- `8 죽음의 가위장`
- `9 황금십자 직전`
- `18 꼬리물림장`
- `20 엔진 꺼짐장`

설명:

- 추세 전환, 구조 불안정, 과도한 노이즈, 힘 소진이 섞여 있는 장
- 단순 진입 신호라기보다 방향 전환과 방어 판단이 중요함

## 25개 전체 최종 표

| id | 패턴명 | 그룹 | 핵심 의미 | 방향 바이어스 | 진입 바이어스 | 기다림 바이어스 | 청산 바이어스 |
|---|---|---|---|---|---|---|---|
| 1 | 쉬운 루즈장 | A | 아주 조용하고 힘이 약한 장 | neutral | avoid | avoid_wait | range_take |
| 10 | 공허한 횡보장 | A | 좁은 범위 안에서 의미 없이 흔들리는 장 | neutral | avoid | avoid_wait | range_take |
| 14 | 모닝 컨솔리데이션 | A | 장 시작 직후 방향 정리 전 박스 구간 | both | breakout | short_wait | range_take |
| 13 | 변동성 컨트랙션 | A | 원래 큰 변동이 갑자기 줄어든 압축 | neutral | avoid/prepare | short_wait | range_take |
| 23 | 삼각수렴 압축 | A | 고점은 낮아지고 저점은 높아지는 압축 | both | breakout | short_wait | hold_runner |
| 4 | 추세 지속장 | B | 한 방향 우위가 계속 이어지는 장 | both | confirm | hold | hold_runner |
| 6 | 점진적 추세장 | B | 계단식으로 천천히 이어지는 추세 | both | early | hold | trail |
| 15 | 캔들 연속 패턴 | B | 같은 방향 캔들이 연속되는 모멘텀 구간 | both | early | hold | trail |
| 19 | 속도감 추세장 | B | 짧은 시간에 강하게 밀리는 추세 | both | breakout | hold | hold_runner |
| 24 | 플래그 패턴장 | B | 급등/급락 후 좁은 역방향 조정 | both | confirm | hold | trail |
| 12 | 브레이크아웃 직전 | C | 압축 끝단에서 발산 직전 | both | breakout | short_wait | hold_runner |
| 7 | 변동성 확대장 | C | 변동이 점점 커지는 발산 준비 구간 | both | breakout | tight_wait | fast_cut |
| 17 | 거래량 폭발장 | C | 거래량이 비정상적으로 커진 장 | both | breakout | tight_wait | fast_cut |
| 3 | 갑자기 발작장 | C | 평온하다가 순간 폭발하는 장 | both | breakout | short_wait | fast_cut |
| 5 | Range 반전장 | D | 박스 상단/하단에서 방향 반전 반복 | both | fade | short_wait | range_take |
| 11 | 눌림목 반등장 | D | 강한 움직임 뒤 조정 후 재개 구간 | buy_prefer | confirm | hold | trail |
| 16 | 페이크아웃 반전 | D | 돌파처럼 보였다가 즉시 반대로 말림 | opposite_to_break | fade | short_wait | fast_cut |
| 22 | 더블탑/바텀 | D | 비슷한 고점/저점을 두 번 테스트 | reversal_side | confirm | short_wait | fast_cut |
| 25 | 데드캣 바운스 | D | 급락 후 약한 반등 뒤 다시 하락 | sell_prefer / avoid_buy | fade | avoid_wait | fast_cut |
| 21 | 갭필링 진행장 | D | 과도한 이동을 천천히 메워가는 장 | fill_direction | confirm | short_wait | range_take |
| 2 | 변동성 큰 장 | E | 큰 몸통과 긴 꼬리가 함께 많은 위험장 | both | confirm | tight_wait | fast_cut |
| 8 | 죽음의 가위장 | E | 하락 전환이 본격화되는 초입 | sell_prefer | confirm | hold | trail |
| 9 | 황금십자 직전 | E | 상승 전환 가능성이 커지는 초입 | buy_prefer | early | hold | hold_runner |
| 18 | 꼬리물림장 | E | 위아래 꼬리가 길고 충돌이 심한 장 | neutral | avoid/fade | avoid_wait | fast_cut |
| 20 | 엔진 꺼짐장 | E | 추세가 진행되다 힘이 급격히 죽는 장 | opposite_or_neutral | avoid/new fade | short_wait | scale_out |

## 행동축 최종 정리

### 진입 우선 패턴

- `4 추세 지속장`
- `6 점진적 추세장`
- `11 눌림목 반등장`
- `12 브레이크아웃 직전`
- `15 캔들 연속 패턴`
- `19 속도감 추세장`
- `24 플래그 패턴장`

의미:

- 방향 우위를 따라 진입하는 편이 유리한 패턴
- 다만 `12`, `19`는 확인 없이 추격하면 손실이 커질 수 있음

### 기다림 우선 패턴

- `1 쉬운 루즈장`
- `10 공허한 횡보장`
- `13 변동성 컨트랙션`
- `14 모닝 컨솔리데이션`
- `23 삼각수렴 압축`

의미:

- 성급한 진입보다 준비/관찰이 우선인 패턴
- 대체로 “지금 들어가기보다, 다음 방향이 드러날 때까지 기다려야 하는” 구간

### 청산/컷 우선 패턴

- `16 페이크아웃 반전`
- `20 엔진 꺼짐장`
- `25 데드캣 바운스`

의미:

- 새 진입보다 기존 포지션 정리나 빠른 방어가 더 중요한 패턴

### 조건부 패턴

- `2 변동성 큰 장`
- `3 갑자기 발작장`
- `5 Range 반전장`
- `7 변동성 확대장`
- `8 죽음의 가위장`
- `9 황금십자 직전`
- `17 거래량 폭발장`
- `18 꼬리물림장`
- `21 갭필링 진행장`
- `22 더블탑/바텀`

의미:

- 방향 확인, 구조 확인, 거래량 확인, 돌파/실패 확인이 붙을 때만 진입 우위가 생김
- 그렇지 않으면 기다림 또는 빠른 방어가 더 맞음

## 추천 보조패턴 조합

### 자주 같이 붙는 조합

- `12 브레이크아웃 직전` + `23 삼각수렴 압축`
- `11 눌림목 반등장` + `24 플래그 패턴장`
- `4 추세 지속장` + `6 점진적 추세장`
- `2 변동성 큰 장` + `7 변동성 확대장`
- `16 페이크아웃 반전` + `18 꼬리물림장`
- `20 엔진 꺼짐장` + `4 추세 지속장 종료부`

## 현재 시스템 입력과의 연결

이 teacher-state는 메인 입력이 아니라 사람 기준 정답 라벨이다.

메인 입력은 계속 기존 시스템이 이미 기록하는 값으로 유지한다.

대표 입력 후보:

- indicator
  - RSI, ADX, DI, 이평, 볼린저 밴드 위치
- regime
  - 변동성 비율, 거래량 비율, 스프레드 상태, 심볼별 buy/sell multiplier
- position/response
  - 현재 위치 해석, 에너지, 상단/하단/중앙 구조 상태
- forecast
  - continuation / reversal / false-break / better-exit-if-wait / recover-after-pullback 확률
- decision
  - 왜 observe인지, 왜 blocked인지, 왜 probe인지
- wait/exit
  - 기다릴수록 좋은지, 빨리 잘라야 하는지, giveback이 큰지, adverse risk가 큰지
- close result
  - 실제 손익, giveback, post-exit MFE/MAE, wait_quality, loss_quality

## 결론

이 25개는 더 줄이지 않는다.

최종 사용 방식은 다음과 같다.

1. 25개를 전부 유지한다.
2. 한 구간에는 주패턴 1개를 붙인다.
3. 겹치면 보조패턴 1개를 추가한다.
4. 동시에 `진입 / 기다림 / 청산` 행동 바이어스를 같이 붙인다.
5. 학습은 기존 시스템 입력을 사용하고, 이 25개는 teacher-state 정답으로 사용한다.

즉 최종 구조는 `25개 단일 목록`이 아니라, `그룹 + 주패턴 + 보조패턴 + 행동 바이어스` 구조다.
