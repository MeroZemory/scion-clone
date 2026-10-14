# Scion 글 그림 구조 해석

[원문](https://www.anthropic.com/engineering/redesigning-source-control)의 그림 6장을 해석한 노트입니다. 각 그림은 `svg/`에 다시 그렸습니다.
설계에 직접 쓰이는 그림은 02·03·04(구조도)이고, 01·05·06(차트)은 규모와 목표 수치를 잡는 근거로 씁니다.

| # | 그림 | 종류 | SVG 재구성 방식 |
|---|------|------|-----------------|
| 01 | 일별 merge 수 | 누적 막대 + 7일 평균선 | 픽셀에서 막대 높이를 읽어 복원한 근사 데이터(`data/01-*.csv`). Sep 9 = 30,401 라벨로 보정 |
| 02 | git 체크아웃 확장 구성 (Scion 이전) | 구조도 | 원본 좌표계(2000×645)에 손으로 다시 그림 |
| 03 | Scion changeset 구조 | 데이터 모델도 | 원본 좌표계(2000×1560)에 손으로 다시 그림 |
| 04 | Scion 체크아웃 아키텍처 | 구조도 | 원본 좌표계(2000×895)에 손으로 다시 그림 |
| 05 | Scion/Antique 코드베이스 주별 변경 수 | 누적 막대 | 픽셀 복원 근사 데이터(`data/05-*.csv`). 합계 12,066으로 라벨 12,257보다 약 1.6% 적음 |
| 06 | 일상 명령 git vs scn 성능 | 그룹 가로 막대 | 그림에 적힌 라벨 값을 그대로 사용(정확값) |

---

## 02. git 체크아웃 확장 구성 (Scion 이전)

Scion이 해결하려던 문제를 보여 주는 "이전 구조"입니다.

```
Jobs ──▶ [Per cluster: Packfile cache ──▶ Mirror replicas ──▶ Mirror primaries] ──▶ Upstream
 ▲                                            │
 └── Node seed ◀── Blob storage(Seed snapshot) ◀┘
```

- **소비자(Jobs)**: CI jobs, Developer environments, Agent sandboxes, Research jobs.
- **클러스터마다 복제되는 계층**(점선 상자): Packfile cache → Mirror replicas → Mirror primaries. 그 위에 Upstream(권위 저장소)이 있습니다.
- **두 가지 데이터 경로**
  - 주황(데이터가 Jobs에 닿는 경로): Jobs → Packfile cache → Mirror replicas로 fetch.
  - 주황(seed 경로): Mirror replicas → Blob storage(seed snapshot) → Node seed → Jobs. 새 노드는 스냅샷으로 시작합니다.
  - 회색(상류 동기화): replicas → primaries → Upstream.
- **문제점(본문)**: 미러가 수백 대로 늘었고, 미러의 디스크·메모리 한계를 넘으면 더 확장할 수 없습니다. seed는 refresh 사이에 main tip과 점점 멀어집니다. partial clone에서 diff/blame을 유지하기도 어렵습니다.
- **설계 시사점**: 저장소 전체를 "완전히 materialize한 사본"을 복제하는 방식은 확장되지 않습니다. 04에서 이 구조를 "불변 객체 단위의 계층형 캐시"로 바꿉니다.

## 03. Scion changeset 구조 (데이터 모델)

저장소가 두 계층으로 나뉩니다.

| 계층 | 저장 위치 | 내용 | 성질 |
|------|-----------|------|------|
| 메타데이터 | Spanner | changeset 레코드, 부모 링크, (ref) | WAL 항목, 서버가 생성 |
| 파일 내용 | Cloud Storage | blob | 불변, 압축, 해시로 dedup (content-addressed) |

**Changeset 레코드 필드** (`id`는 해시로 보임, 예: `9f2c…7ab0`)

| 필드 | 예시 | 필수 여부 |
|------|------|-----------|
| `author` | `Claude <noreply@anthropic.com>` | 필수 |
| `author_date` | `2026-09-15T01:25:09+00:00` | 필수 |
| `committer` | `Scion <noreply+scion@anthropic.com>` | Optional |
| `committer_date` | `2026-09-15T01:31:40+00:00` | Optional |
| `message` | `scion-cache: serve blobs from the memory tier` | 필수 |
| `parents` | `d41c…88e2` (changeset id 목록) | 필수 |
| `signature` | — | Optional |
| `file_changes` | 경로 → (blob 해시, 모드) 목록 | 필수 |

`file_changes` 항목 예시:

| path | blob | 종류 |
|------|------|------|
| `docs/guide.md` | `3e1f…a2c4` | Regular file |
| `src/legacy.rs` | (없음) | Deleted |
| `tools/build.sh` | `9b07…5d18` | Executable |

**git과의 핵심 차이**
- git commit은 **tree 포인터**를 저장합니다. Scion changeset은 **첫 번째 부모 대비 변경된 파일 목록**과 blob 포인터만 저장합니다(델타 기반).
- tree(`Root tree 5c0e…d1a9 → Tree src/ 77f0…e9b4 → app.rs → blob c5d2…0e77`)는 점선 상자로 표시되어 있습니다. **서버가 파생(derive)할 뿐 changeset에는 저장하지 않는다**는 뜻입니다.
- 따라서 changeset 생성 비용은 저장소 크기가 아니라 변경 크기에 비례합니다. packfile, 잠금, 서버 간 조정, ref 이동이 없습니다.
- ref는 changeset 생성과 분리되어 있습니다. ref 이동은 Spanner 단일 행 CAS(compare-and-swap)입니다.

**파생 데이터(derived data) 메커니즘 (본문)**
- tree, blame, path history, 커밋 그래프 skip list, copy detection 인덱스, path 검색 인덱스 등이 해당합니다.
- 모두 하나의 일반 메커니즘을 씁니다. `value(changeset) = f(changeset, value(parents))` 형태의 **재귀 정의**입니다.
- 타입별로 eager 계산과 지연 계산을 고를 수 있습니다. 클라이언트는 내부 구조를 보지 않으므로 서버에서 자유롭게 바꿀 수 있습니다.

## 04. Scion 체크아웃 아키텍처

```
                     control plane (회색)
Clients ─────────────────────────────────────────▶ scion-server ──▶ Spanner (Changesets, branches, trees)
  ├ Antique                                             ▲    └────▶ Cloud Storage (File contents)
  ├ Developer machines ──(object plane: trees/blobs)──▶ scion-cache (Regional) ──Misses──┘
  └ CI and cluster jobs ──▶ scion-daemon (Per node) ──Misses──▶ scion-cache
                                 ▲
                     Periodic snapshot ── Seeds new nodes (점선)
```

**두 개의 평면**

| 평면 | 표시 | 요청 내용 | 대상 |
|------|------|-----------|------|
| Control plane | 회색 | 브랜치, 히스토리, diff, upload/commit/land | 모든 클라이언트 → `scion-server` 직접 |
| Object plane | 주황 | tree와 파일 내용(불변 객체) | 계층형 캐시를 거쳐 전달 |

**Object plane 계층** (파란 상자 = Scion 서비스)

| 계층 | 범위 | 역할 |
|------|------|------|
| `scion-daemon` | 노드당 1개 | 노드 전체의 객체 저장소. 클라이언트(`scn`)는 소켓으로 접속. 주기 스냅샷으로 시작 |
| `scion-cache` | 리전 | 메모리에서 daemon 디스크 포맷 그대로 스트리밍(델타 압축·missing 계산 없음) |
| `scion-server` | 권위(authoritative) | miss를 받으면 Spanner/Cloud Storage에서 읽음. 파생 데이터를 즉석 계산해 기록 |

- **흐름**: Developer machines는 `scion-cache`에 바로 접속합니다. CI/클러스터 작업은 `scion-daemon` → (miss) `scion-cache` → (miss) `scion-server` 순으로 내려갑니다.
- **동일 RPC**: 세 계층 모두 같은 객체 프로토콜 RPC에 응답합니다. 그래서 클라이언트는 캐시 토폴로지를 몰라도 됩니다. 다만 장애 도메인을 격리하기 위해 계층 순서를 강제합니다(리전 캐시 장애가 서버로 몰려 전체가 죽는 상황 방지).
- **협상 방식(git과 반대)**: 클라이언트는 "가진 것"을 알리지 않습니다. 루트 tree부터 시작해 로컬에 없는 tree를 재귀적으로 요청하고, 그다음 blob을 요청합니다. 모든 요청이 불변 객체 하나를 가리키므로 어느 캐시든 응답할 수 있고, 중간에 끊겨도 이어받을 수 있습니다. sparse/virtual checkout은 원하지 않는 tree를 요청하지 않는 것으로 자연스럽게 구현됩니다.
- **수치(본문)**: 계층별 캐시 hit rate 99% 이상. git 미러 인프라 대비 CPU·메모리 200분의 1. 체크아웃은 분 단위에서 초 단위로 빨라졌고, CI CPU 용량은 25% 절감됐습니다.

## 01·05. 규모 차트

- **01 일별 merge 수**: 1월 약 700건/일에서 9월 9일 30,401건/일로 늘었습니다. 6월부터 Pull request(파랑)가 Antique change request(주황)로 바뀌며 마이그레이션 시점이 보입니다. 7월 말에는 "Quiet week" 급감이 있습니다. 7일 평균선은 복원 데이터로 다시 계산했습니다(빠진 날은 0으로 처리).
- **05 주별 Scion/Antique 코드 변경 수**: 1월 말 시작, 9월 둘째 주 약 1,560건/주, 누적 12,257건. 5월 중순부터 자기 자신(Antique)으로 리뷰하기 시작했습니다(dogfooding 전환).
- 두 CSV는 **근사값**입니다. 막대의 둥근 모서리 때문에 작은 막대는 조금 낮게 읽히는 경향이 있습니다.

## 06. git vs scn 명령 성능 (중앙값)

| 환경 | 명령 | git | scn | 배수 |
|------|------|-----|-----|------|
| 개발자 | Pull latest | 87 s | 3.5 s | ×25 |
| 개발자 | Checkout | 15 s | 1.1 s | ×14 |
| 개발자 | Rebase | 13 s | 2.7 s | ×4.8 |
| 개발자 | Status | 3.9 s | 19 ms | ×207 |
| 개발자 | Commit | 1.4 s | 1.1 s | ×1.3 |
| 개발자 | Diff | 407 ms | 67 ms | ×6.1 |
| 에이전트 | New worktree | 7.1 min | 5.1 s | ×84 |
| 에이전트 | Pull latest | 3.0 min | 9.0 s | ×20 |
| 에이전트 | Commit | 18 s | 761 ms | ×24 |
| 에이전트 | Status | 4.3 s | <0.2 s | ×20+ |
| 에이전트 | change request당 총 소스 관리 시간 | 34 min | 3.7 min | ×9.2 (≈11,000 agent hours/일) |
| CI/컴퓨트 | 컴퓨트 작업 시작 시 checkout | 175 s | 22 s | ×8.0 (≈85,000 machine hours/일) |
| CI/컴퓨트 | CI 작업 내 checkout | 31 s | 3.5 s | ×8.8 (≈195,000 machine hours/일) |

- Status가 ×207인 것은 클라이언트가 파일시스템 변경을 감시하기 때문으로 보입니다(본문: "monitors for filesystem changes").
- Commit은 서버에서 일어나므로 개발자 환경에서는 차이가 작습니다(×1.3). 에이전트 환경에서는 ×24로 큽니다.

---

## 우리 Scion 설계로 가져갈 구조 요약

1. **저장소 분리**: 메타데이터(changeset WAL, ref) 저장소와 content-addressed blob 저장소를 나눕니다.
2. **델타 changeset**: 첫 번째 부모 대비 `file_changes`만 저장하고, tree는 저장하지 않고 파생합니다.
3. **파생 데이터 프레임워크**: 부모 값으로 재귀 계산하는 일반 메커니즘을 두고, 타입별로 eager/lazy를 선택합니다.
4. **두 평면**: control plane RPC(히스토리·diff·commit·land)와 object plane RPC(tree/blob 단건 조회)를 나눕니다.
5. **계층형 캐시**: daemon(노드) → cache(리전) → server(권위). 세 계층이 같은 객체 RPC를 쓰고, 계층 순서를 강제합니다.
6. **want-only 협상**: 루트 tree부터 필요한 객체만 재귀 요청하므로 sparse/virtual checkout이 기본이 됩니다.
7. **ref 최소화**: ref 이동은 단일 행 CAS로 하고, changeset 생성 경로와 분리합니다.
