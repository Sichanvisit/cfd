# R4 Bounded Live / Allowlist Expansion Operating Spec

## 1. 목적

이 문서는 R4 다음 운영 단계에서

- `threshold_only 유지`
- `allowlist 확장`
- `bounded live / partial_live 준비`

를 어떤 순서와 조건으로 다룰지 고정하는 운영 spec이다.

## 2. 현재 출발점

현재 baseline:

- preview / shadow: healthy
- promotion gate: pass
- chart rollout: hold
- semantic canary: hold
- live mode: `threshold_only`
- current allowlist: `BTCUSD`

즉 현재는
`partial_live 전 단계`
이자
`allowlist 후보를 정리할 수 있는 단계`
로 본다.

## 3. 운영 action 층위

### Level 0. `stay_threshold_only`

의미:

- mode 유지
- allowlist 유지
- preview / runtime / chart 관측 지속

현재 기본 action이다.

### Level 1. `expand_allowlist within threshold_only`

의미:

- semantic live mode는 그대로 `threshold_only`
- symbol allowlist만 제한적으로 확장

이 단계는 `partial_live`보다 앞선다.

### Level 2. `prepare_bounded_live`

의미:

- allowlist 확장을 일정 기간 관찰한 뒤
- rollback / kill switch 기준이 실제로 동작하는지 재확인
- partial_live로 갈지 여부만 판단

아직 실제 partial_live 적용은 포함하지 않는다.

### Level 3. `enable_partial_live`

의미:

- semantic action이 runtime에 일부 직접 영향

현재 단계에서는 아직 진입 금지다.

## 4. allowlist 확장 순서

현재 추천 순서는 아래와 같다.

1. `NAS100`
2. `XAUUSD`

`BTCUSD`는 기준 심볼로 유지한다.

## 5. NAS100 확장 조건

아래를 만족할 때만 NAS100을 첫 확장 후보로 본다.

- runtime latest가 한 관찰 윈도우 동안 계속 `BUY` 방향 유지
- `nas_clean_confirm_probe`가 반복적으로 관측
- 최근 fallback이 계속 `symbol_not_in_allowlist` 중심
- `semantic_unavailable`, `compatibility_mode_blocked`가 새로 튀지 않음
- chart rollout이 급격히 악화되지 않음
- rollback / kill switch trigger 없음

운영 해석:

- NAS100은 `관찰용 threshold_only 확장` 후보지,
  `partial_live 후보`가 아니다.

## 6. XAUUSD 확장 조건

아래를 만족할 때만 XAUUSD를 두 번째 확장 후보로 본다.

- latest runtime 방향이 더 일관적으로 정리될 것
- `xau_second_support_buy_probe` 또는 `xau_upper_sell_probe` 중 한 방향 우세가 분명해질 것
- `probe_against_default_side`가 반복되지 않을 것
- fallback reason이 allowlist 밖의 구조 이슈로 바뀌지 않을 것

운영 해석:

- XAU는 directional presence는 좋지만
  현재 시점 runtime 방향 흔들림이 있어
  NAS 다음 후보로 둔다.

## 7. 확장 금지 조건

아래 중 하나면 allowlist 확장을 하지 않는다.

- chart rollout `overall hold`가 더 악화된다
- `Stage B`, `Stage E`에서 stop 성격 이유가 나타난다
- canary에서 `semantic_unavailable`, `compatibility_mode_blocked` 비중이 커진다
- preview audit / shadow compare가 healthy를 잃는다
- rollback / kill switch contract에 걸리는 이벤트가 발생한다

## 8. partial_live 진입 전 필요 조건

아래를 모두 만족해야 그제야 `partial_live`를 논의한다.

- allowlist 확장 후 관찰 윈도우를 최소 한 번 통과
- canary status가 `hold`에서 `pass`로 올라옴
- chart rollout이 더 이상 전체 `hold` 중심이 아님
- preview / shadow healthy 유지
- rollback path가 실제 운영에서 설명 가능

즉 `allowlist 확장`과 `partial_live`는 같은 단계가 아니다.

## 9. 현재 운영 결론

현재 결론은 아래다.

- 기본 action: `stay_threshold_only`
- 다음 허용 가능한 변화: `NAS100 allowlist 확장 검토`
- 그 다음 후보: `XAUUSD`
- 아직 허용되지 않는 변화: `partial_live`

## 10. 완료 기준

- allowlist 확장과 partial_live가 같은 것으로 취급되지 않는다
- 다음 심볼 확장 순서와 금지 조건을 문서로 설명할 수 있다
- 실제 mode 변경 전 운영 기준이 흔들리지 않는다

## 11. Current Runtime Note

이 spec 작성 이후 실제 운영 설정은 아래처럼 반영됐다.

- current allowlist: `BTCUSD,NAS100`
- current mode: `threshold_only`

즉 이 문서에서 말한 `Level 1. expand_allowlist within threshold_only`는
지금 기준으로 `NAS100`까지 이미 적용된 상태다.

따라서 다음 실제 후보는:

- `XAUUSD`

로 읽는다.

재확인 메모:

- [refinement_r4_allowlist_expansion_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_reconfirm_memo_ko.md)
