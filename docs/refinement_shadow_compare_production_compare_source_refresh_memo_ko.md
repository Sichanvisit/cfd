# Shadow Compare Production Compare Source Refresh Memo

## 1. 목적

이 문서는 `production compare replay source refresh / 분리` 구현 결과를 정리한 메모다.

기준 파일:

- [refresh_shadow_compare_production_source.py](c:\Users\bhs33\Desktop\project\cfd\scripts\refresh_shadow_compare_production_source.py)
- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- [semantic_shadow_compare_report_20260326_185628.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_185628.json)
- [semantic_preview_audit_20260326_185716.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_185716.json)

## 2. 이번에 구현한 것

### 2-1. dedicated production compare source

새 기본 compare source 디렉터리:

- [replay_intermediate_compare_live](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate_compare_live)

[shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)는 이제

1. `replay_intermediate_compare_live`에 replay rows가 있으면 그 경로를 기본 source로 사용하고
2. 없으면 기존 [replay_intermediate](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate)로 fallback 한다.

### 2-2. refresh script

새 스크립트:

- [refresh_shadow_compare_production_source.py](c:\Users\bhs33\Desktop\project\cfd\scripts\refresh_shadow_compare_production_source.py)

역할:

- 기존 dedicated compare JSONL 정리
- latest [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv) 기준 replay rows 재생성
- dedicated compare source 디렉터리에 최신 JSONL 1개 기록
- latest manifest 기록

latest manifest:

- [shadow_compare_production_source_manifest_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\shadow_compare_production_source_manifest_latest.json)

## 3. 실제 refresh 결과

latest refresh summary 기준:

- dataset path:
  - [replay_dataset_rows_20260326_185212.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate_compare_live\replay_dataset_rows_20260326_185212.jsonl)
- `rows_written = 24429`
- `future_bar_resolution = none`

즉 dedicated compare source는 현재 live entry 범위를 기준으로 새로 생성됐다.

## 4. refresh 후 shadow compare 결과

latest compare 기준:

- `replay_source_path = replay_intermediate_compare_live`
- `selected_file_count = 1`
- `excluded_file_count = 0`
- `aligned_entry_rows = 24429`
- `matched_replay_rows = 24429`
- `missing_replay_join_rows = 0`
- `dropped_entry_rows = 15`

즉 이전 병목이던 `source scope mismatch`와 `missing_replay_join`은 사실상 해소됐다.

## 5. 지금 남은 병목

latest compare summary 기준:

- `scorable_shadow_rows = 0`
- `unscorable_shadow_rows = 24429`
- `semantic_earlier_enter_rows = 24361`

latest preview audit 기준 warning:

- `shadow_compare:shadow_compare_scorable_rows_below_gate`

즉 다음 병목은 더 이상 replay source freshness가 아니다.

이제 남은 직접 owner는:

1. `transition_label_status / management label status`가 왜 scoreable로 안 올라오는지
2. `fallback_heavy` / compare label 분포가 왜 한쪽으로 몰리는지

를 보는 쪽이다.

## 6. 결론

이번 단계로 다음 두 가지는 완료로 봐도 된다.

1. production compare replay source 분리
2. current live 기준 replay source refresh 경로 확보

그래서 이제 shadow compare 품질개선의 다음 초점은
`join/source`가 아니라
`label quality / scoreable transition quality`
로 옮겨가도 된다.
