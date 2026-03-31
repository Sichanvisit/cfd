# Shadow Compare Compare Source Alignment Reconfirm Memo

## 1. 목적

이 문서는 `compare source alignment policy` 구현 결과를
실제 latest shadow compare report 기준으로 다시 확인한 메모다.

기준 산출물:

- [semantic_shadow_compare_report_20260326_183259.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_183259.json)
- [semantic_preview_audit_20260326_183400.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_183400.json)

## 2. 이번 구현에서 바뀐 것

구현 owner:

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)

이번에 반영한 핵심은 네 가지다.

1. replay source를 `production compare source / audit_test_source / legacy_snapshot_source`로 분류한다.
2. default compare에서는 audit/test/legacy 계열을 제외하고 production source만 선택한다.
3. compare window를 selected replay coverage 범위로 정렬한다.
4. report에 selected/excluded file, replay coverage, alignment reason을 같이 드러낸다.

## 3. 실제 latest 결과

latest source scope 기준:

- `selection_mode = default_production_only`
- `inventory_file_count = 12`
- `selected_file_count = 10`
- `excluded_file_count = 2`
- excluded files:
  - `replay_dataset_rows_r2_audit.jsonl`
  - `replay_dataset_rows_r2_audit_entered.jsonl`

latest replay coverage 기준:

- `replay_first_time = 2026-03-06T20:53:25`
- `replay_last_time = 2026-03-22T17:37:13`

latest live entry range 기준:

- `entry_first_time = 2026-03-25T01:06:14`
- `entry_last_time = 2026-03-26T18:29:36`

alignment 결과:

- `aligned_entry_rows = 0`
- `dropped_entry_rows = 23735`
- `alignment_status = no_entry_overlap_with_replay_coverage`
- `alignment_reason = entry_rows_outside_replay_coverage`

즉 이번 구현 이후에는
예전처럼 `missing_replay_join` 2만 건 이상으로 보고되는 대신,
현재 production replay source가 live entry window를 전혀 커버하지 못한다는 사실이
report에서 직접 보이게 되었다.

## 4. preview audit 해석

preview audit 기준:

- `shadow_compare.status = warning`
- issues:
  - `shadow_compare_rows_unavailable`
  - `shadow_compare_shadow_rows_unavailable`
  - `shadow_compare_scorable_rows_below_gate`
  - `shadow_compare_candidate_thresholds_missing`

이 warning은 더 이상 "shadow compare 내부 계산식이 약하다"는 뜻이 아니다.

현재 뜻은:

- default production compare source는 잘 골랐고
- audit source도 잘 제외됐지만
- compare 대상 production replay 자체가 현재 live window보다 오래되어서
- 비교 가능한 row가 0이라는 뜻이다.

## 5. 결론

이번 단계에서 `compare source alignment policy` 구현 자체는 완료로 봐도 된다.

왜냐하면:

- source 분류가 코드로 고정됐고
- default exclude 규칙이 테스트로 잠겼고
- compare window alignment가 실제 latest report에 반영됐고
- source mismatch가 report에서 직접 드러나기 때문이다.

지금 남은 다음 병목은 policy가 아니라 source freshness다.

즉 다음 액션은 보통 이 둘 중 하나다.

1. current live compare용 production replay source를 새로 만든다.
2. shadow compare가 바라보는 production replay source 경로를 live-aligned source로 분리한다.

한 줄로 정리하면:

`shadow compare 품질 문제`가 아니라
`production compare replay coverage가 현재 live window를 못 따라오고 있는 문제`
가 다음 직접 owner다.
