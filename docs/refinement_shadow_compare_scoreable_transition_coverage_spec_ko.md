# Shadow Compare Scoreable Transition Coverage Spec

## 1. 목적

이 문서는 `production compare replay source` 분리 이후 새로 드러난
`scoreable transition coverage` 병목을 다루는 전용 spec이다.

현재 latest 기준으로:

- replay source freshness / join mismatch는 해결됐다
- 그러나 `transition_label_status = INSUFFICIENT_FUTURE_BARS`가 100%라서
  `scorable_shadow_rows = 0` 상태가 유지된다

즉 다음 직접 owner는
`future bar backed replay coverage`다.

## 2. 기준 산출물

- [semantic_shadow_compare_report_20260326_185628.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_185628.json)
- [semantic_preview_audit_20260326_185716.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_185716.json)
- [shadow_compare_production_source_manifest_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\shadow_compare_production_source_manifest_latest.json)

## 3. 현재 병목 요약

latest compare 기준:

- `matched_replay_rows = 24429`
- `missing_replay_join_rows = 0`
- `scorable_shadow_rows = 0`
- `transition_label_status_counts = INSUFFICIENT_FUTURE_BARS only`
- `scorable_exclusion_reason_counts = transition_status_not_valid only`

latest compare source manifest 기준:

- `future_bar_resolution = none`
- `future_bar_path = ""`

즉 current live compare source는
join/source alignment는 맞지만
transition label을 scoreable하게 만들 future bars가 빠져 있다.

## 4. 이번 단계의 목표

목표는 단순히 future bars 파일을 하나 더 만드는 것이 아니다.

실제 목표는:

1. dedicated production compare replay source가
   transition horizon을 scoreable하게 만드는 future bars를 함께 갖게 만들고
2. refresh 결과가 manifest/report에서 바로 보이게 하며
3. 실제 `scorable_shadow_rows`가 0에서 벗어나는지 확인하는 것이다.

## 5. 직접 owner

### 1차 owner

- [refresh_shadow_compare_production_source.py](c:\Users\bhs33\Desktop\project\cfd\scripts\refresh_shadow_compare_production_source.py)
- [fetch_mt5_future_bars.py](c:\Users\bhs33\Desktop\project\cfd\scripts\fetch_mt5_future_bars.py)
- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py)

### 2차 owner

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)

## 6. 이번 단계에서 볼 관측 축

### 6-1. compare source manifest

- `future_bar_resolution`
- `future_bar_path`
- `rows_written`
- `replay_build_manifest_path`

### 6-2. compare report

- `scorable_shadow_rows`
- `transition_label_status_counts`
- `scorable_exclusion_reason_counts`
- `trace_quality_counts`

### 6-3. preview audit

- `shadow_compare_status`
- `shadow_compare_ready`
- `shadow_compare warning issues`

## 7. 권장 실행 순서

### Phase T0. Baseline snapshot

현재 `future_bar_resolution = none`과
`INSUFFICIENT_FUTURE_BARS only` 상태를 기준선으로 고정한다.

### Phase T1. Future bar backed compare source refresh

`refresh_shadow_compare_production_source.py`를
`--fetch-mt5-future-bars` 모드로 실행해서
dedicated compare source를 다시 만든다.

### Phase T2. Compare regeneration

기본 `shadow compare`를 다시 실행해
새 compare source 기준 report를 생성한다.

### Phase T3. Preview audit reconfirm

새 compare report를 기준으로 preview audit을 다시 돌려
warning이 어떻게 바뀌는지 본다.

### Phase T4. Result memo

결과를:

- scoreable row 증가
- 여전히 `INSUFFICIENT_FUTURE_BARS`
- 다른 status로 병목 이동

중 어디로 이동했는지 정리한다.

## 8. 이번 단계에서 하지 않을 것

- target fold 수정
- split health 수정
- promotion threshold 수정
- chart/runtime execution rule 수정

## 9. 완료 기준

아래 중 하나가 만족되면 이번 단계를 닫는다.

1. `future_bar_resolution`이 `none`에서 벗어나고
   `scorable_shadow_rows > 0`이 된다.
2. `future bars`를 붙였는데도 여전히 0이면
   그 다음 병목이 무엇인지 report와 memo로 바로 설명 가능하다.

즉 핵심은
`scoreable row를 실제로 늘리거나, 못 늘리는 직접 이유를 더 좁히는 것`
이다.
