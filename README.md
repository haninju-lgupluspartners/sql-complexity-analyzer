# SQL Complexity Analyzer

SQL 쿼리의 복잡도를 분석하고 점수화하는 도구 모음입니다.

## 모듈 구성

| 모듈 | 설명 | 상태 |
|------|------|------|
| `structural-complexity` | SQL 자체의 구조적 복잡도 분석 | ✅ 완료 |
| `conversion-complexity` | DB 변환 복잡도 분석 | 🚧 TBD |

---

## Structural Complexity (구조적 복잡도 분석)

SQL 쿼리 자체의 구조적 복잡성을 측정하는 스코어링 엔진입니다.

> 구조적 복잡도는 SQL 문법/구조의 복잡성만을 측정합니다. 성능 영향(Full Scan, 인덱스 미사용 등)은 별도 분석 영역입니다.

### 지원 DBMS

| 약어 | DBMS |
|------|------|
| ORA | Oracle |
| MY | MySQL |
| MDB | MariaDB |
| PG | PostgreSQL |
| SS | SQL Server |
| ALT | Altibase |
| DB2 | IBM DB2 |

### 복잡도 측정 카테고리

| 카테고리 | 비중 | 측정 항목 |
|----------|------|----------|
| 구조적 복잡성 | 30% | JOIN 수, 서브쿼리 깊이, CTE, 집합 연산 (UNION/INTERSECT) |
| 절 복잡성 | 15% | SELECT 컬럼 수, WHERE 조건 수, GROUP BY/HAVING/ORDER BY |
| 함수/표현식 | 20% | 집계 함수, 윈도우 함수, CASE 표현식 |
| 쿼리 메트릭 | 10% | 쿼리 길이, 참조 테이블 수 |
| DBMS 특화 | 25% | 각 DB별 고유 문법 |

### 복잡도 등급

0-10 정규화 점수 기준:

| 점수 | 등급 | 설명 |
|------|------|------|
| 0-2 | 매우 단순 | 단순 CRUD |
| 2-4 | 단순 | 기본 JOIN/조건 |
| 4-6 | 보통 | 복합 JOIN, 서브쿼리 |
| 6-8 | 복잡 | 다중 서브쿼리, 윈도우 함수 |
| 8-10 | 매우 복잡 | 계층 쿼리, 동적 SQL |

### 설치

```bash
pip install pyyaml
```

### 사용법

```bash
cd structural-complexity

# 기본 사용
python3 structural_complexity_scoring_engine.py \
    --source-db ORA \
    --input queries.json \
    --output result

# 여러 파일 분석
python3 structural_complexity_scoring_engine.py \
    --source-db MDB \
    --input file1.json file2.json \
    --output analysis_result
```

### CLI 옵션

| 옵션 | 필수 | 설명 |
|------|------|------|
| `--source-db`, `-s` | O | Source DBMS (ORA, MY, MDB, PG, SS, ALT, DB2) |
| `--input`, `-i` | O | 입력 JSON 파일 (복수 가능) |
| `--output`, `-o` | X | 출력 파일명 (확장자 제외) |
| `--rules`, `-r` | X | 룰 YAML 파일 경로 |
| `--format`, `-f` | X | 출력 형식 (json, md, csv), 복수 지정 가능, 기본값: 전체 |
| `--verbose`, `-v` | X | 상세 출력 |

### 입력 JSON 형식

```json
{
  "files": [
    {
      "file_name": "UserMapper.xml",
      "file_path": "/src/main/resources/mapper/UserMapper.xml",
      "queries": [
        {
          "name": "selectUserById",
          "type": "SELECT",
          "sql": "SELECT * FROM users WHERE id = #{id}"
        }
      ]
    }
  ]
}
```

### 출력 형식

기본 실행 시 json, md, csv 3가지 형식 모두 생성됩니다.

| 형식 | 파일 | 설명 |
|------|------|------|
| JSON | `{output}.json` | 전체 분석 결과 상세 데이터 |
| Markdown | `{output}.md` | 리포트 형식의 분석 결과 |
| CSV | `{output}.csv` | 쿼리별 상세 데이터 (스프레드시트용) |

특정 형식만 생성하려면 `--format` 옵션 사용:
```bash
--format json md   # json과 md만 생성
--format csv       # csv만 생성
```

### 측정 항목 상세

#### 1. 구조적 복잡성

| 항목 | 설명 |
|------|------|
| JOIN | JOIN 개수 (0/1/2-3/4-5/6+) |
| 서브쿼리 | 서브쿼리 깊이 (0/1/2/3+), 개수, 상관 서브쿼리 |
| CTE | WITH 절 개수 (1/2-3/4+) |
| 집합 연산 | UNION, UNION ALL, INTERSECT |

#### 2. 절 복잡성

| 항목 | 설명 |
|------|------|
| SELECT | 컬럼 수 (1-5/6-10/11-20/21+), DISTINCT |
| WHERE | 조건 수 (AND/OR 기준), IN 목록 |
| GROUP BY | 사용 여부, 컬럼 수 |
| HAVING | 사용 여부 |
| ORDER BY | 사용 여부, 컬럼 수 |

> WHERE 절의 개별 비교 연산자(=, >=, <=, BETWEEN, LIKE 등)는 구조적 복잡도에 영향을 주지 않으므로 별도 카운팅하지 않습니다.

#### 3. 함수/표현식

| 항목 | 설명 |
|------|------|
| 집계 함수 | COUNT, SUM, AVG, MIN, MAX |
| 윈도우 함수 | OVER, PARTITION BY, ROWS/RANGE BETWEEN |
| CASE | CASE 표현식, WHEN 절, 중첩 CASE |
| 공통 함수 | 문자열, 수학, NULL 처리, CAST |

#### 4. DBMS 특화 (예시)

**Oracle**
- `(+)` 조인, CONNECT BY/START WITH/PRIOR (계층 쿼리)
- ROWNUM, DECODE, NVL/NVL2, LISTAGG
- PIVOT/UNPIVOT, MODEL 절, Oracle 힌트

**MySQL/MariaDB**
- LIMIT/OFFSET, IFNULL, IF(), GROUP_CONCAT
- ON DUPLICATE KEY UPDATE, USE/FORCE/IGNORE INDEX

**PostgreSQL**
- RETURNING, LATERAL, ARRAY/ARRAY_AGG/UNNEST
- JSON 연산자, :: 캐스팅, WITH RECURSIVE

**SQL Server**
- TOP, CROSS/OUTER APPLY, ISNULL, IIF
- 테이블 힌트 (NOLOCK 등), MERGE, TRY...CATCH

### 파일 구조

```
structural-complexity/
├── structural_complexity_scoring_engine.py  # 메인 스코어링 엔진
├── structural-complexity-rules.yml          # 복잡도 측정 룰 정의
└── structure-checklist.md                   # 체크리스트 문서
```

### MyBatis 지원

MyBatis XML 파일의 동적 SQL 태그를 자동으로 전처리합니다:
- `<![CDATA[...]]>` 제거
- `<if>`, `<choose>`, `<when>`, `<foreach>`, `<where>`, `<set>`, `<trim>` 태그 제거
- `#{param}`, `${param}` 파라미터를 `?`로 치환

---

## Conversion Complexity (변환 복잡도 분석)

> 🚧 **TBD** - 추후 업데이트 예정
