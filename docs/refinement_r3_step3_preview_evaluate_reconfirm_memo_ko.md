# R3 Step 3 Preview/Evaluate Reconfirm Memo

## 1. 목적

이 문서는 `R3 Step 3. timing target refinement` 1차 조정이
실제 preview/evaluate 기준에서도 유의미한 개선이었는지
같은 legacy baseline 위에서 다시 확인한 메모다.


## 2. 재확인 기준

비교는 default export/replay 디렉터리 전체가 아니라,
기존 semantic preview latest가 사용했던 동일 legacy 소스 쌍으로 고정했다.

- feature source:
  - `C:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.legacy_20260311_175516.replay.parquet`
- replay source:
  - `C:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate_legacy_20260311_175516_mt5\replay_dataset_rows_20260321_150851.jsonl`

재생성 산출물:

- dataset output:
  - `C:\Users\bhs33\Desktop\project\cfd\data\datasets\semantic_v1_r3_step3_20260326`
- model output:
  - `C:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_step3_20260326`
- build manifest:
  - `C:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_build_20260326_144557_549824.json`
- preview audit:
  - `C:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_144716.json`


## 3. 실행 경로

이번 재확인은 아래 순서로 진행했다.

1. explicit legacy feature/replay 쌍으로 semantic dataset 재빌드
2. `timing / entry_quality / exit_management` 모델 재학습
3. 새 `metrics.json`과 build manifest로 preview audit 재생성
4. 이전 latest audit과 timing 지표 직접 비교


## 4. 결과 요약

비교 기준:

- old:
  - `C:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260321_211011.json`
- new:
  - `C:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_144716.json`

timing 결과:

| metric | old | new | delta |
| --- | ---: | ---: | ---: |
| rows | 2351 | 2351 | 0 |
| accuracy | 0.636325 | 0.636325 | 0.000000 |
| auc | 0.610649 | 0.633218 | +0.022570 |
| brier_score | 0.343885 | 0.342965 | -0.000920 |
| calibration_error | 0.338382 | 0.337823 | -0.000559 |
| split_health_status | healthy | healthy | 유지 |

관찰 포인트:

- row 수와 test class balance는 동일했다.
- accuracy는 그대로였지만, AUC가 `+0.02257` 개선됐다.
- brier score와 calibration error도 소폭 개선됐다.
- join coverage는 `1.0`으로 유지됐다.
- promotion gate는 old/new 모두 `pass`였고,
  warning은 `entry_quality:split_health_warning`, `exit_management:split_health_warning` 그대로였다.


## 5. 해석

이번 Step 3 1차 조정은
`애매한 row를 억지로 positive / negative로 접지 않는` 보수적 refinement였는데,
같은 baseline에서 timing discrimination은 오히려 좋아졌다.

즉 이번 veto는

- sample 수를 무리하게 줄이거나
- target을 지나치게 흐리게 만들지 않으면서
- timing target의 설명 가능성을 높이는 방향으로 작동했다.

현재 기준으로는
`Step 3 timing target 1차 refinement`를 수용 가능한 상태로 볼 수 있다.


## 6. 남은 리스크

이번 재확인은 `legacy source_generation` 기준이다.

따라서 다음 단계에서 여전히 봐야 할 것은:

- split health warning이 남아 있는 `entry_quality`, `exit_management`
- `legacy / mixed / modern` 차이가 timing 이외 target에서 어떻게 드러나는지
- Step 4 split health refinement에서 holdout 구성의 질을 더 명시적으로 잠그는 일


## 7. 현재 판단

- Step 3 1차 rule refinement: 수용
- Step 3 preview/evaluate reconfirm: 완료
- 다음 active step: `Step 4. split health refinement`
