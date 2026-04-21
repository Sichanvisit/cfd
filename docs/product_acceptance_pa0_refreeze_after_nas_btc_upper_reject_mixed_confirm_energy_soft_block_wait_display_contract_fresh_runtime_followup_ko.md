# Product Acceptance PA0 Refreeze After NAS/BTC Upper-Reject Mixed-Confirm Energy-Soft-Block Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## fresh runtime 확인 결과

post-restart short watch 기준으로는
fresh exact `NAS/BTC + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
row가 아직 다시 잡히지 않았다.

반면 같은 시점에서 XAU mixed-confirm energy row는 계속 아래 contract로 기록됐다.

- `WAIT`
- `wait_check_repeat`
- `xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

이건 이번 logging surface와 wait-contract 경로 자체는 살아 있다는 뜻이다.

## 현재 의미

이번 follow-up의 핵심은 다음이다.

- NAS/BTC mixed energy mirror contract는 code / tests 기준으로는 반영 완료
- fresh exact row direct evidence는 아직 없음
- 그래서 PA0 latest `must_block 12`는 old blank backlog를 계속 읽는 상태

## 다음 체크 포인트

다음엔 아래만 보면 된다.

- `entry_decisions.csv` fresh row에서
  - `symbol in {BTCUSD, NAS100}`
  - `check_reason = upper_reject_mixed_confirm`
  - `blocked_display_reason = energy_soft_block`
  - `chart_display_reason in {nas_, btc_..._energy_soft_block_as_wait_checks}`

이게 한 번이라도 찍히면
그 뒤 refreeze에서 `must_block 12 -> 0` 확인으로 바로 이어질 가능성이 높다.
