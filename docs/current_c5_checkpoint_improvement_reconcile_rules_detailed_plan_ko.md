# Current C5 Checkpoint Improvement Reconcile Rules Detailed Plan

## 목적

`C5`는 reconcile을 단순 placeholder에서 한 단계 올려,

- `same-scope duplicate governance group`
- `late callback invalidation`

을 canonical하게 잡아내는 단계다.

## 이번 단계에서 넣는 규칙

### 1. same-scope conflict

- 같은 `scope_key`에 대해 `pending / held / approved` group이 여러 개 있으면 conflict로 본다
- 최신 group을 canonical로 보고, 오래된 `pending / held` duplicate는 안전하게 `cancelled` 처리한다
- `approved` duplicate는 자동 취소하지 않고 report에만 남긴다

### 2. late callback invalidation

- callback이 있는 `approve / hold / reject` action 중
  현재 group의 `approval_id`와 action의 `approval_id`가 다르면
  late callback invalidation으로 센다
- 이 단계에선 report/health 가시화만 하고 group state를 다시 바꾸진 않는다

## board 반영

- `same_scope_conflict_count`를 master board에 올린다
- `reconcile_backlog_count`는
  - approved apply backlog
  - stale actionable
  - same-scope conflict
  를 합산한다

## 이번 단계에서 의도적으로 안 하는 것

- late callback 자동 정리/삭제
- same-scope `approved` duplicate 자동 취소
- cross-symbol merge

## 다음 연결점

- live runner에서 conflict가 실제로 자주 뜨는지 관찰
- 필요하면 `late callback repair`와 `superseded approval invalidation`을 다음 step에서 추가
