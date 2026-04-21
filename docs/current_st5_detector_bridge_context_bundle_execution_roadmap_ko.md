# ST5 Detector Bridge Context Bundle 실행 로드맵

## 실행 범위

- detector 대상:
  - [improvement_log_only_detector.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/improvement_log_only_detector.py)
- registry 대상:
  - [learning_parameter_registry.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_parameter_registry.py)
- 테스트:
  - [test_improvement_log_only_detector_st5.py](C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_improvement_log_only_detector_st5.py)
  - [test_learning_parameter_registry.py](C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_learning_parameter_registry.py)

## 단계

### ST5-1. Runtime Context Field Copy

- detector row attach 단계에서 runtime row의 state-first field를 복사
- scene/candle detector 공통 helper로 정리

### ST5-2. Context Bundle Formatters

- `HTF` line formatter
- `직전 박스` line formatter
- `맥락 충돌` line formatter
- `늦은 추격` line formatter
- 필요 시 `반복성` line formatter

### ST5-3. Detector Evidence Merge

- `context_bundle_lines_ko` 생성
- `context_bundle_summary_ko` 생성
- evidence 상단 prepend
- conflict가 강하면 `why_now_ko` 앞에 짧은 문맥 prefix 부착

### ST5-4. Registry Binding Extend

- learning registry에 context key 추가
- detector evidence registry key 우선순위에 context key 추가
- primary registry key가 `context_conflict_state`를 우선 읽을 수 있게 조정

### ST5-5. Snapshot Tests

- scene detector snapshot이 context bundle을 surface하는지 확인
- candle detector snapshot이 late chase context를 surface하는지 확인
- registry에 새 misread key가 등록됐는지 확인

## 결과물

- detector row가 더 이상 HTF/previous box를 자체 추정하는 reader가 아니라
  `state-first context bundle reader`로 동작
- 이후 `ST6 notifier bridge`에서 같은 bundle summary를 그대로 재사용 가능

## 다음 단계

- `ST6 notifier bridge`
  - `context_bundle_summary_ko`를 DM 한 줄 맥락으로 연결
