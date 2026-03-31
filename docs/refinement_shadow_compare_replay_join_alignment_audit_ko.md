# Shadow Compare Replay Join Alignment / Source Scope Audit

## 1. 목적

이 문서는 shadow compare 품질개선 트랙에서
`replay join alignment / source scope`를 실제 산출물 기준으로 점검한 감사 메모다.

핵심 질문은 두 가지였다.

- 왜 `missing_replay_join`가 대부분인가
- 왜 `replay_latest_mtime`은 최신처럼 보이는데 실제 join은 거의 안 붙는가

## 2. 기준 산출물

- shadow compare:
  - [semantic_shadow_compare_report_20260326_180317.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_180317.json)
- preview audit:
  - [semantic_preview_audit_20260326_180401.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_180401.json)
- current preview build manifest:
  - [semantic_v1_dataset_build_20260326_163015_945811.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_build_20260326_163015_945811.json)

## 3. 핵심 관찰

### 3-1. entry_decisions와 default replay source의 시간 범위가 다르다

current entry decisions 기준:

- first: `2026-03-25T01:06:14`
- last: `2026-03-26T18:00:06`

shadow compare default source:

- [replay_intermediate](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate)

이 디렉터리에는 최신 mtime 파일도 있지만,
최근 파일 목록을 보면 production replay만 있는 것이 아니다.

대표적으로 최신 파일은:

- `replay_dataset_rows_r2_audit_entered.jsonl`
- `replay_dataset_rows_r2_audit.jsonl`
- 그 다음은 `2026-03-22` 계열 대용량 replay rows

즉 `replay_latest_mtime`만 보면 최신처럼 보이지만,
실제 source scope는

- audit용 replay
- 2026-03-22 시점 replay

가 섞여 있는 상태다.

### 3-2. current preview build도 현재 live row용 replay를 보고 있지 않다

current preview build manifest 기준 replay source:

- [replay_dataset_rows_20260321_150851.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate_legacy_20260311_175516_mt5\replay_dataset_rows_20260321_150851.jsonl)

즉 current preview 평가 자체도
현재 live `entry_decisions.csv` 전체와 같은 시간 범위를 보는 구조는 아니다.

### 3-3. 최신 shadow compare에서 실제 dominant 원인은 join 부재다

latest shadow compare 기준:

- `shadow_available_rows = 22839`
- `matched_replay_rows = 310`
- `missing_replay_join_rows = 22529`
- `scorable_shadow_rows = 0`
- `transition_status_not_valid = 310`

즉 현재 scorable이 0인 가장 큰 이유는:

1. 대부분의 live shadow row가 replay에 아예 안 붙고
2. 붙는 소수 row도 `INSUFFICIENT_FUTURE_BARS`

이기 때문이다.

## 4. 결론

이번 audit의 결론은 명확하다.

### 결론 A

현재 shadow compare의 1차 병목은 `trace quality` 이전에
`replay source scope mismatch`다.

### 결론 B

`replay_latest_mtime`이 최신처럼 보이는 것은
실제 live coverage가 최신이라는 뜻이 아니라,
`r2_audit` 같은 최근 파일이 섞여 있기 때문이다.

### 결론 C

따라서 다음 단계는 단순히 threshold를 만지거나
shadow compare label을 고치는 것이 아니라,

- 어떤 replay source를 compare에 써야 하는지
- live row와 같은 scope로 제한할 것인지
- audit용 replay를 production compare source에서 분리할 것인지

를 먼저 정해야 한다.

## 5. 권장 다음 액션

### 1. replay source scope를 분리한다

권장:

- `shadow compare production source`
- `audit / r2_audit source`

를 분리한다.

즉 `data/datasets/replay_intermediate`를 그대로 다 긁지 말고,
compare에 쓸 소스를 명시적으로 선택하게 하는 편이 맞다.

### 2. compare window를 time-aligned 하게 제한한다

권장:

- current live entry rows 전체가 아니라
- replay source가 실제로 커버하는 시간 범위로 compare window를 제한

그러면 `missing_replay_join`가 구조적으로 줄어든다.

### 3. 그 다음에야 trace quality audit이 의미가 커진다

현재는 fallback-heavy only도 문제지만,
join이 거의 다 비는 상태에서 trace quality를 먼저 손보면
우선순위가 틀어질 수 있다.

## 6. 실무 해석

지금 shadow compare warning은
“모델이 나쁘다”는 경고가 아니라,

“비교에 쓰는 replay source 범위가 current live row와 안 맞는다”

는 경고에 더 가깝다.

즉 다음 액션은 모델 조정이 아니라
`compare source alignment` 정리다.
