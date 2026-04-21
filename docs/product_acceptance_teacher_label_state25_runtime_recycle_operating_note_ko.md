# Teacher-Label State25 Runtime Recycle Operating Note

## 목적

이 문서는 `state25` / `Step 9`와 직접 충돌하지 않으면서도,
최근 런타임 운영 중 체감된 문제, 현재 반영된 `guarded runtime recycle`,
그리고 다음 관찰 포인트를 다른 스레드가 바로 이해할 수 있게 정리하는 운영 노트다.

핵심 질문은 하나다.

- 장시간 런타임을 계속 유지할수록
  entry / wait / exit가 체감상 루즈해지는가?
- 그렇다면 `60분 주기 재시작`이 도움이 되는가?

## 관찰된 체감 문제

최근 운영 중 아래 체감이 반복적으로 제기됐다.

- 오래 켜둘수록 진입 수가 줄어드는 느낌
- state 해석이 초반보다 무뎌지는 느낌
- wait / exit가 약간 더 느슨해지는 느낌
- 수동으로 볼 때 “초기 런타임이 더 또렷하다”는 체감

이건 아직 수치로 최종 입증한 상태는 아니지만,
운영 체감으로는 충분히 의미 있는 관찰로 본다.

## 코드 기준으로 확인한 사실

### 1. 현재 main runtime 중복 문제는 아님

현재 확인 기준으로 `main.py`는 단일 프로세스로 도는 쪽이다.
즉 과거처럼 중복 메인 프로세스가 얽혀서 상태가 꼬이는 문제와는 다르다.

### 2. 런타임 내부엔 누적성 요소가 존재함

현재 구조상 아래 성격의 상태가 장시간 런타임 안에서 유지된다.

- adaptive profile refresh
- entry / exit utility cache
- dynamic cost cache
- open snapshot cache
- policy runtime state
- shock / rollback / cooldown state

즉 하드 메모리 누수 여부와 별개로,
장시간 가동 시 “상태가 계속 쌓이는 시스템”인 것은 맞다.

### 3. 짧은 refresh는 일부 있지만 상위 policy loop refresh는 현재 비활성 쪽

현재 코드/설정 확인 기준:

- `ENTRY_ADAPTIVE_REFRESH_SEC` 기본 `120`
- `EXIT_ADAPTIVE_REFRESH_SEC` 기본 `120`
- `DYNAMIC_COST_CACHE_TTL_SEC` 기본 `60`
- `ENTRY_UTILITY_STATS_CACHE_TTL_SEC` 기본 `60`
- `.env`에는 `ENTRY_CONDITION_REFRESH_SEC=180`만 확인됨
- `ENABLE_POLICY_LOOP_REFRESH`는 현재 사실상 꺼진 쪽으로 봐야 함

즉 하위 캐시는 조금씩 갱신되지만,
상위 policy refresh는 현재 적극적으로 활용하지 않는 운영에 가깝다.

### 4. policy refresh가 켜져도 충분히 자주 도는 구조는 아님

`policy_service.maybe_refresh(...)`는:

- startup warmup guard가 있고
- loop count 기준 주기적으로만 진입하며
- `POLICY_UPDATE_MIN_INTERVAL_SEC` 기본값이 길다

즉 “짧고 공격적인 런타임 재정렬”과는 결이 다르다.

## 현재 해석

현재 시점 해석은 아래가 가장 보수적이다.

- 아직 “확정 버그”라고 단정할 단계는 아님
- 하지만 장시간 런타임에서 체감 드리프트가 생긴다는 가설은 타당함
- 특히 상위 policy refresh 비활성 + 다양한 cache / adaptive state 유지 구조를 보면
  `초기 상태가 더 또렷하고 오래 갈수록 둔해진다`는 체감은 충분히 설명 가능함

즉 이 아이디어는 감각만의 얘기가 아니라,
현재 코드 구조상도 검토 가치가 있다.

## 현재 운영 설계

### 핵심 문장

`60분`은 recycle 후보를 여는 기준이고,
실제 재시작은 `flat + runtime health/drift 징후`가 같이 맞을 때만 한다.

즉 이 축은 아래 3단으로 읽으면 된다.

1. `due gate`
   60분이 지났는가
2. `safety gate`
   지금 재시작해도 포지션 관리 문맥이 끊기지 않는가
3. `need gate`
   지금 굳이 재시작할 만큼 stale / drift 징후가 있는가

## 제안 아이디어

### 기본 방향

`무조건 60분마다 강제 재부팅`보다는
`guarded hourly recycle`이 더 적절하다.

### 권장 운영안

1. 기본 주기: 60분
2. 단, 열린 포지션이 없을 때만 재시작
3. 열린 포지션이 있으면 다음 safe point까지 재시작 연기
4. health/drift 징후가 없으면 due여도 재시작하지 않음
5. 재시작 직전/직후 상태를 로그로 남김
6. 가능하면 `ENABLE_POLICY_LOOP_REFRESH`도 같이 검토

## gate 상세

### 1. due gate

- 기준: `RUNTIME_RECYCLE_INTERVAL_SEC=3600`
- 의미: “이제 recycle을 검토해볼 시간인가?”
- 주의: 이 값만으로는 재시작하지 않는다

### 2. safety gate

- `open_positions_count == 0`
- `owned_open_positions_count == 0`
- `flat_grace_sec` 경과
- `post_order_grace_sec` 경과

이 gate는 “지금 재시작해도 안전한가?”를 본다.

### 3. health gate

현재 구현된 health 판단은 아래를 본다.

- 최근 runtime summary가 아예 비어 있는가
- `latest_signal_by_symbol`이 비어 있는가
- live signal row timestamp가 stale한가
- 모든 monitored symbol이 stale하면 `health trigger` 후보

현재 기준값:

- `RUNTIME_RECYCLE_SIGNAL_STALE_SEC=900`

### 4. drift gate

현재 구현된 drift 판단은 최근 runtime summary 기본 window를 바탕으로 아래를 본다.

- stage dominance lock
- blocked reason dominance lock
- wait bridge dominance lock
- symbol decision_state lock
- 최근 window에서 `entry_ready_true == 0`
- 필요 시 `display_ready_true == 0`

현재 기준값:

- `RUNTIME_RECYCLE_DRIFT_MIN_ROWS=40`
- `RUNTIME_RECYCLE_DRIFT_STAGE_DOMINANCE=0.85`
- `RUNTIME_RECYCLE_DRIFT_BLOCK_DOMINANCE=0.85`
- `RUNTIME_RECYCLE_DRIFT_DECISION_DOMINANCE=0.90`
- `RUNTIME_RECYCLE_DRIFT_SIGNAL_MIN_COUNT=2`

즉 해석은 아래와 같다.

- 증거가 적으면 `insufficient`
- 경고 1개면 `watch`
- 경고 2개 이상이면 `drifted`
- `drifted`일 때만 due/flat 조건 위에서 recycle action 후보가 된다

### 이 방식이 더 나은 이유

- 캐시/누적 상태를 주기적으로 초기화 가능
- 포지션을 들고 있는 중간에 재시작해서 관리 문맥을 끊는 위험을 줄임
- “초기 런타임의 선명함”을 더 자주 회복할 가능성이 있음
- 상태 드리프트 체감이 맞는지 실험적으로 비교 가능

## 현재 구현 상태

현재 아래까지는 구현되어 있다.

- `guarded runtime recycle` 상태/판단 로직
- `open position 없음` + grace 조건 기반 safe gate
- `runtime_recycle_health_v1` export
- `runtime_recycle_drift_v1` export
- recent runtime summary + latest signal surface 기반 drift 판정
- 기본 모드 `log_only`
- 필요 시 전환 가능한 `reexec` 모드
- `runtime_status`에 recycle 상태 export

즉 지금은 “아이디어만 있는 상태”는 아니고,
`drift-aware 관찰 먼저, 실제 재기동은 보류` 단계까지 들어와 있다.

## 아직 남은 것

아래는 아직 이번 축의 남은 작업이다.

1. `log_only` 한 사이클 관찰 결과 정리
2. restart 전/후 quality compare 로그 보강
3. `ENABLE_POLICY_LOOP_REFRESH` 활성화 실험
4. 실제 live 운영에서 `reexec` 전환 여부 판단

## 구현 로드맵

### R1. 완료

- due + flat + grace guarded recycle
- runtime status export
- old ML 제거 후 순수 runtime 기준으로 관찰

### R2. 이번 반영 완료

- `health_v1` / `drift_v1` 설계 반영
- runtime status slim/detail에 watch surface 추가
- recycle trigger가 `due_and_flat` 단일 조건에서
  `due + flat + health/drift` 조건으로 확장

### R3. 다음 관찰 구간

- `log_only`로 최소 1사이클 관찰
- 실제 live에서 trigger family가 `health`인지 `drift`인지 분리 관찰
- false positive 여부 확인

### R4. 자동화 전환 후보

- false positive가 낮고 체감 개선이 확인되면
  `RUNTIME_RECYCLE_MODE=reexec`
- 여전히 과민하면 threshold 상향 또는 drift signal count 상향

## state25 / Step 9와의 관계

이 아이디어는 `Step 9-E4 / E5`와 직접 경쟁하는 메인 축은 아니다.

현재 `E4/E5`는:

- labeled row 더 누적
- fresh close 증가
- watchlist pair 관측
- coverage 증가

를 기다리는 구간이다.

그 사이에 병렬로 같이 볼 운영 watch 항목이 바로 이 runtime recycle 축이다.

즉 관계를 정리하면:

- `state25 / Step 9`: 라벨 품질, confusion, execution handoff
- `runtime recycle 축`: 장시간 가동 drift 완화와 운영 선명도 회복

둘은 서로 다른 축이지만, 함께 운영하면 상호보완 가능성이 있다.

## 다른 스레드가 바로 이어받을 때 볼 질문

- 현재 체감 드리프트가 실제 지표로도 보이는가?
- `ENABLE_POLICY_LOOP_REFRESH`만 켜도 체감이 개선되는가?
- guarded `60분`이 적절한가, `90분`이 더 나은가?
- safe restart 조건을 “열린 포지션 없음”으로 둘지, “열린 포지션 + pending exit 없음”으로 더 좁힐지?
- restart 전/후 어떤 지표를 비교해야 “루즈해짐”을 증명할 수 있는가?

## 결론

현재 런타임 운영에 대해 가장 타당한 중간 결론은 이렇다.

- 장시간 연속 가동으로 인한 체감 드리프트 가설은 충분히 타당하다
- 지금 당장 무조건 하드 재부팅을 넣기보다
  `guarded hourly recycle`을 `log_only`로 먼저 관찰하는 것이 더 안전하다
- 이 축은 `Step 9-E4/E5` 재확인 리스트와 같이 보기에 좋은 병렬 watch 항목이다
