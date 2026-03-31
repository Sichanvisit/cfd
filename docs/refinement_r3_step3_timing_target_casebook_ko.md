# R3 Step 3 Timing Target Casebook

## 1. 목적

이 문서는 `R3 Step 3. timing target refinement`의 1차 casebook이다.

이번 1차 목표는 timing target을 크게 뒤엎는 것이 아니라,
`사람이 봐도 애매한 row를 억지로 positive / negative로 접지 않게 만드는 것`이다.


## 2. 이번 1차 변경 요약

기존 규칙은 아래였다.

- `same_side_positive_count > adverse_positive_count`면 positive
- `same_side_positive_count < adverse_positive_count`면 negative
- count tie면 `fallback_delta + quality`가 같은 방향일 때만 target 부여
- 아니면 `None`

문제는 count 우세가 아주 약한데,
fallback과 quality가 둘 다 반대 방향으로 강하게 말하는 row도
그냥 positive / negative로 접힐 수 있었다는 점이다.

그래서 이번 1차에서는 아래 veto를 넣었다.

- count positive인데
  - `fallback_delta < 0`
  - `quality < -TIMING_TIE_QUALITY_THRESHOLD`
  이 둘이 동시에 성립하면 `None`
- count negative인데
  - `fallback_delta > 0`
  - `quality > TIMING_TIE_QUALITY_THRESHOLD`
  이 둘이 동시에 성립하면 `None`

즉 약한 count 우세 하나만으로 target을 확정하지 않고,
나머지 신호가 강하게 반대하면 ambiguous로 남기는 쪽으로 조정했다.


## 3. case 분류

### A. clear positive

예시:

- `same_side=2`
- `adverse=0`
- `positive=2`
- `negative=3`
- `quality=0.0035`

해석:

- semantic count가 분명히 now 쪽으로 우세
- quality도 positive
- fallback count는 거칠게는 반대지만, semantic count와 quality가 더 직접적인 signal

판정:

- `count_positive`
- target = `1`


### B. clear negative

예시:

- `same_side=1`
- `adverse=1`
- `positive=2`
- `negative=3`
- `quality=-0.0012`

해석:

- count tie
- fallback과 quality가 둘 다 negative 방향

판정:

- `tie_break_negative`
- target = `0`


### C. ambiguous tie

예시:

- `same_side=1`
- `adverse=1`
- `positive=2`
- `negative=3`
- `quality=-0.0001`

해석:

- count tie
- fallback은 negative지만 quality가 너무 약함

판정:

- `ambiguous_tie`
- target = `None`


### D. count positive conflict veto

예시:

- `same_side=2`
- `adverse=1`
- `positive=1`
- `negative=3`
- `quality=-0.002`

해석:

- semantic count만 보면 now 우세
- 하지만 fallback과 quality가 둘 다 wait / negative 쪽으로 강하게 반대

기존 문제:

- 예전 규칙이면 그냥 positive가 될 수 있었음

이번 판정:

- `count_positive_conflict_veto`
- target = `None`


### E. count negative conflict veto

예시:

- `same_side=1`
- `adverse=2`
- `positive=3`
- `negative=1`
- `quality=0.002`

해석:

- semantic count만 보면 negative
- 하지만 fallback과 quality가 둘 다 positive 쪽으로 강하게 반대

기존 문제:

- 예전 규칙이면 그냥 negative가 될 수 있었음

이번 판정:

- `count_negative_conflict_veto`
- target = `None`


## 4. 이번 1차의 의미

이번 변경은 target을 더 공격적으로 늘리는 조정이 아니다.

오히려 아래 방향이다.

- 애매한 row를 무리해서 학습용 정답으로 쓰지 않는다.
- semantic count와 fallback / quality가 강하게 충돌하면 ambiguous로 남긴다.
- timing target이 `지금 진입 vs 조금 기다림` 의미를 더 설명 가능하게 만든다.


## 5. 코드 / 테스트 근거

코드:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
  - `_resolve_timing_target_reason`
  - `_resolve_timing_target`

테스트:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
  - tie-break negative
  - ambiguous tie
  - clear positive
  - count positive conflict veto
  - count negative conflict veto


## 6. preview / evaluate 재확인 결과

실제 preview/evaluate 재확인은 별도 메모로 정리했다.

- [refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md)

핵심 결과만 요약하면 아래와 같다.

- 비교 baseline은 기존 latest preview가 쓰던 동일 legacy feature/replay 쌍으로 고정했다.
- timing rows는 `2351 -> 2351`로 동일했다.
- accuracy는 `0.636325 -> 0.636325`로 동일했다.
- timing AUC는 `0.610649 -> 0.633218`로 `+0.02257` 개선됐다.
- brier score는 `0.343885 -> 0.342965`, calibration error는 `0.338382 -> 0.337823`로 소폭 개선됐다.
- promotion gate는 old/new 모두 `pass`였고 warning 구성도 유지됐다.

즉 이번 1차 veto는
`설명 가능성을 높이면서 discrimination을 해치지 않았다` 정도가 아니라,
같은 baseline에서 timing AUC를 실제로 개선한 것으로 볼 수 있다.


## 7. 현재 판단

현재 상태는 다음과 같다.

- `Step 3 1차 rule refinement`: 완료
- `Step 3 casebook`: 완료
- `Step 3 preview / evaluate 재확인`: 완료

따라서 Step 3는 현재 기준으로 닫고,
다음 active step을 `Step 4. split health refinement`로 넘기는 것이 맞다.
