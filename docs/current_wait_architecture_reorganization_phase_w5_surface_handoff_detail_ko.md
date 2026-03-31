# 기다림 정리 Phase W5 상세 문서

부제: wait surface / runtime / handoff 마감을 어떻게 닫을지에 대한 상세 기준서

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 W5 surface/handoff close-out 반영 완료

## 1. 문서 목적

이 문서는 `Phase W5. Wait Surface/Handoff 마감`을 실제 작업 기준으로 풀어 쓴 상세 문서다.

W5의 목적은 새 wait rule을 더 만드는 것이 아니다.
이미 구축된 wait 구조를 운영 표면과 handoff 문서에서 빠르게 읽히게 만들고,
새 스레드나 운영 점검 시점에 CSV를 직접 뒤지지 않아도
최근 wait 흐름을 5분 안에 해석할 수 있게 마감하는 것이다.

즉 W5는 구조 공사라기보다
`지금까지 만든 진실을 사람이 바로 읽을 수 있게 정리하는 close-out phase`
라고 보는 편이 정확하다.


## 2. 왜 W5가 지금 필요한가

지금 wait 축은 구조상으로는 이미 많이 닫혔다.

- bias owner가 분리되어 있다
- wait context contract가 있다
- state policy input contract가 있다
- runtime recent summary가 있다
- end-to-end contract tests가 있다
- skip seam mismatch도 실제 코드에서 한 번 정리했다

즉 현재의 문제는
`구조가 부족하다`가 아니라
`읽기 표면이 아직 사람 친화적으로 마지막 정리가 덜 끝났다`
에 가깝다.

이 상태에서 W5 없이 바로 W6로 넘어가면,
다음과 같은 일이 생길 가능성이 높다.

- 실제 wait surface는 풍부한데 새 스레드에서는 어디부터 읽어야 하는지 다시 설명해야 한다
- runtime status에 이미 있는 요약들을 운영자가 서로 어떻게 연결해야 하는지 감이 안 온다
- bias owner / hard wait / decision bridge 의미를 매번 말로 다시 풀어야 한다
- wait는 구축됐는데 handoff는 여전히 “읽는 사람의 숙련도”에 의존하는 상태가 남는다

그래서 W5는 선택적 문서 작업처럼 보여도,
실제로는 `구축한 observability를 usable하게 만드는 마감 작업`이다.


## 3. 지금 이미 구축된 wait surface

W5를 시작하기 전에 먼저 분명히 해둘 점이 있다.
W5는 빈 땅에서 시작하는 단계가 아니다.

지금 이미 존재하는 표면은 아래와 같다.

### 3-1. row/runtime surface

entry decision row와 runtime latest row에는 이미 다음 계열이 남는다.

- wait state
- wait reason
- wait selected 여부
- wait decision
- wait context contract
- wait bias bundle
- wait state policy input
- wait energy usage trace
- wait decision energy usage trace

즉 한 건의 row를 놓고 보면
`왜 이 장면이 wait처럼 보였는지`
와
`왜 최종적으로 skip 또는 wait decision이 되었는지`
를 꽤 많이 복원할 수 있다.

### 3-2. recent runtime summary

`runtime_status.detail.json`과 slim surface에는 이미 다음 계열의 최근 요약이 있다.

- wait energy trace summary
- wait state semantic summary
- wait decision summary
- wait state-decision bridge summary

즉 최근 200행 수준에서는

- 어떤 wait state가 많이 보였는지
- hard wait가 어떤 state에서 많이 묶였는지
- 실제로 wait decision이 얼마나 선택됐는지
- 특정 state가 어떤 decision으로 이어졌는지

를 이미 읽을 수 있다.

### 3-3. read path 문서

현재 문서에도 일부는 이미 들어가 있다.

- `thread_restart_handoff_ko.md`
- `thread_restart_first_checklist_ko.md`

특히 checklist 쪽은
wait energy summary와 semantic summary를 어느 필드로 읽는지까지 이미 적혀 있다.

즉 W5는 “기능 부재”보다
`이미 있는 runtime surface를 어떻게 더 선명하게 설명하고 묶어 줄지`
의 문제다.


## 4. 지금 남아 있는 gap

W5가 실제로 메워야 하는 남은 gap은 아래 6가지로 정리할 수 있다.

### 4-1. wait state taxonomy가 아직 흩어져 있다

지금은 `CENTER`, `CONFLICT`, `EDGE_APPROACH`, `HELPER_SOFT_BLOCK`,
`HELPER_WAIT`, `POLICY_BLOCK`, `POLICY_SUPPRESSED`,
`PROBE_CANDIDATE`, `ACTIVE` 같은 상태가 존재하지만,
새 사람이 보기엔 이 상태들이

- directional observe 성격인지
- neutral hold 성격인지
- helper-driven 성격인지
- policy hard block 성격인지
- scene-specific probe 성격인지

한눈에 묶여 있지 않다.

즉 field는 있으나 taxonomy guide가 약하다.

### 4-2. hard wait / soft wait 해석법이 아직 분산돼 있다

최근 summary에는 hard wait counts가 있지만,
운영자가 바로 알고 싶은 질문은 대체로 이런 것이다.

- 이 state가 hard wait로 묶인 이유가 구조적인가
- 아니면 helper soft block이 강하게 들어왔기 때문인가
- hard wait는 많지만 실제 wait selected는 낮은가

이 해석이 지금은 checklist와 문맥 속에 흩어져 있다.

### 4-3. bias owner 해석이 아직 코드 지식 의존적이다

W1에서 owner를 분리했기 때문에 구조는 좋아졌다.
하지만 runtime surface를 읽는 사람 입장에서는 여전히

- state bias가 만든 release인지
- belief bias가 만든 wait lock인지
- edge pair가 directional clarity를 줬는지
- probe temperament가 scene-specific wait를 만들었는지

를 빠르게 연결하기 어렵다.

즉 owner separation은 완료됐지만,
owner reading guide는 아직 완전히 끝나지 않았다.

### 4-4. first-pass 운영 동선이 한 장으로 닫혀 있지 않다

지금도 handoff와 checklist를 같이 보면 읽을 수 있다.
하지만 W5가 끝난 상태라면 ideally 다음이 가능해야 한다.

1. latest row에서 지금 주된 축을 본다
2. detail recent summary에서 최근 분포를 본다
3. symptom-to-cause 매핑으로 원인 가설을 세운다
4. 필요한 경우에만 CSV나 코드로 내려간다

현재는 이 동선이 문서 2~3장에 걸쳐 흩어져 있다.

### 4-5. symbol-level read path가 약하다

전체 recent summary는 존재하지만,
실제 운영에서는 심볼별 질문이 많다.

- BTC는 왜 wait가 많지
- NAS는 왜 clean ready보다 policy suppressed가 늘었지
- XAU는 probe scene이 실제 wait로 얼마나 이어졌지

이 질문에 대해
`symbol summary에서 무엇을 먼저 볼지`
가 아직 별도 안내로 정리돼 있지 않다.

### 4-6. W5 완료 선언 문서가 없다

W1은 completion summary가 있고,
W3도 completion summary가 있다.

W5가 끝나면 wait 축 전체를 닫는 문서가 하나 있어야 한다.
그래야 새 스레드에서
`wait는 어디까지 끝났고, 이제 다음은 W6다`
를 명확하게 선언할 수 있다.


## 5. W5가 지향하는 최종 상태

W5가 끝나면 아래 5가지가 성립해야 한다.

1. 새 스레드에서 wait surface 읽는 순서가 한 장으로 정리돼 있다.
2. wait state taxonomy가 그룹별로 설명돼 있다.
3. hard wait / soft wait / decision bridge를 운영자가 문서만으로 해석할 수 있다.
4. bias owner가 runtime summary와 어떻게 연결되는지 설명돼 있다.
5. wait 축 완료 선언 문서가 생겨 W6로 넘어갈 준비가 된다.

즉 W5의 완료 상태는
`데이터는 있는데 읽는 법이 모호한 상태`
에서
`데이터와 읽는 법이 같이 닫힌 상태`
로 바뀌는 것이다.


## 6. W5를 어떻게 나눌 것인가

W5는 W1/W2처럼 깊게 잘라야 하는 phase는 아니다.
구조 extraction이 아니라 close-out이기 때문이다.

하지만 그래도 한 번에 뭉쳐서 하면
무엇이 gap 정리이고 무엇이 문서 sync인지 흐려질 수 있으므로
아래 4단으로 나누는 편이 안전하다.

### W5-1. Surface Inventory / Gap Check

목표:
현재 이미 존재하는 wait surface를 정확히 목록화하고,
무엇이 이미 설명됐고 무엇이 아직 문서에 없는지 정리한다.

핵심 질문:

- latest row에서 지금 바로 읽을 수 있는 wait field는 무엇인가
- detail recent summary에서 읽을 수 있는 wait summary는 무엇인가
- handoff/checklist에서 이미 설명된 것과 빠진 것은 무엇인가

완료 기준:

- `row / latest_signal / recent_runtime_summary / recent_runtime_diagnostics / docs`
  기준 inventory가 정리돼 있다
- 중복 설명과 누락 설명이 분리돼 있다

### W5-2. Runtime Reading Guide Close-out

목표:
운영자가 `runtime_status.detail.json`과 slim surface를 읽는 순서를
딱 한 번에 따라갈 수 있게 정리한다.

핵심 내용:

- latest row first look
- recent summary second look
- symbol summary third look
- CSV fallback last look

여기에 아래 내용을 같이 넣는 것이 좋다.

- wait state taxonomy
- hard wait / soft wait 해석
- state -> decision bridge 해석
- energy trace와 semantic summary를 함께 읽는 법

완료 기준:

- “최근 wait가 많다”는 질문에 대해 5분 read path가 문서화되어 있다
- CSV를 직접 보기 전에 확인해야 할 runtime surface가 정리돼 있다

### W5-3. Handoff / Checklist Sync

목표:
기존 `thread_restart_handoff_ko.md`와
`thread_restart_first_checklist_ko.md`를 W4 이후 상태에 맞게 정리한다.

핵심 내용:

- wait section을 별도 제목으로 분리
- top-level reading order 정리
- symptom-to-cause quick map 보강
- symbol summary reading guidance 추가

완료 기준:

- 새 스레드 시작 문서만 읽고도 wait current state를 바로 볼 수 있다
- handoff와 checklist가 서로 다른 말을 하지 않는다

### W5-4. Completion Summary / Exit Gate

목표:
wait 축이 여기까지 닫혔다는 것을 선언하는 summary 문서를 만든다.

핵심 내용:

- W1~W4에서 무엇이 구축됐는지
- W5에서 읽기 표면이 어떻게 마감됐는지
- 아직 wait 축에서 남은 것이 정말 없는지
- 다음 phase가 왜 W6인지

완료 기준:

- `wait 축은 구조/관측/테스트/문서까지 닫혔다`는 선언이 가능하다
- 다음 작업이 `exit/manage` 연결 준비로 자연스럽게 넘어간다


## 7. 대상 파일

W5는 대부분 문서 작업이지만,
필요하면 runtime summary alias나 설명용 compact field를 조금 더 손볼 수도 있다.
현재 기준으로는 아래 파일이 핵심이다.

문서:

- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`
- `docs/current_wait_architecture_reorganization_phase_w5_surface_handoff_detail_ko.md`
- `docs/current_wait_architecture_reorganization_phase_w5_implementation_breakdown_ko.md`
- `docs/current_wait_architecture_reorganization_phase_w5_completion_summary_ko.md`

코드 확인 대상:

- `backend/app/trading_application.py`
- `backend/services/storage_compaction.py`
- `backend/services/entry_try_open_entry.py`

주의할 점:

W5의 본체는 문서와 read path 정리다.
코드를 건드리더라도 구조를 다시 바꾸는 식의 큰 수정은 W5 범위를 넘는다.


## 8. 이 단계에서 건드리면 안 되는 것

### 8-1. exit/manage 로직을 같이 여는 것

W5는 wait close-out이지 W6가 아니다.
여기서 exit/manage 로직까지 같이 열면 범위가 다시 커진다.

### 8-2. chart 의미 체계를 다시 바꾸는 것

wait를 chart에 더 세밀하게 올리고 싶을 수는 있다.
하지만 W5의 우선은 “읽기 guide 마감”이지 chart semantics 재설계가 아니다.

### 8-3. ML tuning과 wait guide를 섞는 것

semantic rollout, threshold tuning, belief calibration은
읽기 가이드와 별개로 유지하는 편이 안전하다.


## 9. 권장 구현 순서

가장 자연스러운 순서는 아래와 같다.

1. W5-1 inventory 문서 정리
2. W5-2 runtime reading guide 문서 작성
3. W5-3 handoff/checklist sync
4. W5-4 completion summary 작성

즉 W5는
`무엇이 있는지 정리 -> 어떻게 읽는지 적기 -> 기존 handoff에 반영 -> 완료 선언`
순서로 가는 것이 가장 깔끔하다.


## 10. 완료 선언 조건

W5를 완료로 보려면 아래가 만족돼야 한다.

- wait state taxonomy guide가 문서에 있다
- hard wait / soft wait / decision bridge 해석 가이드가 있다
- runtime recent summary first-pass read path가 한 장으로 정리돼 있다
- handoff와 checklist가 현재 구현 상태와 맞게 sync돼 있다
- wait 축 completion summary가 존재한다
- 새 스레드에서 “최근 wait가 왜 많은가”를 CSV 없이 1차 해석할 수 있다


## 11. 지금 바로 시작할 첫 작업

첫 작업은 `W5-1 inventory + gap check`다.

이유는 간단하다.
지금 W5는 대부분의 기반이 이미 존재하기 때문에,
무엇을 새로 만들 것보다
`이미 있는 wait surface를 어떤 문서에서 어떤 순서로 읽히게 할지`
를 먼저 정리해야 전체 close-out이 선명해진다.

즉 다음 실제 행동은
`W5 implementation breakdown 문서를 만들고, handoff/checklist sync 범위를 확정하는 것`
이다.
