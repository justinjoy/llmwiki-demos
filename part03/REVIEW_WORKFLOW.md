# 반려 → 수정 → 재검토

`review.csv`는 **특정 버전의 후보에 대한 판정 입력**입니다. 후보 내용을 수정하는 파일은 아닙니다. `review_workflow.py`로 내용을 수정하면 새 버전이 생기고 상태가 `pending`으로 돌아갑니다. 이전 반려와 수정 전 내용은 그대로 보존됩니다.

```text
후보 r1(pending) → 반려(rejected)
                       ↓ revise: 사람이 내용 수정
후보 r2(pending) → 재검토 → approved / rejected / held
```

내용은 같지만 보류 사유가 해소되었거나 판정을 다시 검토하려면 `reopen`을 사용합니다. 이 경우에도 새 버전을 만들어 이전 검토 CSV가 재사용되지 않게 합니다. 승인된 후보를 고쳐도 같은 절차를 거칩니다.

## 먼저 CSV 편집부터 연습하기

```sh
python3 review_walkthrough.py --interactive
```

화면에 표시된 실습 폴더의 `review.csv`를 열어 판정·이유·검토자를 작성하고 저장한 뒤 Enter를 누릅니다. 첫 단계는 오류를 넣은 F03 r2 반려, 두 번째 단계는 교정된 F03 r3와 나머지 후보의 재검토입니다. 각 단계는 실제 CSV 가져오기를 실행하고 저장된 판정·이력을 보여 줍니다. 편집 오류가 있으면 같은 파일을 고쳐 다시 시도할 수 있습니다. 편집 전후 CSV 사본도 실습 폴더에 남습니다.

원래 후보로 실습할 때는 아래 명령을 사용합니다. CSV를 저장한 뒤 `import-review`까지 실행해야 DB와 이력에 판정이 반영됩니다.

## 1. 현재 후보와 버전 확인

`~/git/llmwiki-demos/part03`에서 실행합니다. 배포본은 최초 후보를 모두 `pending`으로 등록해 둔 상태입니다. 저장소가 없는 새 실습 폴더에서는 `init`으로 시작합니다. 이미 초기화된 저장소에는 영향을 주지 않습니다.

```sh
python3 review_workflow.py init
python3 review_workflow.py list
python3 review_workflow.py show F03
```

출력에서 버전, 판정, 수정자, 변경 이유, 원문 인용을 확인합니다. `F03` r1의 예시는 `pay → ledger`입니다.

## 2. 판정 기록

다음 둘 중 한 방식을 선택합니다. 명령의 검토자·이유는 본인이 실제 확인한 값으로 입력하세요.

**CSV 방식:** `review.csv`의 ID·revision·content_sha256은 그대로 두고 판정·이유·검토자를 작성합니다. 일부만 검토했으면 나머지는 `pending`과 빈 이유·검토자로 남깁니다.

```sh
python3 review_workflow.py import-review
```

**후보별 명령:** 현재 `list`에서 확인한 버전을 지정합니다.

```sh
python3 review_workflow.py decide F03 --revision 1 --status rejected --reviewer "본인 이름" --reason "원문 문서·절 및 실제 반려 이유"
```

이 명령은 사용법입니다. 배포된 F03이 잘못됐다고 판정한 예시가 아닙니다. 검토 결과에 맞는 `approved`, `held`, `rejected`를 사용하세요. 이미 끝난 판정은 같은 버전에서 덮어쓸 수 없습니다. `reopen` 또는 `revise`가 필요합니다.

## 3. 반려된 후보 수정

현재 내용을 별도 편집 파일로 받습니다.

```sh
python3 review_workflow.py show F03 --output corrected-F03.json
```

`corrected-F03.json`을 편집기로 열어 `subject`, `object`, `scope`, 원문 위치·인용 등 잘못된 값을 고칩니다. 후보 ID는 유지하고 원문 인용은 해당 절에 실제 존재하는 문장을 사용합니다. 원본 `assertions.jsonl`이나 `approved.jsonl`을 직접 고치지 않습니다.

```sh
python3 review_workflow.py revise F03 --revision 1 --file corrected-F03.json --actor "수정자 이름" --reason "무엇을 왜 수정했는지"
```

- r1의 내용·반려·검토자는 남습니다.
- 변경 전후 필드, 수정자, 수정 이유, UTC 시각이 기록됩니다.
- 새 r2는 `pending`입니다. 입력 JSON에 승인 상태가 있더라도 승인을 이어받지 않습니다.
- 다른 사람이 먼저 수정해 버전이 달라졌다면 명령을 거부합니다.
- 현재 승인 파일은 즉시 무효화되고 비워집니다. 기존 파일은 `.review/backups/`에 보관합니다.

내용 변경 없이 재검토하는 경우:

```sh
python3 review_workflow.py reopen F03 --revision 1 --actor "요청자 이름" --reason "보류 사유가 해소되어 다시 검토"
```

## 4. 최신 버전을 재검토

```sh
python3 review_workflow.py show F03
python3 review_workflow.py decide F03 --revision 2 --status approved --reviewer "재검토자 이름" --reason "원문 문서·절과 수정된 방향·범위를 확인"
python3 review_workflow.py history F03
```

`review.csv`에 새 버전의 판정을 작성하고 `import-review`를 실행해도 됩니다. 수정 전 CSV를 가져오면 버전/해시 불일치로 거부합니다. 판정을 기록하는 명령은 현재 CSV를 다시 작성하므로, CSV에서 편집 중인 다른 판정은 먼저 `import-review`로 저장하세요. 덮어쓴 이전 작업 CSV는 백업됩니다.

## 5. 모두 검토한 뒤 내보내기

```sh
python3 export_review.py --overwrite
python3 validate_assertions.py approved.jsonl --status approved
```

CSV의 판정을 먼저 이력에 기록한 다음 전체 후보에 `pending`이 없는지 확인합니다. 일부 미검토가 있으면 완료한 판정은 저장되지만 승인 파일은 게시되지 않습니다.

| 산출물 | 역할 |
| --- | --- |
| `approved.jsonl` | 최신 버전에서 승인된 직접 관계, 검토자·이유·후보 버전·내용 해시 |
| `approved.meta.json` | 현재 후보 버전과 승인 파일 해시, 유효/무효 상태 |
| `rejected.json`, `held.json` | 최신 버전의 반려·보류 상태 |
| `review_history.json` | 전체 후보의 모든 수정 버전과 판정, 필드별 변경 전후 |
| `.review/state.sqlite3` | 검토 이력의 기준 저장소. 기존 버전·판정 행의 수정/삭제 차단 |
| `.review/backups/` | 교체 전 CSV·승인 파일. Git에는 제외 |

상태 DB와 JSON 이력은 코드와 함께 버전 관리합니다. DB는 검토 명령으로 변경하고 JSON은 읽기용 이력 사본으로 사용하세요. 이는 서명된 승인 시스템이나 사용자 인증 기능이 아닙니다. 검토자는 명령·CSV에 입력한 식별자이며 실제 검토 여부는 사람이 책임집니다.

```sh
cd ../part04
python3 run_lesson4.py --assertions ../part03/approved.jsonl
```

4교시는 버전 관리된 승인 파일의 상태·해시·현재 후보 버전을 확인합니다. 수정으로 무효화된 파일이나 검토 DB 없이 복사된 관리 파일은 거부합니다. 파일 하나만 복사하는 대신 part03 검토 자료를 함께 유지하세요. 실행 결과는 그 시점의 입력 스냅샷이므로 나중에 후보가 바뀌면 4교시도 다시 실행해야 합니다.

## LLM 재추출과 외부 수정

`run_lesson3.py --task extract`는 유효한 재추출 결과를 저장한 뒤 검토 저장소와 비교합니다. 변경된 후보만 새 `pending` 버전으로 등록합니다. 변경 없는 재추출은 사람이 수정한 최신 후보를 덮어쓰지 않습니다.

추출 파일을 직접 교체했다면 다음 명령으로 명시적으로 등록합니다. 등록 전에는 이전 승인 파일 사용이 차단됩니다.

```sh
python3 review_workflow.py sync --actor "작업자 이름" --reason "새 추출 결과 등록"
```

기존 ID가 빠진 결과는 거부합니다. 과거 후보를 지우지 말고 원본을 복원한 뒤 반려·보류로 처리하세요. 기존 4열 검토 CSV는 후보 버전을 증명할 수 없으므로 새 검토 CSV에서 다시 확인해야 합니다. 초기화 이전 CSV도 백업합니다.

## E 오류 예문을 수정하려면

E01~E06의 원래 형태는 `id/claim`만 있는 오류 검토 예문이므로 직접 승인할 수 없습니다. `--kind assertion`을 명시하고 **동일한 ID를 가진 완전한 사실 레코드**로 수정하면 새 버전부터 원문 검증·재검토 후 승인할 수 있습니다.

예를 들어 E01을 구조화하려면 수정 JSON에 `assertion_id: "E01"`, 올바른 Service 간 관계, 문서·절·인용 등 필수 필드를 작성하고 다음처럼 등록합니다.

```sh
python3 review_workflow.py revise E01 --revision 1 --kind assertion --file corrected-E01.json --actor "수정자 이름" --reason "반대 방향 주장을 원문에 근거한 구조화 사실로 교정"
```

같은 올바른 사실이 이미 F03에 있으면 중복 후보를 추가할 필요 없이 E01을 반려하고 F03을 참조하면 됩니다. 담당 팀·별칭 등 직접 호출 관계가 아닌 항목은 `entities.json`·`aliases.json`의 검토 대상이며 이 승인 파일로 내보내지 않습니다.

## 격리된 시연과 검사

```sh
python3 review_walkthrough.py
python3 -m unittest discover -s tests -v
```

시연은 별도 `runs/` 작업 공간에서 오류 후보 → 반려 → 수정 → 재승인을 실행합니다. 학습자의 현재 검토 상태를 바꾸지 않으며 검토자는 교육용 예시로 표시합니다.
