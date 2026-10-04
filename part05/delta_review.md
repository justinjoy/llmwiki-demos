# 세션 갱신 관찰

실행 명령: `python3 run_lesson5.py --task delta`

실제 출력은 [delta_actual.txt](delta_actual.txt), API·버전·단계별 이벤트는 [delta_run.json](delta_run.json)에 있습니다.

| 단계 | 실제 관찰 | 이유 |
| --- | --- | --- |
| 1 | mutual +2 | alice와 bob의 양방향 friend 입력 |
| 2 | 변화 없음 | alice에서 carol로의 단방향 입력은 mutual을 만들지 않음 |
| 3 | mutual -2 | bob에서 alice 방향 철회로 양방향 조건 소멸 |

이 예제는 friend/mutual 관계를 하나의 PyreWire `EasySession`에서 갱신합니다. S1/S2/S3를 각각 새 `EasySession`으로 여는 스냅샷 재평가와 구분합니다. `snapshot()`과 `step()`은 동일 세션에서 혼용하지 않습니다. 두 실험의 관계 이름과 출력 수를 섞지 않습니다.
