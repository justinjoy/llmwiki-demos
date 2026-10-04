# 입력 오류 실습 기록

`errors/wrong_arity.dl`은 depends_on에 인자 하나만 주므로 실제 Wirelog 파서가 오류를 반환합니다. `invalid_result.json`에서 종료 오류를 확인합니다.

`errors/reversed_direction.dl`은 order → pay를 pay → order로 뒤집습니다. 두 열 모두 symbol이므로 실제 엔진은 실행에 성공합니다. `direction_result.json`을 ARCH-01 v1 §1 및 2교시 관계 사전과 대조하면 의미 오류를 찾을 수 있습니다.

위 기록은 실행 시연 설명입니다. 본인이 수정한 입력과 실제 검토는 review.md에 기록합니다.
