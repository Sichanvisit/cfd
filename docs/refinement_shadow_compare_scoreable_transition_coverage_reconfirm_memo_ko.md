# Shadow Compare Scoreable Transition Coverage Reconfirm Memo

## 1. 목적

이 문서는 `scoreable transition coverage` 단계의 실제 결과를 다시 확인한 메모다.

기준 산출물:

- [shadow_compare_production_source_manifest_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\shadow_compare_production_source_manifest_latest.json)
- [semantic_shadow_compare_report_20260326_190949.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_190949.json)
- [semantic_preview_audit_20260326_191035.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_191035.json)

## 2. 이번 단계에서 한 것

1. [refresh_shadow_compare_production_source.py](c:\Users\bhs33\Desktop\project\cfd\scripts\refresh_shadow_compare_production_source.py)를
   `--fetch-mt5-future-bars`로 실행했다.
2. dedicated compare source를 future bars 포함 상태로 다시 만들었다.
3. 기본 `shadow compare`를 재생성했다.
4. 그 report를 명시로 preview audit에 다시 연결했다.

## 3. 실제 refresh 결과

latest compare source manifest 기준:

- `dataset_path = replay_dataset_rows_20260326_190500.jsonl`
- `rows_written = 24732`
- `future_bar_path = data/market_bars/future_bars_entry_decisions_m15.csv`
- `future_bar_resolution = explicit`

즉 이번 단계에서 compare source는 더 이상 `future_bar_resolution = none`이 아니다.

## 4. compare 결과 변화

baseline(이전)과 비교하면:

### 이전

- `matched_replay_rows = 24429`
- `missing_replay_join_rows = 0`
- `scorable_shadow_rows = 0`
- `transition_label_status = INSUFFICIENT_FUTURE_BARS only`

### 이번

- `matched_replay_rows = 24732`
- `missing_replay_join_rows = 0`
- `scorable_shadow_rows = 22582`
- `unscorable_shadow_rows = 2150`
- `transition_label_status_counts`
  - `VALID = 22582`
  - `AMBIGUOUS = 1166`
  - `INSUFFICIENT_FUTURE_BARS = 984`

즉 이번 단계의 핵심 성과는:

- `scoreable row가 0에서 22582로 증가`
- `future bars 부재`가 주 병목이 아니라는 점을 확인

이다.

## 5. preview audit 결과

latest preview audit 기준:

- `promotion_gate.status = pass`
- `shadow_compare_status = healthy`
- shadow compare 관련 warning은 사라졌다
- 남은 warning은
  - `entry_quality:split_health_warning`
  - `exit_management:split_health_warning`

즉 shadow compare plumbing / source / scoreable coverage는
현재 promotion gate 기준으로는 healthy 상태까지 올라왔다.

## 6. 지금 남은 직접 병목

이번 단계로 `scoreable coverage`는 해결됐지만
compare quality 자체는 아직 거칠다.

latest compare 기준:

- `semantic_enter_rows = 24732`
- `semantic_earlier_enter_rows = 24659`
- `semantic_precision = 0.015322`
- `semantic_false_positive_rate = 0.984678`
- `trace_quality_counts = fallback_heavy only`

즉 다음 직접 owner는 이제:

1. `trace quality audit`
2. `semantic enter compare policy refinement`

이다.

한 줄로 말하면:

`scoreable row 부족`은 해결됐고,
이제 남은 건 `왜 거의 전부 earlier-enter로 찍히는지`와
`왜 trace quality가 전부 fallback_heavy인지`를 파는 단계다.

## 7. 결론

이번 단계는 완료로 봐도 된다.

이유:

- future bars가 compare source에 실제로 붙었고
- scoreable rows가 충분히 생겼고
- preview audit에서도 shadow compare가 `healthy`로 올라왔기 때문이다.

다음 active step은
`S2 trace quality audit`
또는 바로 이어지는
`S3 compare policy refinement`
중에서, 우선순위상 S2부터 보는 쪽이 더 자연스럽다.
