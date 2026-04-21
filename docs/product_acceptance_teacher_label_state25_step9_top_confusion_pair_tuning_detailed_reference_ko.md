# Teacher-Label State25 Step 9-E4 Top Confusion Pair Tuning 상세 기준서

## 목적

Step 9-E4의 목적은 현재 seed와 pilot baseline이 실제로 가장 많이 헷갈리는 쌍을 먼저 찾아서,
watchlist 전체를 한꺼번에 건드리지 않고 상위 1~3쌍만 좁게 조정하는 것입니다.

이번 단계는 execution 반영 단계가 아니라:

- 현재 실제 confusion을 기준으로 우선순위를 정하고
- rule labeler의 fallback 경계를 약하게 보정하고
- recent labeled row에 bounded relabel을 적용한 뒤
- 다시 baseline / QA를 돌려 변화 여부를 보는 단계입니다.

## 입력

Step 9-E4는 아래 두 입력을 같이 봅니다.

1. full labeling QA 결과
- primary/secondary pair 분포
- watchlist pair 관측 여부
- group skew

2. pilot baseline 결과
- group top confusion
- pattern top confusion
- supported pattern ids

기준 파일:

- [teacher_pattern_full_labeling_qa.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_full_labeling_qa.py)
- [teacher_pattern_pilot_baseline.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_pilot_baseline.py)
- [teacher_pattern_confusion_tuning.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_confusion_tuning.py)

## 현재 E4 우선순위

현재 seed 기준 실제 우선순위는 이렇습니다.

1. group confusion
- `A -> D`
- 의미: 조용한 장/압축 fallback이 explicit reversal-range 문맥을 먹고 있음

2. pattern confusion
- `1 -> 5`
- 의미: `쉬운 루즈장`과 `Range 반전장`이 explicit range reversal setup 구간에서 섞임

반면 원래 watchlist였던:

- `12-23`
- `5-10`
- `2-16`

은 현재 seed에선 아직 충분히 관측되지 않아 `observe_only`로 둡니다.

## 이번 단계에서 채택한 조정

### 1. pattern 1 fallback 축소

`쉬운 루즈장`은 thin/noise 상태라고 해도:

- explicit `range_*_reversal` setup
- reversal risk가 이미 높음

이면 fallback 우선권을 주지 않도록 줄였습니다.

즉 `조용함`만으로 1번이 되지 않고,
명시적인 reversal 문맥이 있으면 5번 쪽으로 밀리게 했습니다.

### 2. pattern 5 proxy 강화

`Range 반전장`은 retest/doji가 빈약한 recent sparse row에서도:

- setup_id가 `range_lower_reversal`, `range_upper_reversal`, `outer_band_reversal`
- reversal risk가 높음
- participation이 thin하고 breakout 준비가 아님

이면 5번 proxy 점수를 더 받도록 보정했습니다.

즉 micro detail이 얇아도 explicit range-reversal 문맥은 살리게 했습니다.

### 3. pattern 13 fallback 축소

`변동성 컨트랙션`이:

- explicit range reversal setup
- 이미 reversal risk가 높은 구간

까지 먹어버리지 않도록 thin/low-body fallback을 줄였습니다.

즉 `13`이 `5` 앞을 가로채는 fallback도 같이 정리했습니다.

### 4. pattern 14 session-only fallback 차단

`모닝 컨솔리데이션`은:

- 세션명만 있고
- compression/doji 근거는 없고
- explicit range reversal setup인 경우

붙지 않도록 조정했습니다.

즉 `session + low volume`만으로 14가 되는 경계를 막고,
실제 압축/정리 근거가 있을 때만 14가 붙게 좁혔습니다.

## bounded relabel 원칙

이번 E4는 rule 변경만 하고 끝내지 않고, recent window에 bounded relabel을 허용합니다.

원칙:

- recent `2K` 범위만 relabel
- 기존 labeled row를 덮을 수 있음
- overwrite는 execution이 아니라 teacher-label compact row에만 적용
- provenance는 `rule_v2_tuned_relabel`
- backup 파일은 반드시 생성

## 현재 결과 해석

최근 bounded relabel을 실제 적용한 결과:

- relabel은 동작함
- preview 기준 최근 재부착 패턴은 `1`, `9` 위주
- current seed 전체 분포는 아직 크게 안 변함
- 즉 E4 첫 보정은 들어갔지만, 현재 seed의 큰 병목은 여전히
  `최근 sparse row 다수가 micro detail 없이 session/setup fallback 위주`
  라는 점입니다

그래서 이번 단계 해석은:

- E4 구현 자체는 완료
- 첫 번째 fallback 보정도 적용
- 하지만 confusion 수치가 크게 줄지 않은 것은
  current seed가 아직 `1/5/14` 근처 sparse setup에 치우쳐 있기 때문

입니다.

## 출력물

이번 단계 산출물:

- confusion tuning report service
- confusion tuning CLI
- labeler fallback 보정
- bounded relabel provenance 구분

관련 파일:

- [teacher_pattern_confusion_tuning.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_confusion_tuning.py)
- [teacher_pattern_labeler.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeler.py)
- [teacher_pattern_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_backfill.py)
- [teacher_pattern_confusion_tuning_report.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/teacher_pattern_confusion_tuning_report.py)

## 다음 연결

이번 E4 다음은 두 갈래입니다.

1. 현재 결과 유지 + labeled row 추가 누적
- rare/watchlist pair가 실제로 나올 때까지 기다리기

2. E5 execution handoff로 바로 가지 않고
- current seed로는 pilot까지만 유지
- 추가 누적 뒤 다시 E4/E5를 반복

즉 현재 판단은:

- E4는 구현 완료
- 현재 seed에선 `observe + accumulate` 성격이 더 큼
- execution handoff는 아직 아님
