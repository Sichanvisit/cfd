# 청산 구조 정렬 Phase E4 완료 요약

작성일: 2026-03-29 (KST)
상태: 완료

## 1. E4가 맡았던 것

E4의 목적은 `exit_manage_positions.py`에 남아 있던 실행 seam을 정리해서,
청산도 entry / wait처럼

- input contract
- candidate / policy owner
- execution orchestration
- runtime / logger surface

가 분리된 구조로 끌어올리는 것이었다.


## 2. E4에서 실제로 끝난 것

### E4-1

- manage execution input contract freeze
- runtime sink contract freeze

### E4-2

- recovery execution candidate 분리
- hard guard action candidate 분리
- reverse action candidate 분리

### E4-3

- partial close candidate 분리
- stop-up / break-even candidate 분리
- protect / lock / time stop / target stage candidate 분리

### E4-4

- execution plan orchestrator 분리
- execution result surface 분리
- manage loop를 `candidate -> plan -> execute` 형태로 정리


## 3. E4 이후 청산의 현재 구조

지금 청산 축은 크게 이렇게 읽힌다.

1. handoff / profile / recovery posture가 canonical context로 얼어 있다.
2. wait state와 utility decision이 별도 owner로 분리돼 있다.
3. recent exit runtime summary가 runtime status에 올라온다.
4. manage execution loop는 candidate와 plan을 받아 실행한다.

즉 이제 청산도 "룰이 한 함수 안에 모여 있는 로직"에서
"contract와 owner가 보이는 구조"로 많이 이동한 상태다.


## 4. 객관적 평가

E4까지 끝난 지금 기준으로는,
청산도 entry / wait와 같은 방향의 설계 수준으로 꽤 올라왔다고 봐도 된다.

물론 entry / wait처럼 handoff/read guide와 end-to-end close-out이 더 붙으면 더 좋아지지만,
적어도 core policy / execution seam이 커다란 함수 안에 뭉쳐 있던 시점은 이미 넘어섰다.


## 5. 다음 자연스러운 단계

이후는 큰 구조 공사보다 마감 성격이 강하다.

추천 순서는 이렇다.

1. exit runtime read guide / handoff close-out
2. exit continuity / contract test 보강
3. lifecycle 관점의 entry-wait-exit 연결 summary 정리

즉 이제부터는 "더 쪼개는 것"보다 "지금 만든 구조를 운영과 handoff에서 쉽게 읽히게 하는 것"이 더 자연스럽다.
