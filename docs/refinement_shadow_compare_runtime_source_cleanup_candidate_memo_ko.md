# Shadow Compare Runtime Source Cleanup Candidate Memo

## 1. 목적

이 문서는 `S2 trace quality audit`를 한 번 더 파본 결과, 왜 `observe_confirm_v1_fallback`이 계속 남는지에 대한 runtime source cleanup 후보를 정리한다.

## 2. 추가로 확인된 핵심 사실

latest [entry_decisions.detail.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl) sample 기준으로:

- payload에는 `observe_confirm_v2`가 실제로 존재한다.
- payload에는 `observe_confirm_v1`도 함께 존재한다.
- 그런데 같은 row의 `consumer_migration_guard_v1`는
  - `canonical_payload_present = false`
  - `compatibility_payload_present = true`
  - `resolved_field_name = observe_confirm_v1`
  - `used_compatibility_fallback_v1 = true`

로 기록돼 있다.

즉 final payload 기준으로는 `observe_confirm_v2`가 있는데, consumer resolution guard는 여전히 canonical v2를 못 본 것으로 판단하고 있다.

## 3. 코드 기준 해석

[consumer_contract.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_contract.py)의 `resolve_consumer_observe_confirm_resolution()` 자체는 입력 container 안에 `observe_confirm_v2` payload가 있으면 canonical을 우선 읽는 구조다.

반면 [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py) logging path를 보면:

- `build_consumer_migration_guard_metadata(...)`
- `resolve_consumer_observe_confirm_resolution(...)`

를 호출할 때 사용하는 source는 local `observe_confirm_v2`, `observe_confirm_v1` 변수다.

즉 현재 의심되는 지점은 아래 둘 중 하나다.

1. logging guard를 계산하는 시점에는 local `observe_confirm_v2`가 비어 있다.
2. final payload에는 later-stage serialization이나 mirrored payload로 `observe_confirm_v2`가 채워진다.

이 경우 최종 row는 `observe_confirm_v2`를 갖고 있어도, trace-quality provenance는 여전히 `observe_confirm_v1_fallback`으로 남을 수 있다.

## 4. 왜 중요한가

이건 단순 compare warning이 아니라 아래 의미를 가진다.

- compare policy를 바꿔도 `fallback_heavy only`는 쉽게 안 사라질 수 있다.
- trace-quality source warning이 실제 current runtime contract와 어긋나 있을 수 있다.
- 즉 warning이 "현재 runtime이 정말 v1 fallback이다"가 아니라 "guard 계산 시점 기준으론 v1 fallback이었다"일 가능성을 확인해야 한다.

## 5. 현재 판단

현 단계에서 가장 안전한 판단은:

- `S3 compare policy refinement`로 바로 가기 전에
- `runtime source cleanup / consumer migration source audit`

을 한 번 두는 것이다.

이유는 지금 compare warning이 threshold 문제가 아니라 source provenance 문제일 수 있기 때문이다.

## 6. 다음 구체 액션

다음에 보면 좋은 owner는 아래다.

- [consumer_contract.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_contract.py)
- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

점검 질문:

1. local `observe_confirm_v2`는 언제 채워지는가?
2. consumer migration guard는 final payload 직전과 동일한 source를 보고 있는가?
3. `observe_confirm_v2`가 row에 남는 이유가 canonical source인지, compatibility payload mirror인지?

이 3개가 정리되면 `compare policy`를 만질지 `runtime source`를 먼저 정리할지 더 정확히 결정할 수 있다.
