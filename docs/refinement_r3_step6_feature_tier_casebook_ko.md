# R3 Step 6 Feature Tier Casebook

## 1. 목적

이 문서는 `R3 Step 6. legacy feature tier refinement`의 1차 casebook이다.

이번 Step 6의 목표는
`legacy / mixed / modern` source에서
semantic dataset builder가 trace-quality feature를 어떻게 처리하는지
설명 가능한 기준으로 고정하는 것이다.

## 2. 이번 1차 변경 요약

기존 builder baseline은 아래와 같았다.

- `legacy`
  - `semantic_input_pack = enabled`
  - `trace_quality_pack = observed_only`
- 그 외
  - `semantic_input_pack = enabled`
  - `trace_quality_pack = enabled`

이번 1차에서는 이것을 조금 더 보수적으로 바꿨다.

- `legacy`
  - `trace_quality_pack = observed_only`
- `mixed`
  - `trace_quality_pack = observed_only`
- `unknown`
  - `trace_quality_pack = observed_only`
- `modern`
  - `trace_quality_pack = enabled`

즉 mixed를 더 이상 무조건 modern처럼 다루지 않고,
legacy 흔적이 섞여 있을 때는 observed-only로 보는 안전한 방향으로 고정했다.

추가로 summary/metrics에 아래 정보가 직접 남게 했다.

- `feature_tier_summary`
- `observed_only_dropped_feature_columns`

## 3. case 분류

### A. legacy source

예상 처리:

- `semantic_input_pack = enabled`
- `trace_quality_pack = observed_only`
- trace-quality all-missing은 build fail이 아니라 observed-only drop

실제 Step 6 legacy rebuild 기준:

- `source_generation = legacy`
- `feature_tier_summary.trace_quality_pack.mode = observed_only`
- `trace_quality_pack`
  - `candidate_count = 37`
  - `retained_count = 4`
  - `dropped_count = 33`
  - `observed_only_dropped_count = 33`

해석:

- legacy에서는 trace-quality가 비어도 이상이라기보다
  source 제약으로 보는 것이 맞고,
  Step 6은 그걸 숫자로 보이게 한 단계다.

### B. mixed source

예상 처리:

- `semantic_input_pack = enabled`
- `trace_quality_pack = observed_only`

왜 이렇게 보나:

- mixed는 modern만 있는 상태가 아니라
  legacy와 modern이 섞인 상태다.
- 이때 trace-quality all-missing을 바로 이상으로 잡으면
  mixed migration 단계에서 false warning이 커질 수 있다.

이번 Step 6에서는 mixed를 safer policy로 내려서,
우선은 `observed_only` 기준으로 고정했다.

테스트 근거:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
  - mixed source synthetic case에서
  - `source_generation = mixed`
  - `trace_quality_pack = observed_only`
  - `signal_age_sec`가 `observed_only_dropped_feature_columns`에 남는지 확인

### C. modern source

예상 처리:

- `semantic_input_pack = enabled`
- `trace_quality_pack = enabled`

해석:

- modern source에서 trace-quality는 builder가 기본적으로 기대하는 feature pack이다.
- 따라서 all-missing이면 legacy처럼 자연스러운 결손이 아니라
  upstream 문제일 가능성이 더 높다.

이번 1차에서는 modern의 mode 자체를 바꾸지 않았다.
즉 modern은 여전히 `enabled` 기준을 유지한다.

### D. unknown source

예상 처리:

- `trace_quality_pack = observed_only`

해석:

- unknown은 generation 판별이 불명확한 상태이므로
  Step 6 1차에서는 안전하게 observed-only로 두는 편이 낫다.

## 4. Step 6에서 새로 surface된 것

이번 단계 이후 dataset summary와 training metrics에는 아래가 더 잘 보인다.

- `feature_tier_summary`
  - tier별 mode
  - candidate_count
  - retained_count
  - dropped_count
  - observed_only_dropped_count
- `observed_only_dropped_feature_columns`

즉 이제는 단순히
"몇 개가 dropped 되었나"만 보는 게 아니라,
"그 dropped가 observed-only 정책 때문에 생긴 것인지"
를 바로 읽을 수 있다.

## 5. 코드 / 테스트 근거

코드:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
  - `_feature_tier_policy`
  - `_resolve_dataset_feature_policy`
  - `_write_dataset_artifact`
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
  - legacy summary fallback
  - `dataset_feature_tier_summary`
  - `dataset_observed_only_dropped_feature_columns`

테스트:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
  - legacy trace-quality drop visibility
  - mixed trace-quality observed-only handling
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)
  - old summary fallback compatibility

## 6. 현재 판단

현재 Step 6의 1차 결과는 이렇게 정리할 수 있다.

- mixed를 modern처럼 과하게 다루지 않도록 안전한 정책으로 낮췄다.
- legacy/current preview는 그대로 유지된다.
- summary/metrics에서 feature tier 상태가 더 잘 보인다.
- old summary fixture도 backward compatible하게 읽힌다.

즉 Step 6은
`feature tier 규칙을 뒤집은 단계`라기보다,
`mixed/legacy 처리를 더 안전하게 만들고 visibility를 높인 단계`로 보는 게 맞다.
