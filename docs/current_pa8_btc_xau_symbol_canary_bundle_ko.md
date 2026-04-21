# PA8 BTC/XAU Symbol Canary Bundle

## 목적

- NAS100 전용으로 먼저 열어둔 PA8 action-only canary 체인을
  BTCUSD / XAUUSD에도 같은 수준으로 연결한다.
- 단, readiness는 심볼별 실제 preview 품질과 sample floor로 나눈다.
- scene bias는 계속 제외하고 action-only bounded canary로만 본다.

## 이번 번들에서 올리는 단계

1. symbol action preview
2. provisional canary review packet
3. execution checklist
4. activation packet
5. activation human review
6. monitoring packet
7. rollback review packet
8. activation apply
9. first window observation
10. closeout decision

## BTCUSD candidate

- scope:
  - `protective_exit_surface`
  - `RECLAIM_CHECK`
  - `active_open_loss`
  - baseline `PARTIAL_EXIT`
  - candidate `WAIT`
- 의도:
  - `full_exit_gate_not_met_trim_fallback`로 과하게 trim 되는 protective reclaim loss를
    bounded WAIT canary로 검토
- sample floor:
  - `50`

## XAUUSD candidate

- scope:
  - `protective_exit_surface`
  - `RECLAIM_CHECK`
  - `open_loss_protective | active_open_loss`
  - baseline `PARTIAL_EXIT`
  - candidate `WAIT`
- 의도:
  - XAU reclaim loss protective family의 과한 trim을
    bounded WAIT canary로 검토
- sample floor:
  - `25`

## 핵심 원칙

- 공통 chain을 쓰되 심볼별 family는 좁게 고정한다.
- size change는 없다.
- new entry logic은 없다.
- scene bias는 계속 preview-only다.
- live row가 없으면 first window는 `preview_seed_reference`로만 시작한다.

## 기대 상태

- BTCUSD:
  - NAS처럼 ready 또는 active 상태까지 올라갈 가능성이 높다.
- XAUUSD:
  - overall symbol review는 support일 수 있어도,
    scoped protective reclaim WAIT candidate는 별도 bounded canary chain으로 본다.
