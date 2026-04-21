# PA8 Non-Apply Audit 상세 계획

## 목표

PA8 closeout가 왜 실제 apply까지 못 가는지를 심볼별로 한 장에서 읽을 수 있게 만든다.

## 왜 지금 필요한가

- 현재 `PA8`는 canary 자체는 살아 있는데 `observed_window_row_count = 0`으로 멈춰 있다.
- 겉으로는 모두 `HOLD_CLOSEOUT_PENDING_LIVE_WINDOW`로만 보여서, 실제 병목이
  - canary 비활성인지
  - post-activation live row 부재인지
  - sample floor 미달인지
  - guardrail regression인지
  를 빠르게 구분하기 어렵다.

## 입력 아티팩트

- `checkpoint_pa8_canary_refresh_board_latest.json`
- 내장 `refreshed_payloads`
  - `first_window.summary`
  - `closeout.summary`
  - `active_triggers`

## 핵심 규칙

심볼별로 아래를 audit row로 고정한다.

- `activation_apply_state`
- `first_window_status`
- `closeout_state`
- `live_observation_ready`
- `observed_window_row_count`
- `seed_reference_row_count`
- `sample_floor`
- `active_trigger_count`
- `active_triggers`
- `primary_non_apply_reason_code`
- `primary_non_apply_reason_ko`
- `recommended_next_action`

primary reason 우선순위:

1. `canary_not_active`
2. `no_post_activation_live_rows`
3. `live_rows_below_sample_floor`
4. `guardrail_trigger_active`
5. `live_observation_not_ready`
6. `closeout_review_not_reached`

## 이번 단계에서 하지 않는 것

- closeout threshold 변경
- sample floor 완화
- guardrail 완화
- runtime behavior 수정

즉 이번 단계는 오직 `왜 아직 apply가 안 되는지 설명하는 audit`이다.

## 산출물

- `checkpoint_pa8_non_apply_audit_latest.json`
- `checkpoint_pa8_non_apply_audit_latest.md`

## 완료 조건

- 심볼별 primary blocker가 한국어로 바로 읽힌다
- `seed는 충분한데 live row가 0인지`, `sample floor 미달인지`, `guardrail인지`가 분리된다
- 다음 조치가 심볼별로 명시된다
