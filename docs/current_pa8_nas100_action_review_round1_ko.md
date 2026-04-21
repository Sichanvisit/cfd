# PA8 NAS100 Action Review Round 1

## Goal

PA8 action-only review checklist에서 `NAS100`이 첫 번째 primary review 대상이므로,
실제 resolved dataset 기준으로 hold precision blocker가 어디에서 발생하는지 casebook 형태로 다시 푼다.

이번 단계는 rule patch가 아니라 review close-out 문서를 만드는 단계다.

## Inputs

- `checkpoint_pa8_action_review_checklist_latest.json`
- `checkpoint_dataset_resolved.csv`

## Expected output

- `checkpoint_pa8_action_review_nas100_latest.json`
- `checkpoint_pa8_action_review_nas100_latest.md`

## Review questions

1. `hold_precision_below_symbol_floor`를 가장 많이 만드는 mismatch family는 무엇인가
2. 그 family가 하나로 충분히 좁혀지는가
3. 현재 resolver reason이 무엇이며, hindsight는 무엇을 말하는가
4. 다음 단계가 곧바로 patch인지, 아니면 추가 review인지 결정할 수 있는가

## Round-1 exit criteria

- top mismatch cluster가 row count 기준으로 정리된다
- manual-exception 상위 family가 함께 요약된다
- next step이 `narrow patch candidate identified`인지 아니면 `more review needed`인지 문서화된다
