# LLM 프롬프트 실행 안내

실행 장소는 **터미널**입니다. ZIP을 풀고 `run_lesson1.py`와 `raw/`가 보이는 `demos/part01/` 폴더로 이동하세요. 대화창에 파일을 첨부할 필요가 없습니다.

Python 3.9 이상과 본인이 사용하는 LLM CLI의 설치·로그인이 필요합니다. 1교시는 Wirelog 설치 없이 진행합니다. 아래 명령의 `python3`는 Windows에서 설치 방식에 따라 `python`으로 바꾸세요.

## 1교시: 첫 실행

Claude 사용자의 예입니다. 먼저 실제 전송할 입력을 확인합니다.

```sh
python3 run_lesson1.py --cli claude --task pay --dry-run
```

출력된 `input.txt`에는 `prompt.txt`와 원문 3개가 포함됩니다. 이 단계는 LLM을 호출하지 않습니다. 확인 후 실행합니다.

```sh
python3 run_lesson1.py --cli claude --task pay --overwrite
```

`--overwrite`는 배포된 TODO 템플릿을 채우기 위한 옵션입니다. 기존 내용은 실행 기록 폴더의 `previous.md`에 백업합니다. LLM 응답은 `wiki/services/pay.md`에 저장됩니다. 이 파일을 열고 원문의 문서 버전·절과 대조하세요.

## 도구별로 바꿀 부분

같은 스크립트에서 `--cli` 값만 바꿉니다.

```sh
python3 run_lesson1.py --cli codex --task pay --overwrite
python3 run_lesson1.py --cli claude --task pay --overwrite
python3 run_lesson1.py --cli cursor-agent --task pay --overwrite
python3 run_lesson1.py --cli copilot --task pay --overwrite
python3 run_lesson1.py --cli agy --task pay --overwrite
```

| 지정한 CLI | 스크립트 내부 호출 |
| --- | --- |
| `codex` | `codex exec ... -`에 프롬프트를 표준 입력으로 전달 |
| `claude` | `claude --output-format text -p 프롬프트본문` |
| `cursor-agent` | `cursor-agent --output-format text -p 프롬프트본문` |
| `copilot` | `copilot --silent -p 프롬프트본문` |
| `agy` (Antigravity) | `agy -p 프롬프트본문` |
| 그 외 실행 파일 | `실행파일 -p 프롬프트본문` |

위 네 도구의 옵션은 제작 환경의 `--help`로 확인했습니다. **Codex의 `-p`는 프로필 선택 옵션**이므로 그대로 호출하면 안 됩니다. 공통 스크립트가 이 차이를 처리합니다. Cursor 실행 파일 이름이 `agent`인 환경에서는 `--cli agent`를 지정하세요. 다른 제품도 `agent` 이름을 사용할 수 있으므로 실제 설치 경로를 확인하세요.

Antigravity의 실행 명령은 **`agy -p`**입니다. 수업 환경에서 확인한 실행 파일 이름 `agy`를 지정합니다.

```sh
python3 run_lesson1.py --cli agy --task pay --overwrite
```

IDE만 여는 명령은 사용할 수 없습니다. 교육 담당자는 각 CLI가 비대화식으로 응답 본문을 반환하는지 사전 확인합니다. 실행 파일 이름이 다르면 그 이름이나 절대 경로를 전달합니다. 별칭·셸 함수 대신 실행 파일을 지정합니다.

모델 등 추가 옵션은 인자별로 전달합니다.

```sh
python3 run_lesson1.py --cli claude --task pay --overwrite --cli-arg=--model --cli-arg=수업에서_지정한_모델명
```

## 1교시 실습 순서

아래의 `claude`를 본인의 실행 파일 이름으로 바꾸세요. 각 실행이 끝난 후 결과를 검토하고 다음 단계로 진행합니다.

```sh
# 실습 A: pay 생성·검토 후 order 생성·검토
python3 run_lesson1.py --cli claude --task pay --overwrite
python3 run_lesson1.py --cli claude --task order --overwrite

# 실습 B: 장애 페이지 → 탐색 입구 → 질문의 답·근거
python3 run_lesson1.py --cli claude --task incident --overwrite
python3 run_lesson1.py --cli claude --task index --overwrite
python3 run_lesson1.py --cli claude --task explore --overwrite
python3 run_lesson1.py --cli claude --task log --overwrite

# 저장된 위키의 상대 파일 링크 검사
python3 check_links.py wiki
```

| 단계 | 사용 프롬프트 | 저장 결과 |
| --- | --- | --- |
| pay | `prompt.txt` | `wiki/services/pay.md` |
| order | `prompts/order.txt` | `wiki/services/order.md` |
| incident | `prompts/incident.txt` | `wiki/incidents/INC-03.md` |
| index | `prompts/index.txt` | `wiki/index.md` |
| explore | `prompts/explore.txt` | `exploration.csv` |
| log | `prompts/log.txt` | `wiki/log.md` |

모든 경로는 `demos/part01/` 기준입니다. 생성한 내용이 틀리면 편집기에서 고친 뒤 `review.md`에 수정 이유를 기록합니다. `exploration.csv`와 `log.md`도 생성 초안이며 사람이 검토한 기록으로 자동 승인되지 않습니다.

강사 시연에서 여섯 단계를 연속으로 실행하려면 `--task all`을 사용합니다. 여섯 번의 LLM 호출이 발생하며, 중간 실패 또는 선행 파일의 TODO가 있으면 중단합니다. 이미 성공한 앞 단계 파일과 기록은 남습니다.

```sh
python3 run_lesson1.py --cli claude --task all --overwrite
```

## 다른 프롬프트에도 사용하는 공통 스크립트

`run_prompt.py`의 **`-p`는 프롬프트 파일 경로**, `-c`는 첨부할 텍스트 파일, `-o`는 응답 저장 경로입니다. LLM 호출 시에는 파일 경로가 아니라 파일의 실제 내용을 전달합니다.

다음 명령은 1교시 pay 단계를 직접 실행하는 동일한 방법입니다.

```sh
python3 run_prompt.py --cli claude -p prompt.txt -c raw/ARCH-01_v1.md -c raw/ADR-07_v1.md -c raw/INC-03_v1.md -o wiki/services/pay.md --overwrite
```

다른 교시에서는 해당 `prompt.txt`와 과제에 필요한 원문·앞 단계 결과를 `-c`로 지정합니다. 폴더를 자동 탐색하거나 모든 정답을 첨부하지 않습니다. 여러 파일을 요청하는 프롬프트는 응답 전체가 `-o` 하나에 저장되므로 산출물별 프롬프트로 나누거나 검토 후 파일별로 분리합니다. 다른 교시의 Wirelog 질의는 별도 실습 패키지의 `tools/query.py`를 사용합니다.

## 실행 기록과 실패 처리

- 1교시 기록: `runs/날짜-고유번호/`.
- 공통 스크립트 기록: 현재 폴더의 `runs/` 또는 `--log-dir`로 지정한 폴더.
- `input.txt`: 실제 전송한 프롬프트와 원문. `stdout.txt`: 실제 응답. `stderr.txt`: CLI 오류·진행 로그. `run.json`: 실행 상태·출력 경로·입력 해시.
- 성공한 응답만 결과 파일로 저장합니다. 실패·빈 응답·시간 초과 시 기존 결과는 유지합니다. 응답 바깥의 코드 블록 하나와 ANSI 색상 코드는 제거합니다.
- 기본 대기 시간은 호출당 300초입니다. 필요하면 `--timeout 600`으로 늘립니다. 인증 실패는 해당 CLI에서 먼저 로그인하고 다시 실행합니다.
- 출력에 사용량 통계·JSON 이벤트가 섞이면 CLI를 본문만 출력하는 모드로 설정합니다. 오류 원인은 `stderr.txt`에서 확인합니다.
- CLI는 별도 작업 폴더에서 실행하고 원문을 입력에 포함합니다. 파일 저장은 Python이 담당합니다. 모델에 도구 실행을 요청하지 않으며 각 CLI의 권한 설정은 유지합니다. 이것이 모든 CLI의 파일 접근을 OS 수준에서 차단한다는 뜻은 아닙니다.

프롬프트의 의미와 인용의 정확성은 자동 검증하지 않습니다. 본 패키지의 검증은 모형 CLI로 인자 전달·파일 보존·오류 처리를 확인한 것이며, 각 유료 모델의 실제 응답 품질이나 Antigravity 동작을 검증한 것은 아닙니다.
