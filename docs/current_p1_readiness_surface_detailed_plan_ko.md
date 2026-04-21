# P1 Readiness Surface 상세 계획

## 목표

최종 승인이나 승격이 아직 불가능한 항목을 `안 보이는 대기 상태`로 두지 않고,
`왜 아직 아닌지`, `무엇이 부족한지`, `다음에 뭘 보면 되는지`까지 같은 문법으로 드러낸다.

핵심 원칙은 이렇다.

- readiness는 곧바로 apply 하지 않는다
- readiness는 `observe -> report -> review -> apply` 중 현재 위치를 보여주는 표면이다
- readiness는 board JSON 안에만 묻어두지 않고 `master board`, `일간 PnL`, `체크/보고서 흐름`과 연결한다

## 대상

### 1. PA8 closeout readiness

보여줘야 할 것:

- symbol별 `READY_FOR_REVIEW / PENDING_EVIDENCE / BLOCKED`
- live window가 몇 개 쌓였는지
- 왜 아직 closeout review가 아닌지
- 다음 행동이 `계속 수집`, `review`, `degraded 복구` 중 무엇인지

### 2. PA9 handoff readiness

보여줘야 할 것:

- `handoff_state / review_state / apply_state`
- symbol별 `review candidate / apply candidate`
- PA8이 먼저 막고 있는지, review는 준비됐는지, apply 직전인지

### 3. reverse readiness

보여줘야 할 것:

- `READY_FOR_APPLY / PENDING_EVIDENCE / BLOCKED / NOT_APPLICABLE`
- pending reverse 후보가 있는지
- 아직 포지션이 열려서 기다리는지
- order block 때문에 막혔는지

### 4. historical cost confidence

보여줘야 할 것:

- `HIGH / MEDIUM / LOW / LIMITED` 대신 현재는 `MEDIUM / LOW / LIMITED` 중심
- 최근 마감 거래 중 몇 건이 gross/net/cost를 안전하게 분리할 수 있는지
- 과거 구간은 왜 제한적인지

## 구현 범위

### P1-1 readiness surface builder

파일:

- [improvement_readiness_surface.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/improvement_readiness_surface.py)

역할:

- PA8 / PA9 / reverse / historical cost를 한 payload로 묶는다
- `summary + per-surface detail` 구조로 저장한다
- JSON/Markdown artifact를 같이 만든다

주요 산출물:

- `data/analysis/shadow_auto/improvement_readiness_surface_latest.json`
- `data/analysis/shadow_auto/improvement_readiness_surface_latest.md`

### P1-2 master board 연결

파일:

- [checkpoint_improvement_master_board.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_master_board.py)

역할:

- readiness surface를 board summary로 끌어올린다
- `blocking_reason / next_required_action / readiness_state`를 surface 기준으로 정리한다
- 테스트 시에는 temp artifact로 분리해 실데이터 오염을 막는다

### P1-3 runtime reverse 상태 export

파일:

- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

역할:

- `pending_reverse_by_symbol`을 runtime status에 export한다
- reverse readiness surface가 실제 pending reverse 후보를 읽을 수 있게 만든다

### P1-4 일간 PnL 연결

파일:

- [telegram_pnl_digest_formatter.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/telegram_pnl_digest_formatter.py)
- [telegram_ops_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/telegram_ops_service.py)

역할:

- `1D` 손익 마감 메시지 끝에 readiness 요약 4줄을 붙인다
- 매일 시스템 상태를 자연스럽게 확인하게 만든다

예시:

```text
━━ 시스템 상태 ━━
PA8 closeout: PENDING_EVIDENCE (준비 0 / 활성 3)
PA9 handoff: PENDING_EVIDENCE (review 0 / apply 0)
reverse readiness: PENDING_EVIDENCE (pending 1 / blocked 0 / ready 0)
historical cost: LOW (최근 4 / 9건 안전)
```

## 완료 조건

- master board summary에 readiness 4축이 항상 채워진다
- board가 temp 경로에서 만들어질 때 readiness artifact도 같은 temp 경로에 쓴다
- runtime status에 pending reverse가 export된다
- `1D PnL` 메시지에 readiness 요약이 붙는다
- 새 readiness 관련 테스트가 통과한다

## 테스트 축

- [test_improvement_readiness_surface.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_improvement_readiness_surface.py)
- [test_checkpoint_improvement_master_board.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_checkpoint_improvement_master_board.py)
- [test_trading_application_runtime_status.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_trading_application_runtime_status.py)
- [test_telegram_ops_service.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_telegram_ops_service.py)

## 다음 단계 연결

P1이 닫히면 다음은 이렇게 간다.

1. `P2-full` 설명력 확장
2. `P3` `/propose` 수동 트리거
3. `P3` PnL 교훈 코멘트
4. `P4` detector log-only lane

즉 P1은 최종 판정을 내리는 단계가 아니라,
`아직 아닌 이유를 운영 표면으로 드러내는 기준면`이다.
