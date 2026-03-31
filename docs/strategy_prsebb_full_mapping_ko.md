# 전략-PRSEBB 전체 매핑 정리

## 1. 문서 목적

이 문서는 아래 4가지를 한 번에 정리하기 위한 기준서다.

1. 사용자가 정의한 `1~15 전략 요소`가 현재 시스템에 어디에 녹아 있는지
2. `Position / Response / State / Evidence / Belief / Barrier`가 각각 무엇을 맡아야 하는지
3. 지금까지 이미 적용된 조정들이 어느 레이어에 들어가 있는지
4. 전략 요소끼리, 레이어끼리 `겹쳐도 되는 것`과 `겹치면 안 되는 것`이 무엇인지

이 문서는 단순 아이디어 메모가 아니라, 현재 코드베이스 기준의 `실제 구조 정리 문서`다.

---

## 2. 한눈 요약

| 구분 | 현재 반영 강도 | 요약 |
|---|---|---|
| 1단계: 시장의 뼈대 | 약함~부분 | 세션 박스, 단일 S/R, 박스 위치는 일부 들어와 있으나, `세션 3분할`, `당일 시가`, `멀티TF S/R`, `4번의 법칙`은 아직 owner가 약하다 |
| 2단계: 에너지의 흐름 | 부분~강함 | 더블BB, 변동성, 정배열 품질, 이격도 scalar는 들어와 있으나, 규칙형 해석보다 `보정 계수`로 쓰이는 비중이 크다 |
| 3단계: 진입 쐐기 | 강함 | 밴드/박스 반응, 캔들 rejection, 패턴류는 Response 쪽에 비교적 잘 들어와 있다 |
| PRSEBB 구조 완성도 | 중상 | 구조는 갖춰져 있고 연결도 된다. 다만 `1단계 구조 우선` 철학을 완전히 owner로 올린 상태는 아니다 |
| 현재 엔진 성격 | 반응형 우세 | 현재 엔진은 `구조 우선 엔진`보다는 `박스/밴드 반응형 엔진 + 구조 보조`에 더 가깝다 |

### 핵심 진단

| 항목 | 현재 상태 |
|---|---|
| 가장 강한 축 | `Double BB + Box 반응 + 캔들/패턴` |
| 가장 약한 축 | `세션 3박스`, `당일 시가`, `멀티TF S/R`, `4번의 법칙`, `1분봉 매물대 필터` |
| 구조적으로 맞게 잡힌 부분 | `Position은 위치`, `Response는 반응`, `State는 환경`, `Evidence는 합산`, `Belief는 지속성`, `Barrier는 차단` |
| 아직 흔들리는 부분 | `1단계 뼈대가 semantic owner가 아니라 context 보조 성격에 가까운 점` |

---

## 3. 현재 시스템의 큰 흐름

| 단계 | 역할 | 현재 구현 위치 |
|---|---|---|
| Market Data / Context | 원본 가격, 박스, 밴드, 이평, S/R, 패턴용 window를 준비 | `backend/services/context_classifier.py`, `backend/trading/session_manager.py` |
| Position | 지금 어디에 있는지 해석 | `backend/trading/engine/position/*` |
| Response | 그 위치에서 무슨 반응이 나왔는지 해석 | `backend/trading/engine/response/*` |
| State | 시장 환경과 품질을 보정 계수로 해석 | `backend/trading/engine/state/*` |
| Evidence | Position/Response/State를 합쳐 BUY/SELL 근거화 | `backend/trading/engine/core/evidence_engine.py` |
| Belief | 근거의 지속성과 우위를 누적 | `backend/trading/engine/core/belief_engine.py` |
| Barrier | middle chop, conflict, liquidity, direction policy로 차단 | `backend/trading/engine/core/barrier_engine.py` |
| Observe/Confirm | 실행 가능한 archetype/action으로 handoff | `backend/trading/engine/core/observe_confirm_router.py` |
| Forecast / Energy / Consumer | 실행 보조, 예측, 운영용 압축/소비 | `backend/trading/engine/core/forecast_*`, `backend/services/*` |

---

## 4. PRSEBB 레이어 역할표

| 레이어 | 이 레이어가 답해야 하는 질문 | 주 입력 | 주 출력 | 해야 하는 일 | 하면 안 되는 일 |
|---|---|---|---|---|---|
| Position | `지금 가격은 어디에 있는가?` | box, bb20, bb44, ma, sr, trendline | zone, bias, conflict, position energy | 상단/중앙/하단, edge proximity, 위치 에너지 설명 | 반응까지 해석해서 바로 BUY/SELL 확정 |
| Response | `그 위치에서 어떤 반응이 나왔는가?` | 캔들, wick, 밴드 터치/이탈, 박스 bounce/break, 패턴 | hold, reject, break, reclaim, lose | 이벤트/반응 추출 | 큰 구조 위치를 owner처럼 선언 |
| State | `지금 시장 환경은 어떤가?` | market mode, direction policy, liquidity, volatility, disparity, alignment | gain, damp, penalty | 반응 해석의 품질 보정 | side/archetype를 직접 결정 |
| Evidence | `지금 근거가 어느 쪽으로 쌓이는가?` | Position + Response + State | buy/sell reversal/continuation evidence | 종합 근거 계산 | raw 사실을 새로 발명 |
| Belief | `그 근거가 얼마나 지속되고 있는가?` | evidence 시계열 | belief, persistence, dominance | 누적, streak, 지속성 반영 | 새로운 반응 신호 생성 |
| Barrier | `좋아 보여도 지금 막아야 하는가?` | position 구조, state penalty, evidence, belief | buy/sell barrier | middle chop, conflict, liquidity, policy 차단 | semantic 의미 자체를 뒤집기 |

### 레이어별 현재 구현 강도

| 레이어 | 현재 구현 강도 | 설명 |
|---|---|---|
| Position | 강함 | box + bb20 + bb44 기반 위치 해석은 현재 시스템의 핵심이다 |
| Response | 강함 | band/box rejection-break, candle wick, pattern이 비교적 잘 붙어 있다 |
| State | 중간 | 상태 요약과 gain/damp는 있으나 세밀한 전략 규칙보다 압축 계수에 가깝다 |
| Evidence | 강함 | reversal/continuation evidence 조합은 꽤 명확하다 |
| Belief | 중간~강함 | EMA와 streak 기반 지속성은 잘 정리돼 있다 |
| Barrier | 강함 | middle/conflict/liquidity/policy 차단 구조가 비교적 잘 들어가 있다 |

---

## 5. 사용자 전략 1~15 전체 매핑표

### 5-1. 총괄 표

| 번호 | 전략 항목 | 의도 | 1차 owner | 2차 owner | 현재 반영도 | 현재 상태 한 줄 요약 |
|---|---|---|---|---|---|---|
| 1 | 3단 세션 박스권 | 시간대별 구조 뼈대 | Position | State | 부분 | 세션 박스는 있으나 PRSEBB는 사실상 한 박스 위주로 사용 |
| 2 | 박스 복사 Expansion | 돌파 후 1차 타겟/되돌림 예측 | Position | Evidence | 약함 | helper는 있으나 semantic 입력 owner는 아님 |
| 3 | 당일 시가 돌파 | 당일 방향 기준선 | Position | State/Evidence | 없음 | 현재는 당일 시가가 아니라 신호봉 open만 메타데이터에 있다 |
| 4 | 다중 S/R | 주요 지지/저항 도달/반응 | Position | Response/Barrier | 부분 | 현재는 최근 H1 high/low 수준의 단순 S/R가 중심 |
| 5 | 4번의 법칙 | 반복 테스트 후 돌파 압력 | Response | State/Evidence | 약함 | legacy scorer엔 touch count가 있지만 PRSEBB owner는 아님 |
| 6 | Double BB 변곡/돌파 | 기본 위치/반응 앵커 | Position/Response | Evidence | 강함 | 현재 엔진의 가장 강한 축 |
| 7 | 이격도 타점 | 과열/과매도 정도 | State | Evidence | 부분 | 값은 들어오나 규칙형 타점 로직은 약함 |
| 8 | 다중 이평 정배열/역배열 | 구조 정렬과 응축 | Position/State | Evidence | 부분 | MA 값과 alignment는 있으나 세밀한 배열 논리는 축약돼 있음 |
| 9 | 추세선 | 대각 구조선 반응 | Position/Response | Evidence | 약함 | 축은 있으나 runtime 주입이 약함 |
| 10 | 이격도 다이버전스 | 반전 힌트 | Response/State | Evidence | 없음 | 아직 없다 |
| 11 | 캔들 꼬리 | rejection 확인 | Response | Evidence | 강함 | 현재 Response에서 잘 반영됨 |
| 12 | 캔들 패턴 | 진입 쐐기 | Response | Evidence | 부분 | wick/body 해석은 있으나 패턴 taxonomy는 약함 |
| 13 | 차트 형태 | 구조 완성 확인 | Response | Evidence | 강함 | 더블탑/바텀, H&S, 역H&S 반영됨 |
| 14 | RSI / DI 과매수과매도 | 극단값 확인 | State | Evidence | 부분 | 값은 들어오지만 semantic owner로 강하지 않음 |
| 15 | 1분봉 매물대 필터 | 최종 손익비 필터 | Barrier | Observe/Confirm | 없음 | 아직 PRSEBB 핵심 입력에 없다 |

### 5-2. 세부 표

| 번호 | 전략 항목 | 현재 어떤 형태로 들어와 있는가 | 현재 owner가 맞는가 | 빠진 것 | 현재 판단 |
|---|---|---|---|---|---|
| 1 | 3단 세션 박스권 | `SessionManager`에 ASIA/EUROPE/USA 세션 정의와 박스 계산이 있다 | 부분적으로만 맞다 | 세션 3개가 각각 semantic axis로 직접 안 들어간다 | `개념은 존재, semantic owner는 약함` |
| 2 | 박스 복사 Expansion | `get_expansion_target()` helper가 있다 | 아직 아님 | expansion target이 Position/Evidence 입력으로 안 들어간다 | `기능 helper 수준` |
| 3 | 당일 시가 돌파 | `current_open`은 들어오지만 당일 전체 open이 아니다 | 아니다 | daily open 기준선과 reclaim/break 반응 | `사실상 미반영` |
| 4 | 다중 S/R | 최근 H1 high/low가 support/resistance로 들어간다 | 일부만 맞다 | H1/H4/D1/W1 다층 구조, 1차/2차 S/R | `단순화된 버전만 존재` |
| 5 | 4번의 법칙 | scorer에 touch count가 있다 | 아니다 | PRSEBB response/state/evidence 입력으로 승격 필요 | `legacy only` |
| 6 | Double BB 변곡/돌파 | bb20, bb44 위치와 hold/reject/break가 Position/Response에 강하게 있다 | 맞다 | 사용자 세부 기준의 더 정교한 threshold | `핵심 owner 맞음` |
| 7 | 이격도 타점 | `current_disparity`가 State quality에 들어간다 | 반쯤 맞다 | 상승장/하락장별 명시 임계값 규칙 | `quality scalar 수준` |
| 8 | 다중 이평 정배열/역배열 | `ma20/60/120/240/480`, `ma_alignment`가 들어간다 | 부분적으로 맞다 | 압축/수렴, 다층 배열 논리 강화 | `축은 있으나 해석이 얕음` |
| 9 | 추세선 | 모델 필드는 있으나 실제 runtime 공급이 약하다 | 아니다 | trendline 값 주입과 reclaim/break 반응 | `거의 미반영` |
| 10 | 이격도 다이버전스 | 현재 별도 계산 없음 | 아니다 | divergence detector | `미반영` |
| 11 | 캔들 꼬리 | candle rejection raw로 반영 | 맞다 | 위치/SR 연동 강화 정도만 남음 | `잘 들어가 있음` |
| 12 | 캔들 패턴 | 강한 body/wick 성질은 반영되지만 패턴 taxonomy는 약하다 | 부분적으로 맞다 | hammer, engulfing 등 명시 패턴 | `부분 반영` |
| 13 | 차트 형태 | double top/bottom, H&S, inverse H&S가 pattern_response에 있다 | 맞다 | neckline 품질, pattern state 보강 | `잘 들어가 있음` |
| 14 | RSI / DI 과매수과매도 | metadata에는 있으나 PRSEBB 핵심 판단엔 약하다 | 부분적으로 맞다 | threshold-based semantic usage | `값 저장 위주` |
| 15 | 1분봉 매물대 필터 | 현재 핵심 semantic 레이어엔 없다 | 아니다 | 1분봉 VP/매물대 입력, 손익비 필터 | `미반영` |

---

## 6. PRSEBB 외에 이미 적용된 것들

이 표는 `1~15 전략표에는 직접 안 적혀 있지만`, 실제 런타임에 이미 들어가 있는 중요한 조정들을 정리한 것이다.

| 영역 | 이미 적용된 내용 | 현재 owner | 의미 |
|---|---|---|---|
| Position | edge에서는 authority 강화, middle에서는 handoff 강화 | Position/Evidence | 끝단은 Position이 주도하고 중앙은 뒤 레이어가 주도하도록 조정 |
| Position | weak alignment를 bias 또는 unresolved로 softening | Position | 너무 이른 `ALIGNED_*_WEAK` 확정을 줄임 |
| Position | `raw_alignment_label`, `alignment_softening` 메타 보존 | Position | raw 판단과 soft 판단을 둘 다 추적 가능 |
| Response | 하단 터치 후 바깥 마감은 hold가 아니라 break로 정리 | Response | `BUY hold` 오판 감소 |
| Response | 상단 터치 후 되밀림은 reject로 읽는 구조 강화 | Response | `SELL reject` 감도 개선 |
| Observe/Confirm | middle/no-SR 진입 억제 | Observe/Confirm | 가운데에서 근거 없이 진입하는 케이스 감소 |
| Observe/Confirm | outer-band reversal support guard | Observe/Confirm | bb44 지지가 없으면 reversal confirm 억제 |
| Observe/Confirm | structural lower break 우선 | Observe/Confirm | 하단 이탈형은 `SELL continuation` 쪽으로 정리 |
| Observe/Confirm | mixed upper reject override | Observe/Confirm | global lower/middle 안의 local upper reject를 `SELL` 후보로 살림 |
| Evidence | middle compress, edge authority 반영 | Evidence | central zone에서 Position 과민 반응 억제 |
| Belief | EMA + streak 누적 | Belief | 한 봉 반짝과 지속 우위를 구분 |
| Barrier | conflict, middle chop, liquidity, direction policy 차단 | Barrier | 의미가 있어도 실행을 막아야 할 때 차단 |
| Context | preflight 2H trend/range/shock | State 상위 context | 큰 시장 환경의 상위 가드 |
| Consumer/Execution | energy helper, runtime guards | Consumer | semantic truth를 바꾸지 않고 실행 보조만 담당 |

---

## 7. 전략과 레이어가 겹쳐도 되는가

## 7-1. 결론

겹쳐도 된다.  
정확히는 `같은 사실이 여러 레이어에 들어가도 되지만, 역할이 달라야 한다`.

즉 `중복 자체`가 문제는 아니다.  
문제는 `같은 의미를 여러 번 세거나`, `한 레이어가 다른 레이어의 일을 빼앗는 것`이다.

## 7-2. 겹쳐도 되는 구조

| 사실 | Position에서 하는 말 | Response에서 하는 말 | State에서 하는 말 | Evidence에서 하는 말 | 정상 여부 |
|---|---|---|---|---|---|
| 가격이 볼밴 상단 근처 | `상단 위치다` | `상단 reject가 나왔다` | `지금 range라 reversal 의미가 크다` | `sell reversal evidence가 강해진다` | 정상 |
| 가격이 박스 하단 근처 | `하단 위치다` | `하단 bounce인지 break인지` | `trend인지 range인지` | `buy reversal 또는 sell continuation 중 무엇이 우세한지` | 정상 |
| 가격이 중앙 근처 | `middle / unresolved다` | `mid reclaim / mid lose가 나왔다` | `noise/conflict가 높은지` | `바로 진입보다 wait 쪽이 맞는지` | 정상 |
| S/R 근처 | `support/resistance 근접` | `hold / break / reject 반응` | `유동성/환경 품질` | `근거 강화 또는 약화` | 정상 |

## 7-3. 겹치면 안 되는 구조

| 잘못된 겹침 | 왜 문제인가 |
|---|---|
| Position이 이미 `상단 reject니까 SELL 확정`까지 말함 | Position이 Response 역할까지 먹어버림 |
| Response가 `지금 큰 위치는 하단이다`를 직접 owner처럼 선언 | Response가 Position 역할까지 먹어버림 |
| 같은 의미가 Position fit, Evidence base, Observe routing에서 세 번 과대가산됨 | 한 가지 사실이 과대평가돼 side가 왜곡됨 |
| Barrier가 semantic side를 새로 바꿈 | Barrier는 막는 역할이지 의미를 다시 정의하는 owner가 아님 |
| Energy helper가 side/archetype를 재결정함 | execution helper가 semantic owner를 침범함 |

## 7-4. 겹침 허용 원칙

| 원칙 | 설명 |
|---|---|
| 위치는 Position | 어디에 있느냐 |
| 반응은 Response | 그 위치에서 무슨 이벤트가 나왔느냐 |
| 환경은 State | 지금 시장 환경이 그 반응을 얼마나 믿게 하느냐 |
| 종합은 Evidence | 근거를 한쪽으로 모으는 곳 |
| 지속성은 Belief | 그 근거가 유지되느냐 |
| 차단은 Barrier | 좋아 보여도 막아야 하느냐 |

---

## 8. 현재 코드 기준 레이어별 상세 진단

### 8-1. Position 상세 진단

| 항목 | 현재 상태 | 평가 |
|---|---|---|
| box 위치 | 강하게 반영 | 좋음 |
| bb20 위치 | 강하게 반영 | 좋음 |
| bb44 위치 | 강하게 반영 | 좋음 |
| weak alignment softening | 적용됨 | 좋음 |
| middle handoff | 적용됨 | 좋음 |
| S/R 위치 | 단일축으로 반영 | 아직 단순함 |
| 추세선 위치 | 축은 있으나 약함 | 보강 필요 |
| 세션 3박스 전체 반영 | 약함 | 보강 필요 |
| 당일 시가 기준 | 사실상 없음 | 신규 owner 필요 |

### 8-2. Response 상세 진단

| 항목 | 현재 상태 | 평가 |
|---|---|---|
| bb20 lower hold/break | 반영 | 좋음 |
| bb20 upper reject/break | 반영 | 좋음 |
| bb44 hold/reject | 반영 | 좋음 |
| box lower bounce/break | 반영 | 좋음 |
| box upper reject/break | 반영 | 좋음 |
| mid reclaim / mid lose | 반영 | 좋음 |
| candle wick rejection | 반영 | 좋음 |
| pattern 구조 | 반영 | 좋음 |
| 4번의 법칙 | 없음 | 보강 필요 |
| divergence | 없음 | 보강 필요 |
| 1분봉 매물대 반응 | 없음 | 보강 필요 |

### 8-3. State 상세 진단

| 항목 | 현재 상태 | 평가 |
|---|---|---|
| market_mode | 반영 | 좋음 |
| direction_policy | 반영 | 좋음 |
| liquidity_state | 반영 | 좋음 |
| volatility 품질 | 반영 | 좋음 |
| noise/conflict | 반영 | 좋음 |
| disparity scalar | 반영 | 부분 |
| ma_alignment | 반영 | 부분 |
| 세밀한 상승장/하락장별 이격 규칙 | 없음 | 보강 필요 |
| 다이버전스 state | 없음 | 보강 필요 |

### 8-4. Evidence 상세 진단

| 항목 | 현재 상태 | 평가 |
|---|---|---|
| Position fit | 강함 | 좋음 |
| Response 기반 reversal/continuation 근거 | 강함 | 좋음 |
| State gain/damp 반영 | 강함 | 좋음 |
| middle compress | 적용됨 | 좋음 |
| 전략 1단계 구조 우선 반영 | 아직 약함 | 보강 필요 |

### 8-5. Belief / Barrier 상세 진단

| 레이어 | 현재 상태 | 평가 |
|---|---|---|
| Belief | evidence를 EMA와 streak로 누적 | 구조적으로 좋음 |
| Barrier | middle chop, conflict, liquidity, policy 차단 | 구조적으로 좋음 |
| 1분봉 매물대 필터형 barrier | 없음 | 보강 필요 |

---

## 9. 코드 기준 주요 연결점

| 역할 | 파일 |
|---|---|
| 세션 박스 계산 | `backend/trading/session_manager.py` |
| 엔진 컨텍스트 조립 | `backend/services/context_classifier.py` |
| Position vector/snapshot 조립 | `backend/trading/engine/position/builder.py` |
| Position 해석/에너지 | `backend/trading/engine/position/interpretation.py` |
| Response raw 조립 | `backend/trading/engine/response/builder.py` |
| band 반응 | `backend/trading/engine/response/band_response.py` |
| box 구조 반응 | `backend/trading/engine/response/structure_response.py` |
| candle rejection | `backend/trading/engine/response/candle_response.py` |
| pattern 구조 | `backend/trading/engine/response/pattern_response.py` |
| Response vector 압축 | `backend/trading/engine/response/transition_vector.py` |
| State raw/vector 조립 | `backend/trading/engine/state/builder.py` |
| State 품질 계산 | `backend/trading/engine/state/quality_state.py` |
| Evidence 조립 | `backend/trading/engine/core/evidence_engine.py` |
| Belief 누적 | `backend/trading/engine/core/belief_engine.py` |
| Barrier 차단 | `backend/trading/engine/core/barrier_engine.py` |
| Observe/Confirm 라우팅 | `backend/trading/engine/core/observe_confirm_router.py` |

---

## 10. 현재 철학과 엔진의 차이

| 항목 | 사용자가 원하는 철학 | 현재 엔진의 실제 성격 |
|---|---|---|
| 우선순위 | `1단계 구조 -> 2단계 에너지 -> 3단계 트리거` | `box/band 반응 + trigger` 쪽이 더 강함 |
| Position 역할 | 세션/시가/SR 중심 구조 owner | box/bb 중심 location owner |
| Response 역할 | 구조 위에서 나온 반응 확인 | 잘 구현돼 있음 |
| State 역할 | 추세/이격/정배열 규칙형 보정 | 현재는 scalar quality 보정 위주 |
| Evidence 역할 | 구조 우선 종합 판단 | 현재는 반응형 근거 합산이 상대적으로 강함 |

### 요약

| 문장 | 현재 판정 |
|---|---|
| `지금 시스템은 구조 우선 시스템인가?` | 아직 아니다 |
| `지금 시스템은 반응형 시스템인가?` | 상대적으로 그렇다 |
| `PRSEBB 구조 자체가 잘못됐는가?` | 아니다 |
| `owner 재배치가 필요한가?` | 그렇다 |

---

## 11. 다음 재배치 우선순위

| 우선순위 | 해야 할 일 | 왜 중요한가 |
|---|---|---|
| 1 | 세션 3박스, 당일 시가, 멀티TF S/R를 Position/State owner로 승격 | 네 전략의 `시장 뼈대`를 semantic 중심으로 올리기 위해 |
| 2 | 4번의 법칙, divergence, 1분봉 매물대 필터를 Response/Barrier에 추가 | 실행 품질과 timing 정확도를 높이기 위해 |
| 3 | disparity, RSI/DI를 값 저장이 아니라 규칙형 해석으로 승격 | 에너지 층을 네 방식대로 정교화하기 위해 |
| 4 | Evidence 조합비를 `구조 우선 -> 에너지 -> 트리거` 순으로 재배치 | 현재 반응형 쏠림을 줄이기 위해 |

---

## 12. 최종 결론

| 질문 | 답 |
|---|---|
| 지금 PRSEBB가 네 전략을 아예 못 담는 구조인가? | 아니다. 담을 수 있는 구조다 |
| 지금 PRSEBB가 네 전략을 이미 완전히 담고 있는가? | 아니다 |
| 가장 잘 담긴 부분은? | Double BB, box/band response, candle rejection, pattern |
| 가장 덜 담긴 부분은? | 세션 3박스, 당일 시가, 멀티TF S/R, 4번의 법칙, 1분봉 매물대 |
| 겹치는 건 문제인가? | 역할만 분리되면 괜찮다 |
| 지금 가장 필요한 작업은? | `1단계 시장의 뼈대`를 semantic owner로 끌어올리는 재배치 |

### 한 줄 요약

현재 시스템은 `PRSEBB 구조는 맞게 세워졌지만, 사용자가 원하는 철학 대비 아직 1단계 구조 owner가 약하고 2~3단계 반응 owner가 강한 상태`다.
