# CFD 자주 보는 테스트 안내서

## 목적

이 문서는 `변수 이름`이나 `내부 함수 이름`을 몰라도,
지금 무엇이 궁금한지 기준으로
`어떤 테스트를 보면 되는지` 바로 찾게 하려고 만든 안내서다.

바로 짧게 보고 싶으면 이 문서를 다 읽지 말고
[regular_test_watchlist_quickstart_ko.md](/C:/Users/bhs33/Desktop/project/cfd/regular_test_watchlist_quickstart_ko.md)
부터 보면 된다.

즉 이 문서는

- `지금 Step 9 상태를 보고 싶다`
- `E5가 왜 아직 안 되는지 보고 싶다`
- `런타임 재시작 로직이 맞는지 보고 싶다`
- `라벨 규칙 바꾼 뒤에 뭐가 깨졌는지 보고 싶다`

이런 질문으로 찾아보면 된다.

## 진짜 바쁠 때는 이것만 보면 된다

지금 단계에서 가장 자주 쓰는 최소 루틴은 아래 3개다.

### 0. 아예 한 명령으로 돌리고 싶다

```powershell
python scripts/run_regular_test_watchlist.py
```

이건 쉽게 말하면:

- Step 9 watch report를 먼저 한 번 찍고
- 핵심 테스트 5개를 바로 이어서 돌린다

즉 지금 가장 자주 보는 루틴을 `명령 하나`로 합친 것이다.

이때 같이 갱신되는 보고서:

- JSON: [teacher_pattern_step9_watch_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.json)
- MD: [teacher_pattern_step9_watch_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.md)

중요:

- 이 보고서는 자동 갱신이 아니라 내가 명령을 실행했을 때만 다시 써진다
- 그래서 필요할 때만 찍어보는 방식으로 쓰면 된다

추가로 아래처럼 쓸 수 있다.

- `python scripts/run_regular_test_watchlist.py --profile label`
  - 라벨 / QA / baseline / backfill 확인용
- `python scripts/run_regular_test_watchlist.py --profile runtime`
  - runtime status / recycle / surface 확인용
- `python scripts/run_regular_test_watchlist.py --profile all`
  - 위 추천 묶음을 거의 다 합쳐서 한 번에 확인

### 1. 지금 상황판 보기

```powershell
python scripts/teacher_pattern_step9_watch_report.py
```

이건 쉽게 말하면:

- 지금 seed가 얼마나 쌓였는지
- `10K`까지 얼마나 남았는지
- watchlist pair가 아직도 안 떴는지
- 지금은 계속 누적하면 되는지

를 한 번에 보는 명령이다.

이때 같이 갱신되는 보고서:

- JSON: [teacher_pattern_step9_watch_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.json)
- MD: [teacher_pattern_step9_watch_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.md)

특히 MD 파일은 사람이 읽기 쉽게 현재 상태, E5 blocker, watchlist pair, runtime recycle 상태를 바로 요약해둔 버전이다.

### 2. 지금 단계 핵심 테스트만 보기

```powershell
pytest tests/unit/test_teacher_pattern_step9_watch.py tests/unit/test_teacher_pattern_execution_handoff.py tests/unit/test_runtime_recycle.py tests/unit/test_trading_application_runtime_status.py tests/unit/test_teacher_pattern_labeler.py -q
```

이건 쉽게 말하면:

- Step 9 상황판
- E5 gate
- runtime recycle
- runtime status
- 핵심 label rule

이 다섯 가지가 안 깨졌는지 보는 최소 핵심 묶음이다.

### 3. labeler / relabel / baseline 건드린 뒤 보기

```powershell
pytest tests/unit/test_teacher_pattern_labeler.py tests/unit/test_teacher_pattern_full_labeling_qa.py tests/unit/test_teacher_pattern_pilot_baseline.py tests/unit/test_teacher_pattern_asset_calibration.py tests/unit/test_teacher_pattern_backfill.py -q
```

이건 쉽게 말하면:

- 라벨 규칙이 여전히 맞는지
- QA 숫자가 맞는지
- baseline supported pattern이 맞는지
- calibration 경고가 이상하지 않은지
- backfill이 안전한지

를 같이 보는 묶음이다.

## 제일 자주 보게 되는 질문

### 1. 지금 Step 9를 계속 밀어도 되는지 보고 싶다

이럴 때 보면 되는 것:

- `python scripts/teacher_pattern_step9_watch_report.py`
- `tests/unit/test_teacher_pattern_step9_watch.py`

쉽게 말하면:

- 지금 seed가 얼마나 쌓였는지
- `10K`까지 얼마나 남았는지
- watchlist pair가 아직도 `0`인지
- 지금은 그냥 계속 누적하면 되는지, 아니면 `E4/E5`를 다시 볼 타이밍인지

이걸 보는 용도다.

지금 우리 프로젝트에선 이게 거의 `상황판` 역할이다.

## 2. E5가 왜 아직 NOT_READY인지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_teacher_pattern_execution_handoff.py`

쉽게 말하면:

- E5에서 무엇 때문에 아직 막히는지
- `seed 부족 때문인지`
- `coverage 부족 때문인지`
- `supported pattern 부족 때문인지`
- `confusion 문제 때문인지`

이걸 최종 gate 관점에서 확인하는 테스트다.

지금은 특히
`E5가 아직 왜 안 열리는지`
를 볼 때 제일 직접적이다.

## 3. watchlist pair가 아직도 관측 안 되는지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_teacher_pattern_confusion_tuning.py`
- `tests/unit/test_teacher_pattern_full_labeling_qa.py`

쉽게 말하면:

- `12-23`, `5-10`, `2-16`
  이 조합이 실제로 잡히는지
- 아직은 그냥 관찰 단계인지
- 관측되면 바로 tuning 대상으로 넘길 수 있는지

이걸 본다.

즉 `watchlist pair 쪽이 살아 있나`를 보는 테스트다.

## 4. 한 시간 지나면 재시작하는 로직이 맞는지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_runtime_recycle.py`

쉽게 말하면:

- 포지션이 있으면 재시작하면 안 되는지
- 포지션이 없어도 바로 재시작하지 않고 grace를 기다리는지
- 지금은 `log_only`만 하는지
- health/drift 징후가 있을 때만 재시작 후보가 되는지

이걸 확인하는 테스트다.

즉 `runtime recycle 안전장치가 제대로 걸려 있나`
를 보는 테스트라고 생각하면 된다.

## 5. runtime_status.json에 내가 보고 싶은 정보가 제대로 실리는지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_trading_application_runtime_status.py`

쉽게 말하면:

- runtime status 파일에
  `observe 이유`, `wait 상태`, `position-energy 요약`,
  `runtime recycle 상태`, `최근 요약`
  같은 게 빠짐없이 잘 들어가는지

이걸 본다.

지금처럼
`왜 진입 안 하지?`
`지금 blocked 이유가 뭐지?`
`recycle 상태가 뭐지?`
같은 걸 runtime status로 확인하고 싶을 때 가장 중요하다.

## 6. 라벨 규칙을 바꿨는데 pattern 25나 11 같은 핵심 규칙이 안 깨졌는지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_teacher_pattern_labeler.py`

쉽게 말하면:

- `25`가 여전히 passive high-risk upper reversal sell로 붙는지
- `11`이 confirm pullback buy에 잘 붙는지
- `12-23` 같은 breakout/triangle 쌍이 그대로 나오는지
- 원래 `5`로 남아야 할 건 여전히 `5`로 남는지

이걸 보는 테스트다.

즉 `state25 규칙 자체가 안 깨졌는지`
를 보는 가장 핵심 테스트다.

## 7. relabel/backfill을 다시 돌렸을 때 기존 데이터가 이상해지지 않는지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_teacher_pattern_backfill.py`

쉽게 말하면:

- 이미 붙어 있던 라벨을 함부로 덮어쓰지 않는지
- recent window만 잘 건드리는지
- relabel provenance가 맞게 기록되는지

이걸 확인한다.

즉 `backfill을 다시 돌려도 안전한가`
를 볼 때 쓰면 된다.

## 8. seed / baseline / QA 숫자가 이상하지 않은지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_teacher_pattern_full_labeling_qa.py`
- `tests/unit/test_teacher_pattern_pilot_baseline.py`
- `tests/unit/test_teacher_pattern_asset_calibration.py`

쉽게 말하면:

- labeled row 부족 경고가 잘 잡히는지
- primary coverage 계산이 맞는지
- supported pattern class가 충분한지
- asset별 skew나 ATR flat 경고가 맞게 잡히는지

이걸 본다.

즉 `Step 9 숫자 판단이 엉뚱하지 않나`
를 볼 때 쓰면 된다.

## 9. runtime 표면이 여전히 score보다 position-energy 중심으로 보이는지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_storage_compaction.py`

쉽게 말하면:

- raw score는 legacy로 남고
- 메인 surface는 `position`, `energy`, `observe`, `readiness`
  중심으로 정리되는지
- compact row / hot payload에 probe, wait, quick trace가 잘 남는지

이걸 확인하는 테스트다.

즉 `런타임 표면이 내가 의도한 방식으로 보이느냐`
를 볼 때 쓰면 된다.

## 10. micro payload나 entry ATR proxy가 제대로 들어가는지 보고 싶다

이럴 때 보면 되는 것:

- `tests/unit/test_trade_logger_entry_atr_proxy.py`
- `tests/unit/test_trading_application_micro_structure.py`

쉽게 말하면:

- ATR이 비어 있거나 `1.0` 고정처럼 보일 때 proxy가 잘 들어가는지
- micro-structure Top10 재료가 기본 형태를 유지하는지

이걸 본다.

즉 `payload가 비거나 납작해지는 문제`
를 다시 의심할 때 보면 좋다.

## 지금 기준 추천 묶음

### A. 제일 자주 보는 최소 묶음

이 5개면 지금 단계에서는 충분하다.

- `tests/unit/test_teacher_pattern_step9_watch.py`
- `tests/unit/test_teacher_pattern_execution_handoff.py`
- `tests/unit/test_runtime_recycle.py`
- `tests/unit/test_trading_application_runtime_status.py`
- `tests/unit/test_teacher_pattern_labeler.py`

명령:

```powershell
pytest tests/unit/test_teacher_pattern_step9_watch.py tests/unit/test_teacher_pattern_execution_handoff.py tests/unit/test_runtime_recycle.py tests/unit/test_trading_application_runtime_status.py tests/unit/test_teacher_pattern_labeler.py -q
```

이 묶음은 쉽게 말하면:

- Step 9 상황판
- E5 gate
- runtime recycle
- runtime status surface
- 핵심 label 규칙

이 다섯 가지를 한 번에 본다.

### B. labeler / relabel / baseline 건드린 뒤 보는 묶음

- `tests/unit/test_teacher_pattern_labeler.py`
- `tests/unit/test_teacher_pattern_full_labeling_qa.py`
- `tests/unit/test_teacher_pattern_pilot_baseline.py`
- `tests/unit/test_teacher_pattern_asset_calibration.py`
- `tests/unit/test_teacher_pattern_backfill.py`

명령:

```powershell
pytest tests/unit/test_teacher_pattern_labeler.py tests/unit/test_teacher_pattern_full_labeling_qa.py tests/unit/test_teacher_pattern_pilot_baseline.py tests/unit/test_teacher_pattern_asset_calibration.py tests/unit/test_teacher_pattern_backfill.py -q
```

쉽게 말하면:

- 규칙 바뀌어도 라벨이 맞는지
- QA 숫자가 맞는지
- baseline 지원 클래스가 맞는지
- calibration 경고가 맞는지
- relabel/backfill이 안전한지

를 같이 본다.

### C. runtime 표면 쪽 바꾼 뒤 보는 묶음

- `tests/unit/test_storage_compaction.py`
- `tests/unit/test_trading_application_runner_profile.py`
- `tests/unit/test_trade_logger_entry_atr_proxy.py`
- `tests/unit/test_trading_application_micro_structure.py`
- `tests/unit/test_runtime_recycle.py`
- `tests/unit/test_trading_application_runtime_status.py`

명령:

```powershell
pytest tests/unit/test_storage_compaction.py tests/unit/test_trading_application_runner_profile.py tests/unit/test_trade_logger_entry_atr_proxy.py tests/unit/test_trading_application_micro_structure.py tests/unit/test_runtime_recycle.py tests/unit/test_trading_application_runtime_status.py -q
```

쉽게 말하면:

- runtime이 보여주는 화면/상태
- recycle
- micro payload
- ATR proxy

가 한 번에 안 깨졌는지 본다.

## 정말 헷갈릴 때 이렇게 찾으면 된다

### “지금 Step 9 계속 가도 돼?”

- `teacher_pattern_step9_watch_report.py`
- `test_teacher_pattern_step9_watch.py`

### “E5 왜 아직 안 열려?”

- `test_teacher_pattern_execution_handoff.py`

### “watchlist pair 아직도 안 떴어?”

- `test_teacher_pattern_confusion_tuning.py`
- `test_teacher_pattern_full_labeling_qa.py`

### “runtime recycle 이거 안전해?”

- `test_runtime_recycle.py`

### “runtime_status.json에 내가 보고 싶은 게 다 들어가?”

- `test_trading_application_runtime_status.py`

### “labeler 바꾼 뒤 25/11/12-23 안 깨졌어?”

- `test_teacher_pattern_labeler.py`

### “backfill 다시 돌려도 안전해?”

- `test_teacher_pattern_backfill.py`

### “payload나 ATR proxy 다시 이상해진 거 아니야?”

- `test_trade_logger_entry_atr_proxy.py`
- `test_trading_application_micro_structure.py`

## 마지막 한 줄 요약

지금 단계에서 제일 중요하게 계속 보는 건 아래다.

1. `teacher_pattern_step9_watch_report.py`
2. `test_teacher_pattern_step9_watch.py`
3. `test_teacher_pattern_execution_handoff.py`
4. `test_runtime_recycle.py`
5. `test_trading_application_runtime_status.py`
6. `test_teacher_pattern_labeler.py`

즉 지금은
`Step 9 상황판`, `E5 gate`, `runtime recycle`, `runtime status`, `label rule`
이 다섯 축만 계속 보면 된다.
