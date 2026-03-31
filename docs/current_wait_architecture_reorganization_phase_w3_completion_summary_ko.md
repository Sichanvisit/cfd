# 기다림 정리 Phase W3 완료 정리

부제: wait runtime observability 마감 요약

작성일: 2026-03-29 (KST)

## 1. 한 줄 요약

Phase W3는 완료됐다.

이번 단계에서 한 일은
새로운 wait rule을 더 만드는 것이 아니라,
이미 row와 runtime payload에 남고 있던 wait semantic을
recent diagnostics와 slim surface에서 바로 읽히게 마감한 것이다.


## 2. W3에서 실제로 닫힌 것

### 2-1. recent window에서 wait semantic 자체를 읽을 수 있게 됐다

이제 `runtime_status.detail.json` recent window에는
아래 요약이 함께 올라온다.

- wait state semantic summary
- wait decision summary
- wait state-decision bridge summary

즉 운영자는 이제
`최근 wait가 왜 많았는가`
를 energy trace만으로 보지 않고,

- 어떤 wait state가 많았는지
- 어떤 state가 hard wait로 굳었는지
- 실제 wait 선택률이 어느 정도였는지
- 특정 state가 어떤 decision으로 이어졌는지

까지 바로 읽을 수 있다.


### 2-2. 심볼별 wait recent 흐름도 바로 볼 수 있게 됐다

window 전체 요약만 보면 결국 다시 CSV를 뒤지게 된다.
그래서 이번 W3에서는 심볼별 summary에도 같은 semantic을 붙였다.

즉 이제

- `BTCUSD`
- `NAS100`
- `XAUUSD`

같은 심볼별로
wait state와 decision 흐름이 어떻게 다른지
recent window 기준으로 바로 비교할 수 있다.


### 2-3. slim top-level surface에서도 핵심 wait semantic을 바로 꺼내 본다

detail 파일만 열어야 보이는 구조로 두지 않고,
slim runtime status에도 기본 recent wait semantic 요약을 꺼내 두었다.

그래서 가장 바깥 운영 표면에서도

- 최근 wait state 분포
- 최근 wait selection 비율
- 최근 state -> decision 연결 분포

를 바로 읽을 수 있다.


### 2-4. 새 스레드 read path도 같이 닫혔다

이번 단계에서는 코드만 바뀐 것이 아니라,
새 스레드에서 실제로 따라갈 읽기 경로도 같이 정리했다.

반영 문서:

- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`

즉 이제 새 스레드에서는
`wait-energy trace`만 보는 것이 아니라
`wait semantic summary`도 같은 recent window에서 함께 보도록 안내된다.


## 3. W3에서 추가된 핵심 의미

### wait state semantic summary

이 요약은
최근에 어떤 wait state가 많이 등장했는지,
그중 어떤 상태가 hard wait로 굳었는지를 보여준다.

그래서
`helper soft block이 최근 wait를 주도 중인가`
`probe candidate가 최근 state에서 많이 보이는가`
같은 질문에 바로 답할 수 있다.


### wait decision summary

이 요약은
최근 wait decision이 실제로 어떻게 갈렸는지를 보여준다.

즉
state가 wait 쪽으로 보이는 경우가 많더라도
decision 단계에서 실제 wait 선택으로 이어졌는지,
아니면 대부분 skip으로 풀렸는지를 구분할 수 있다.


### wait state-decision bridge summary

이 요약은
`어떤 state가 어떤 decision으로 이어졌는가`
를 recent window에서 이어서 보여준다.

그래서

- `CENTER -> skip`
- `PROBE_CANDIDATE -> wait_*`
- `HELPER_SOFT_BLOCK -> wait_soft_helper_block`

같은 연결이 최근 흐름에서 강한지 바로 볼 수 있다.


## 4. W3가 실제로 줄여준 해석 비용

W3 전에는
최근 wait 흐름을 보려면 보통 아래 순서가 필요했다.

1. CSV row를 직접 연다
2. wait state / hard / reason / decision을 따로 본다
3. 최근 패턴을 사람이 다시 머리로 묶는다

W3 이후에는
recent diagnostics 자체가 이 묶음을 이미 요약해 준다.

즉 지금은
`truth는 row에 있고, pattern은 runtime summary에 있다`
는 상태가 되었다.


## 5. W3 완료 기준 대비 점검

이번 단계에서 roadmap 기준 완료 조건은 아래처럼 닫혔다.

- semantic summary shape 고정 완료
- runtime aggregation 구현 완료
- symbol summary parity 반영 완료
- slim top-level recent wait semantic surface 반영 완료
- runtime status 회귀 테스트 반영 완료
- handoff/checklist read path 반영 완료


## 6. W3에서 의도적으로 하지 않은 것

이번 단계는 observability surface 마감이지,
운영 도구 전체를 끝내는 단계는 아니다.

따라서 아래는 아직 별도 작업으로 남는다.

- alerting
- 시계열 비교 대시보드
- wait와 chart를 한 화면에서 묶는 correlation UI
- exit/manage까지 같은 수준으로 확장하는 작업


## 7. 검증

이번 단계에서 직접 확인한 테스트는 아래다.

- `pytest tests/unit/test_trading_application_runtime_status.py -q`
- `pytest tests/unit/test_wait_engine.py -q`
- `pytest tests/unit/test_entry_try_open_entry_policy.py -q`


## 8. 다음 단계

지금 시점에서 W3는 완료로 봐도 된다.

다음 선택지는 두 갈래다.

1. wait 정리를 더 이어서 다음 phase로 간다
2. 이제 exit/manage 쪽을 entry/wait 수준으로 맞추기 시작한다

현재 구조상으로는
wait recent observability는 충분히 닫혔으므로,
다음 큰 가치가 나는 곳은
trade lifecycle의 남은 반쪽인 exit/manage 쪽이다.
