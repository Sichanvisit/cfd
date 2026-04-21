# CFD 테스트 초간단판

## 목적

이 문서는 길게 읽지 않고
`지금 당장 뭘 실행하면 되는지`
만 빠르게 보려고 만든 초간단판이다.

지금 단계는 `state25 Step 9 + runtime 운영`이 메인이라,
사실상 아래 3개만 기억하면 된다.

## 0. 아예 한 명령으로 돌리고 싶을 때

```powershell
python scripts/run_regular_test_watchlist.py
```

쉽게 말하면:

- 먼저 Step 9 상황판을 한 번 찍고
- 바로 핵심 테스트 5개를 이어서 돌린다

즉 `지금 제일 자주 보는 루틴`을 한 명령으로 합친 것이다.

이때 같이 갱신되는 보고서:

- JSON: [teacher_pattern_step9_watch_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.json)
- MD: [teacher_pattern_step9_watch_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.md)

중요:

- 이 보고서는 자동으로 계속 갱신되지 않는다
- 내가 원할 때 이 명령을 실행했을 때만 다시 써진다

추가로:

- `python scripts/run_regular_test_watchlist.py --profile label`
  - 라벨/QA/baseline 쪽 묶음
- `python scripts/run_regular_test_watchlist.py --profile runtime`
  - runtime 표면/로그 쪽 묶음
- `python scripts/run_regular_test_watchlist.py --profile all`
  - 위 추천 묶음을 전부 합친 버전

## 1. 지금 상태판 보기

```powershell
python scripts/teacher_pattern_step9_watch_report.py
```

이걸 보면 된다 when:

- 지금 Step 9를 계속 밀어도 되는지 보고 싶을 때
- `10K`까지 얼마나 남았는지 보고 싶을 때
- watchlist pair가 아직도 `0`인지 보고 싶을 때
- 지금은 계속 누적인지, 다시 `E4/E5`를 볼 타이밍인지 보고 싶을 때

쉽게 말하면:

`지금 전체 상황 요약판`

이때 같이 갱신되는 보고서:

- JSON: [teacher_pattern_step9_watch_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.json)
- MD: [teacher_pattern_step9_watch_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.md)

중요:

- 이제는 JSON만이 아니라 사람이 읽기 쉬운 MD 요약본도 같이 떨어진다
- 둘 다 내가 원할 때만 실행해서 갱신하면 된다

## 2. 지금 단계 핵심 테스트만 보기

```powershell
pytest tests/unit/test_teacher_pattern_step9_watch.py tests/unit/test_teacher_pattern_execution_handoff.py tests/unit/test_runtime_recycle.py tests/unit/test_trading_application_runtime_status.py tests/unit/test_teacher_pattern_labeler.py -q
```

이걸 보면 된다 when:

- 오늘 한 작업이 핵심 축을 깨뜨렸는지 빠르게 보고 싶을 때
- Step 9 / E5 / runtime recycle / runtime status / labeler를 한 번에 점검하고 싶을 때

쉽게 말하면:

`지금 프로젝트 핵심 5축 안 깨졌는지 확인`

## 3. 라벨 쪽 건드린 뒤 보는 묶음

```powershell
pytest tests/unit/test_teacher_pattern_labeler.py tests/unit/test_teacher_pattern_full_labeling_qa.py tests/unit/test_teacher_pattern_pilot_baseline.py tests/unit/test_teacher_pattern_asset_calibration.py tests/unit/test_teacher_pattern_backfill.py -q
```

이걸 보면 된다 when:

- labeler rule을 바꿨을 때
- relabel / bounded backfill을 다시 돌렸을 때
- baseline supported pattern 수가 바뀔 수 있을 때

쉽게 말하면:

`라벨 규칙과 Step 9 숫자 판단이 맞는지 확인`

## 4. 런타임 표면 바꾼 뒤 보는 묶음

```powershell
pytest tests/unit/test_storage_compaction.py tests/unit/test_trading_application_runner_profile.py tests/unit/test_trade_logger_entry_atr_proxy.py tests/unit/test_trading_application_micro_structure.py tests/unit/test_runtime_recycle.py tests/unit/test_trading_application_runtime_status.py -q
```

이걸 보면 된다 when:

- runtime_status.json 쪽을 바꿨을 때
- entry decision compact/hot payload를 바꿨을 때
- micro payload / ATR proxy / runtime recycle을 건드렸을 때

쉽게 말하면:

`실런타임에 보이는 표면이 안 깨졌는지 확인`

## 지금 기준 제일 쉬운 사용법

평소엔 아래만 해도 충분하다.

1. `python scripts/teacher_pattern_step9_watch_report.py`
2. 필요하면 핵심 테스트 5개 묶음 실행

즉 아주 짧게 말하면:

- 전부 한 번에 보려면: `run_regular_test_watchlist.py`
- 상태 보려면: `teacher_pattern_step9_watch_report.py`
- 핵심 안 깨졌는지 보려면: 핵심 5개 `pytest`
- 라벨 건드렸으면: labeler/QA/baseline 묶음 `pytest`

## 더 자세한 설명이 필요할 때

긴 설명판은 여기:

- [regular_test_watchlist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/regular_test_watchlist_ko.md)
