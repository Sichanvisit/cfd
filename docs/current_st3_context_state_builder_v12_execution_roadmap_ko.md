# ST3 Context State Builder v1.2 실행 로드맵

## 목표

`HTF + previous box + optional share`를 하나의 context contract로 조립해,
이후 `ST4 runtime payload`, `ST7 detector bridge`, `ST8 notifier bridge`가 같은 문맥을 읽게 한다.


## ST3-1. 입력 계약 고정

할 일:

- `htf_state`
- `previous_box_state`
- `share_state`
- `proxy_state`
- `consumer_check_side`

입력 모양 고정

완료 기준:

- builder 입력이 문서와 코드에서 일치


## ST3-2. conflict 계산 구현

할 일:

- `AGAINST_HTF`
- `AGAINST_PREV_BOX`
- `AGAINST_PREV_BOX_AND_HTF`
- `CONTEXT_MIXED`
- primary + flags + intensity + score

완료 기준:

- `context_conflict_state`
- `context_conflict_flags`
- `context_conflict_intensity`
- `context_conflict_score`
반환


## ST3-3. late chase 구현

할 일:

- reason별 최소 규칙
- confidence
- trigger_count

완료 기준:

- `late_chase_risk_state`
- `late_chase_reason`
- `late_chase_confidence`
- `late_chase_trigger_count`
반환


## ST3-4. share merge 보강

할 일:

- optional share merge
- `cluster_share_symbol_band`
- `share_context_label_ko`

완료 기준:

- share 입력이 있으면 builder가 band/label까지 정리


## ST3-5. 테스트

할 일:

- HTF + previous box 동시 conflict
- late chase primary
- mixed context
- share band inference

완료 기준:

- focused pytest 통과
- `py_compile` 통과
