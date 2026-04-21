# OC3. PA8 Rollback / Approval Cleanup Lane 상세 계획

## 목적

`OC3`의 목적은 `PA8`이 live row를 조금 쌓았더라도 실제로 앞으로 못 가는 이유가
`rollback required`인지, `Telegram approval backlog`인지, 아니면 둘이 같이 얽힌 것인지를
운영자가 한 번에 읽을 수 있게 만드는 것입니다.

지금 기준으로는 `NAS100`이 대표 사례입니다.

- `closeout_state = ROLLBACK_REQUIRED`
- master board `blocking_reason = approval_backlog_pending`
- Telegram backlog에는 `CANARY_ROLLBACK_REVIEW`가 실제로 pending

즉 `OC3`는 "왜 아직 closeout review/apply로 못 넘어가는가"를
`rollback`과 `approval cleanup` 관점에서 따로 떼어 보여주는 lane입니다.

---

## 왜 별도 lane이 필요한가

기존에도 관련 정보는 흩어져 있었습니다.

- master board
- PA8 closeout runtime
- Telegram actionable approval group

하지만 운영자가 바로 보고 싶은 건 이런 질문입니다.

- 지금 막는 건 rollback review인가, approval backlog인가
- Telegram에서 실제로 처리해야 하는 review prompt가 무엇인가
- NAS/BTC/XAU 중 어느 심볼을 먼저 정리해야 하는가
- pending approval을 치우면 바로 closeout review로 갈 수 있는가

이걸 `OC3`에서 한 lane으로 묶습니다.

---

## 입력 근거

### 1. Master board

- `approval_backlog_count`
- `apply_backlog_count`
- `stale_actionable_count`
- `pa8_primary_focus_symbol`

### 2. PA8 closeout runtime

- `rollback_required_symbol_count`
- `review_candidate_symbol_count`
- `apply_candidate_symbol_count`
- symbol row의
  - `closeout_state`
  - `first_window_status`
  - `rollback_required`
  - `closeout_review_candidate`

### 3. Telegram actionable groups

- `pending`
- `held`

여기서 `CANARY_*` review를 우선 `PA8 관련 actionable backlog`로 봅니다.

---

## lane 상태 정의

- `ROLLBACK_APPROVAL_PENDING`
  - rollback required symbol에 대한 Telegram review가 pending/held 상태
- `ROLLBACK_REVIEW_MISSING_PROMPT`
  - rollback required는 감지됐지만 대응 review prompt가 backlog에 없음
- `CLOSEOUT_REVIEW_PENDING`
  - closeout review 자체가 backlog에 남아 있음
- `OTHER_ACTIONABLE_REVIEW_PENDING`
  - 같은 심볼의 다른 actionable review가 backlog에 남아 있음
- `READY_FOR_CLOSEOUT_REVIEW`
  - rollback/approval cleanup은 비어 있고 closeout review packet만 남아 있음
- `READY_FOR_CLOSEOUT_APPLY`
  - closeout apply 직전 상태
- `WAITING_LIVE_WINDOW`
  - approval cleanup보다 live window 증거 누적이 먼저 필요
- `NO_CLEANUP_REQUIRED`
  - 현재 rollback/approval cleanup blocker가 보이지 않음

---

## 출력 아티팩트

- `data/analysis/shadow_auto/checkpoint_pa8_rollback_approval_cleanup_lane_latest.json`
- `data/analysis/shadow_auto/checkpoint_pa8_rollback_approval_cleanup_lane_latest.md`

오케스트레이터 watch payload에도 `pa8_rollback_approval_cleanup` 블록으로 같이 들어갑니다.

---

## 운영 해석

운영자가 이 lane에서 먼저 볼 것은 아래 4개입니다.

1. `overall_cleanup_state`
2. `primary_cleanup_symbol`
3. `approval_backlog_count / rollback_approval_pending_count`
4. `Relevant Approval Groups`

즉 `OC3`는

`PA8이 막힌 이유를 "rollback review가 남아서인지", "approval backlog가 남아서인지", "둘 다인지"로 분해해서 보여주는 cleanup 전용 lane`

입니다.

---

## 완료 기준

- rollback/approval cleanup 상태가 JSON/Markdown으로 출력됨
- symbol row마다 cleanup lane 상태가 보임
- Telegram actionable group이 관련 심볼/리뷰 타입으로 같이 surface됨
- orchestrator watch에서 `pa8_rollback_approval_cleanup`가 같이 보임
