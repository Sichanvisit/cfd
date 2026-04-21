# ST9 Proposal / Hindsight Bridge 실행 로드맵

## 실행 범위

- proposal runtime
  - [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)
- 테스트
  - [test_trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_trade_feedback_runtime.py)
  - [test_trade_feedback_runtime_db3.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_trade_feedback_runtime_db3.py)
  - [test_trade_feedback_runtime_st9.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_trade_feedback_runtime_st9.py)

## 단계

### ST9-1. Issue Context Bridge Helper

- latest issue에서 context/hindsight 관련 필드 추출
- proposal용 `proposal_context_summary_ko` 조립

### ST9-2. Feedback Promotion Row 승격

- feedback promotion row에 context/hindsight 필드 추가
- 기존 direct binding 정보는 유지

### ST9-3. Surfaced Problem Pattern 연결

- top matched feedback promotion row의 context/hindsight를
  surfaced issue에 복사

### ST9-4. Proposal Envelope / Report 보강

- `why_now_ko` 보강
- `evidence_snapshot`에 context/hindsight summary 추가
- report line에 `맥락/사후:` 줄 추가

### ST9-5. Unit Test

- feedback row가 context/hindsight 요약을 들고 있는지
- proposal envelope가 context/hindsight를 why-now로 surface하는지
- report line이 `맥락/사후:`를 포함하는지 확인

## 결과물

- detector / notifier / propose / hindsight가 더 같은 언어를 쓰게 됨
- review backlog에서 `왜 이 패턴이 지금 위험한지`를 더 빨리 읽을 수 있음
- hindsight가 detector 내부 상태로만 남지 않고 proposal review까지 연결됨

## 다음 단계

- state-first context를 approval/review 운영 패킷까지 이어서
  실제 bounded review packet 언어를 더 통일하기
