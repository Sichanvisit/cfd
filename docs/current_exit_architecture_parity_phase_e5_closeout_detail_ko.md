# 청산 구조 정렬 Phase E5 Close-out 상세

작성일: 2026-03-29 (KST)  
상태: 완료

## 1. 왜 E5가 필요한가

E1~E4를 지나면서 청산 축은 이미 큰 구조 공사를 끝냈다.

- profile / recovery owner 분리
- exit wait state 계약화
- utility decision 분리
- manage execution seam 분리
- recent exit runtime summary 노출

그런데 이 상태만으로는 새 스레드나 운영자가 바로 안심하고 읽을 수는 없다.
아직 남는 질문은 다음과 같다.

- 지금 분리한 의미가 정말 `trade row -> runtime summary`까지 안 깨지고 이어지는가
- 새 스레드에서 청산을 어디부터 읽어야 하는가
- entry / wait / exit를 한 생애주기로 보면 무엇을 먼저 읽어야 하는가

E5는 이 세 질문을 닫는 phase다.

## 2. E5의 목표

E5는 새 엔진 로직을 더 만드는 phase가 아니다.  
이미 분리된 계약을 운영 surface와 continuity test로 잠그는 close-out phase다.

정확한 목표는 아래 세 가지다.

1. canonical exit scene을 기준으로 `state -> decision -> trade row -> runtime summary` 연속성을 테스트로 고정한다.
2. 청산 recent summary를 새 스레드에서 바로 읽을 수 있게 read guide / handoff / checklist를 정리한다.
3. entry / wait / exit를 한 눈에 이어 읽는 lifecycle summary를 만든다.

## 3. E5에서 다루는 범위

### E5-1 continuity / contract test close-out

대표 청산 장면을 몇 개 고정해서 아래 축이 같은 의미를 유지하는지 검증한다.

- wait state surface
- taxonomy
- persisted trade row
- latest runtime compact row
- recent exit runtime summary

이 단계의 핵심은 “엔진 내부 의미”를 더 복잡하게 만드는 것이 아니라,
이미 만든 의미가 저장과 집계 과정에서 흐트러지지 않음을 잠그는 것이다.

### E5-2 runtime / handoff close-out

청산 recent summary는 이미 runtime에 올라와 있다.
E5에서는 이걸 실제 읽는 순서를 문서로 고정한다.

- slim에서 먼저 볼 필드
- detail에서 더 깊게 볼 필드
- state / decision / bridge 순서
- symbol summary로 내려가는 시점

### E5-3 lifecycle summary

이제 시스템은 entry와 wait, exit가 각각 따로 잘 정리돼 있다.
그다음 필요한 것은 세 축을 하나의 이야기로 보는 문서다.

- entry에서는 무엇이 의미를 정하는가
- wait에서는 무엇이 “좋은 기다림 / 나쁜 기다림”을 가르는가
- exit에서는 무엇이 hold / recovery / reverse / exit_now로 갈리는가
- runtime에서는 각 축을 어느 필드에서 읽는가

## 4. E5 완료 조건

아래 조건이 충족되면 E5는 닫혔다고 봐도 된다.

- `test_exit_end_to_end_contract.py`로 representative exit continuity가 잠겨 있다.
- `current_exit_runtime_read_guide_ko.md`와 handoff / checklist에 exit read path가 반영돼 있다.
- `current_entry_wait_exit_lifecycle_summary_ko.md`로 전체 생애주기 설명이 한 장에 정리돼 있다.
- 청산축을 새 스레드에서 읽을 때 CSV를 바로 열기 전에 runtime surface부터 따라갈 수 있다.

## 5. 이번 phase에서 일부러 안 하는 것

E5는 아래 항목을 목표로 하지 않는다.

- exit 엔진 신규 전략 추가
- alerting / dashboard 추가
- 시계열 비교 대시보드 구축
- portfolio-level orchestration 추가

즉 E5는 확장 phase가 아니라, 지금까지 만든 청산 구조를 운영 가능한 형태로 닫는 phase다.
