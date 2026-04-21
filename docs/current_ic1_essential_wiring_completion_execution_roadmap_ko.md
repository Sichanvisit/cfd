# IC1 Essential Wiring Completion 실행 로드맵

## 목표

필수 배선을 완결해서 runtime row, execution trace, chart/flow history, accuracy tracker가 같은 current-cycle 판단을 공유하게 만든다.

## 실행 순서

### Step 1. single-row surface 정규화

대상:

- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

작업:

- `build_entry_runtime_signal_row(...)`
- `build_chart_painter_runtime_row(...)`
- `_append_ai_entry_trace(...)`

가 모두 nested `execution_action_diff_v1`를 잃지 않고 `execution_diff_*` flat surface를 남기게 한다.

완료 기준:

- entry/chart/trace 모두 `execution_diff_original_action_side`, `execution_diff_final_action_side`를 surface

### Step 2. current accuracy single-row attach

대상:

- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

작업:

- single-row enrich 종료 시점에
  - `directional_continuation_accuracy_horizon_bars`
  - `directional_continuation_accuracy_sample_count`
  - `directional_continuation_accuracy_correct_rate`
  를 붙인다.

완료 기준:

- batch runtime status뿐 아니라 entry/chart row도 accuracy surface를 가진다.

### Step 3. runtime signal wiring audit artifact

대상:

- [runtime_signal_wiring_audit.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\runtime_signal_wiring_audit.py)
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

작업:

- audit summary JSON/MD 생성
- runtime status detail에 summary/path export

완료 기준:

- `runtime_signal_wiring_audit_summary_v1`
- `runtime_signal_wiring_audit_artifact_paths`

가 runtime detail에 존재

### Step 4. 짧은 live 확인

확인 포인트:

- overlay event hint와 flow history event가 같은지
- execution diff가 빈값 없이 쌓이는지
- accuracy report가 pending에서 measured로 넘어가기 시작하는지

### Step 5. CA2/BC11로 환류

- CA2: KPI 누적
- BC11: fresh review candidate 기반 bounded live canary

## 상태 기준

### READY

- single-row/batch-row/trace 모두 같은 diff/accuracy contract
- runtime audit summary가 정상 생성
- flow history mismatch가 소수

### HOLD

- 일부 row는 surface되지만 trace 또는 flow sync가 부족
- accuracy measured sample이 아직 너무 적음

### BLOCKED

- execution diff missing rate 높음
- flow sync mismatch 반복
- runtime audit artifact 미생성

## 산출물

- [current_ic1_essential_wiring_completion_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_ic1_essential_wiring_completion_detailed_plan_ko.md)
- [runtime_signal_wiring_audit.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\runtime_signal_wiring_audit.py)
- [runtime_signal_wiring_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\runtime_signal_wiring_audit_latest.json)
- [runtime_signal_wiring_audit_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\runtime_signal_wiring_audit_latest.md)
