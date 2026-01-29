# SQL 변환 복잡도 체크리스트 (Conversion Checklist)

## 개요

이 체크리스트는 **Source DB → Target DB 변환 난이도**를 측정합니다. 접근 방식 2(Source DB 기반 검출 로직 분리)를 적용하여 각 패턴이 적용되는 Source DB를 명확히 지정합니다.

### 핵심 원칙

1. **applicable_db 명시**: 각 패턴이 적용되는 Source DB를 명확히 지정
2. **동등 기능 그룹화**: 같은 기능을 수행하지만 DBMS마다 다른 문법을 사용하는 항목들을 그룹으로 관리
3. **변환 매트릭스 제공**: Source DB → Target DB 변환 가이드 포함
4. **오탐 방지**: Source DB에 해당하지 않는 패턴은 검출하지 않음

### 지원 DBMS 목록

| 약어 | DBMS |
|-----|------|
| ORA | Oracle |
| MY | MySQL |
| MDB | MariaDB |
| PG | PostgreSQL |
| SS | SQL Server |
| ALT | Altibase |
| DB2 | IBM DB2 |

### 자동변환 등급

| 등급 | 코드 | 설명 |
|-----|------|------|
| 자동 | A | 단순 치환으로 자동 변환 가능 |
| 부분 | P | 부분 자동 변환 (검증 필요) |
| 수동 | M | 수동 변환 필요 |

---


## # 1. DML Syntax

### 1.1 기본 DML

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dml_simple_select_low | 단순 SELECT (조건 3개 이하) | 5 | ast | WHERE 조건 수 ≤ 3 | ALL | A |
| dml_simple_select_high | 단순 SELECT (조건 4개 이상) | 10 | ast | WHERE 조건 수 ≥ 4 | ALL | A |
| dml_truncate | TRUNCATE TABLE | 5 | regex | `TRUNCATE\s+TABLE` | ALL | A |
| dml_insert_select | INSERT INTO ... SELECT | 5 | regex | `INSERT\s+INTO\s+\w+.*SELECT` | ALL | A |

### 1.2 다중 테이블 DML (그룹: multi_table_dml)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dml_multi_delete_mysql | 다중 테이블 DELETE | 15 | regex | `DELETE\s+\w+\s*,\s*\w+\s+FROM` | MY, MDB | P |
| dml_multi_delete_using | DELETE ... USING | 15 | regex | `DELETE\s+FROM\s+\w+\s+USING` | MY, MDB, PG | P |
| dml_multi_update | 다중 테이블 UPDATE | 15 | regex | `UPDATE\s+\w+\s*,\s*\w+\s+SET` | MY, MDB | P |

**변환 매트릭스:**
- MY/MDB → PG: 서브쿼리 또는 CTE로 변환
- MY/MDB → ORA: MERGE 또는 서브쿼리로 변환

### 1.3 UPSERT 구문 (그룹: upsert_syntax)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dml_insert_ignore | INSERT IGNORE | 10 | regex | `INSERT\s+IGNORE\s+INTO` | MY, MDB | P |
| dml_replace_into | REPLACE INTO | 10 | regex | `REPLACE\s+INTO` | MY, MDB | P |
| dml_merge_into_oracle | MERGE INTO (Oracle) | 15 | regex | `MERGE\s+INTO` | ORA | P |
| dml_merge_sqlserver | MERGE (SQL Server) | 15 | regex | `MERGE\s+\w+\s+(AS\s+)?\w+\s+USING` | SS | P |
| dml_on_duplicate | ON DUPLICATE KEY UPDATE | 10 | regex | `ON\s+DUPLICATE\s+KEY\s+UPDATE` | MY, MDB | P |
| dml_on_conflict | INSERT ... ON CONFLICT | 10 | regex | `ON\s+CONFLICT\s*\(` | PG | P |
| dml_upsert_altibase | UPSERT | 10 | keyword | `UPSERT` | ALT | P |

**변환 매트릭스:**
- ORA MERGE → PG: INSERT ON CONFLICT 또는 CTE
- MY ON DUPLICATE → PG: INSERT ON CONFLICT
- MY ON DUPLICATE → ORA: MERGE INTO

### 1.4 RETURNING 절 (그룹: returning_clause)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dml_returning_pg | RETURNING (PostgreSQL) | 15 | regex | `(INSERT\|UPDATE\|DELETE).*RETURNING` | PG | M |
| dml_returning_oracle | RETURNING INTO (Oracle) | 15 | regex | `RETURNING.*INTO` | ORA | M |
| dml_output_sqlserver | OUTPUT (SQL Server) | 15 | regex | `OUTPUT\s+(INSERTED\|DELETED)\.` | SS | M |

### 1.5 벌크 작업

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dml_bulk_insert | BULK INSERT | 15 | regex | `BULK\s+INSERT` | SS | M |
| dml_copy | COPY | 15 | regex | `COPY\s+\w+\s+(FROM\|TO)` | PG | M |
| dml_load_data | LOAD DATA | 15 | regex | `LOAD\s+DATA\s+(LOCAL\s+)?INFILE` | MY, MDB | M |
| dml_sqlldr | SQL*Loader 참조 | 15 | regex | `@\w+\.ctl` | ORA | M |

### 1.6 SELECT INTO

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dml_select_into_table | SELECT INTO (테이블 생성) | 10 | regex | `SELECT.*INTO\s+\w+\s+FROM` | SS | P |
| dml_select_into_var | SELECT INTO (변수 할당) | 10 | regex | `SELECT.*INTO\s+@\w+` | MY, MDB | P |
| dml_select_into_plsql | SELECT INTO (PL/SQL) | 10 | regex | `SELECT.*INTO\s+\w+\s*;` | ORA, PG | P |

---


## # 2. DDL Syntax

### 2.1 테이블/뷰 관리

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| ddl_create_table | CREATE TABLE | 5 | regex | `CREATE\s+TABLE` | ALL | A |
| ddl_create_table_as | CREATE TABLE AS SELECT | 10 | regex | `CREATE\s+TABLE\s+\w+\s+AS\s+SELECT` | ALL | P |
| ddl_alter_table | ALTER TABLE | 10 | regex | `ALTER\s+TABLE` | ALL | P |
| ddl_drop_table | DROP TABLE | 5 | regex | `DROP\s+TABLE` | ALL | A |
| ddl_drop_if_exists | DROP IF EXISTS | 5 | regex | `DROP\s+(TABLE\|VIEW\|INDEX)\s+IF\s+EXISTS` | MY, MDB, PG | P |
| ddl_create_view | CREATE VIEW | 10 | regex | `CREATE\s+(OR\s+REPLACE\s+)?VIEW` | ALL | P |
| ddl_create_index | CREATE INDEX | 5 | regex | `CREATE\s+(UNIQUE\s+)?INDEX` | ALL | A |

### 2.2 파티션 관리

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| ddl_partition_by | PARTITION BY | 15 | regex | `PARTITION\s+BY\s+(RANGE\|LIST\|HASH)` | ALL | P |
| ddl_add_partition | ADD PARTITION | 15 | regex | `ADD\s+PARTITION` | ALL | P |
| ddl_drop_partition | DROP PARTITION | 15 | regex | `DROP\s+PARTITION` | ALL | P |
| ddl_partition_oracle | Oracle 파티션 구문 | 15 | regex | `PARTITION\s+\w+\s+VALUES\s+LESS\s+THAN` | ORA | P |

### 2.3 프로시저/함수/트리거

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| ddl_create_procedure | CREATE PROCEDURE | 20 | regex | `CREATE\s+(OR\s+REPLACE\s+)?PROCEDURE` | ALL | M |
| ddl_create_function | CREATE FUNCTION | 20 | regex | `CREATE\s+(OR\s+REPLACE\s+)?FUNCTION` | ALL | M |
| ddl_create_trigger | CREATE TRIGGER | 20 | regex | `CREATE\s+(OR\s+REPLACE\s+)?TRIGGER` | ALL | M |
| ddl_create_package | CREATE PACKAGE | 25 | regex | `CREATE\s+(OR\s+REPLACE\s+)?PACKAGE` | ORA | M |

### 2.4 시퀀스 (그룹: sequence_syntax)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| ddl_create_sequence | CREATE SEQUENCE | 15 | regex | `CREATE\s+SEQUENCE` | ORA, PG, SS, ALT | P |
| ddl_nextval_oracle | NEXTVAL (Oracle) | 15 | regex | `\w+\.NEXTVAL` | ORA | P |
| ddl_nextval_pg | nextval() (PostgreSQL) | 15 | regex | `nextval\s*\(\s*'` | PG | P |
| ddl_next_value_ss | NEXT VALUE FOR (SQL Server) | 15 | regex | `NEXT\s+VALUE\s+FOR` | SS | P |

**변환 매트릭스:**
- ORA seq.NEXTVAL → PG: nextval('seq')
- ORA seq.NEXTVAL → MY: 시퀀스 테이블 또는 AUTO_INCREMENT

### 2.5 세션/시스템 설정

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| ddl_alter_session | ALTER SESSION SET | 10 | regex | `ALTER\s+SESSION\s+SET` | ORA | P |
| ddl_set_session | SET (세션 변수) | 10 | regex | `SET\s+(SESSION\s+)?\w+\s*=` | MY, MDB, PG | P |
| ddl_set_sqlserver | SET (SQL Server) | 10 | regex | `SET\s+(NOCOUNT\|ANSI_NULLS\|QUOTED_IDENTIFIER)` | SS | P |

### 2.6 메타데이터 조회

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| ddl_info_schema | information_schema | 15 | regex | `FROM\s+information_schema\.` | MY, MDB, PG, SS | P |
| ddl_user_tables_oracle | USER_TABLES/ALL_TABLES | 15 | regex | `FROM\s+(USER\|ALL\|DBA)_(TABLES\|COLUMNS\|INDEXES)` | ORA | P |
| ddl_sys_tables_ss | sys.tables (SQL Server) | 15 | regex | `FROM\s+sys\.(tables\|columns\|indexes)` | SS | P |
| ddl_system_table_alt | SYSTEM_.* (Altibase) | 15 | regex | `FROM\s+SYSTEM_\w+` | ALT | P |

### 2.7 기타 DDL

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| ddl_explain | EXPLAIN | 5 | regex | `EXPLAIN\s+(ANALYZE\s+)?` | MY, MDB, PG | P |
| ddl_explain_plan | EXPLAIN PLAN FOR | 5 | regex | `EXPLAIN\s+PLAN\s+FOR` | ORA | P |
| ddl_comment_on | COMMENT ON | 5 | regex | `COMMENT\s+ON\s+(TABLE\|COLUMN)` | ORA, PG | P |

---


## # 3. 페이징/정렬 (그룹: pagination_syntax)

### 3.1 페이징 구문

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| page_limit_offset | LIMIT OFFSET | 5 | regex | `LIMIT\s+\d+(\s+OFFSET\s+\d+)?` | MY, MDB, PG | P |
| page_offset_fetch | OFFSET FETCH | 5 | regex | `OFFSET\s+\d+\s+ROWS\s+FETCH\s+(FIRST\|NEXT)` | SS, ORA | P |
| page_fetch_first | FETCH FIRST N ROWS | 10 | regex | `FETCH\s+(FIRST\|NEXT)\s+\d+\s+ROWS\s+ONLY` | ORA, DB2 | P |
| page_rownum | ROWNUM | 15 | regex | `ROWNUM\s*(<\|<=\|=\|>\|>=)` | ORA | M |
| page_rownum_where | WHERE ROWNUM | 15 | regex | `WHERE\s+ROWNUM` | ORA | M |
| page_rowid | ROWID | 15 | keyword | `ROWID` | ORA | M |
| page_top_n | TOP N | 10 | regex | `SELECT\s+TOP\s+\d+` | SS | P |
| page_top_percent | TOP PERCENT | 10 | regex | `SELECT\s+TOP\s+\d+\s+PERCENT` | SS | P |

**변환 매트릭스:**
- ORA ROWNUM → PG: ROW_NUMBER() OVER() 또는 LIMIT
- ORA ROWNUM → MY: LIMIT
- SS TOP → PG: LIMIT
- SS TOP → ORA: FETCH FIRST (12c+) 또는 ROWNUM

### 3.2 정렬 옵션

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| sort_nulls_first | NULLS FIRST | 10 | regex | `ORDER\s+BY.*NULLS\s+FIRST` | ORA, PG | P |
| sort_nulls_last | NULLS LAST | 10 | regex | `ORDER\s+BY.*NULLS\s+LAST` | ORA, PG | P |

**변환 매트릭스:**
- ORA/PG NULLS FIRST → MY: CASE WHEN col IS NULL THEN 0 ELSE 1 END, col
- ORA/PG NULLS FIRST → SS: CASE WHEN col IS NULL THEN 0 ELSE 1 END, col

---

## # 4. 고급 쿼리 구문

### 4.1 CTE (Common Table Expression)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| adv_cte | WITH 절 (CTE) | 10 | regex | `WITH\s+\w+\s+AS\s*\(` | ALL (MY 8.0+) | P |
| adv_cte_recursive | WITH RECURSIVE | 15 | regex | `WITH\s+RECURSIVE` | MY, MDB, PG | P |
| adv_cte_recursive_ora | 재귀 CTE (Oracle) | 15 | regex | `WITH\s+\w+.*CONNECT\s+BY` | ORA | P |

### 4.2 계층적 쿼리 (Oracle 전용)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| adv_connect_by | CONNECT BY | 25 | regex | `CONNECT\s+BY(\s+NOCYCLE)?` | ORA | M |
| adv_start_with | START WITH | 20 | regex | `START\s+WITH` | ORA | M |
| adv_prior | PRIOR | 15 | keyword | `PRIOR\s+\w+` | ORA | M |
| adv_sys_connect_path | SYS_CONNECT_BY_PATH | 20 | regex | `SYS_CONNECT_BY_PATH\s*\(` | ORA | M |
| adv_connect_by_root | CONNECT_BY_ROOT | 20 | regex | `CONNECT_BY_ROOT\s+\w+` | ORA | M |
| adv_level | LEVEL (계층) | 15 | keyword | `LEVEL` (CONNECT BY 컨텍스트) | ORA | M |

**변환 매트릭스:**
- ORA CONNECT BY → PG: WITH RECURSIVE
- ORA CONNECT BY → MY: WITH RECURSIVE (8.0+)

### 4.3 PIVOT/UNPIVOT

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| adv_pivot | PIVOT | 15 | regex | `PIVOT\s*\(` | ORA, SS | M |
| adv_unpivot | UNPIVOT | 15 | regex | `UNPIVOT\s*\(` | ORA, SS | M |

**변환 매트릭스:**
- ORA/SS PIVOT → PG: CASE WHEN + GROUP BY 또는 crosstab()
- ORA/SS PIVOT → MY: CASE WHEN + GROUP BY

### 4.4 Oracle 조인 문법

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| adv_plus_join | (+) 조인 | 10 | regex | `\w+\s*\(\+\)` | ORA | P |

**변환 매트릭스:**
- ORA (+) → ALL: LEFT/RIGHT OUTER JOIN

### 4.5 기타 고급 구문

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| adv_dual | DUAL 테이블 | 3 | regex | `FROM\s+DUAL` | ORA | A |
| adv_model | MODEL 절 | 25 | regex | `MODEL\s+(RETURN\|DIMENSION\|MEASURES)` | ORA | M |
| adv_flashback | FLASHBACK | 20 | regex | `AS\s+OF\s+(TIMESTAMP\|SCN)` | ORA | M |

---


## # 5. 함수 - 문자열

### 5.1 공통 문자열 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_concat_func | CONCAT() | 5 | regex | `CONCAT\s*\(` | ALL | A |
| str_replace | REPLACE() | 5 | regex | `REPLACE\s*\(` | ALL | A |
| str_trim | TRIM() | 5 | regex | `TRIM\s*\(` | ALL | A |
| str_ltrim | LTRIM() | 5 | regex | `LTRIM\s*\(` | ALL | A |
| str_rtrim | RTRIM() | 5 | regex | `RTRIM\s*\(` | ALL | A |
| str_upper | UPPER() | 5 | regex | `UPPER\s*\(` | ALL | A |
| str_lower | LOWER() | 5 | regex | `LOWER\s*\(` | ALL | A |
| str_lpad | LPAD() | 5 | regex | `LPAD\s*\(` | ALL | A |
| str_rpad | RPAD() | 5 | regex | `RPAD\s*\(` | ALL | A |
| str_ascii | ASCII() | 5 | regex | `ASCII\s*\(` | ALL | A |

### 5.2 SUBSTR/SUBSTRING (그룹: substring_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_substr | SUBSTR() | 3 | regex | `SUBSTR\s*\(` | ORA, MY, MDB, PG, ALT | A |
| str_substring | SUBSTRING() | 3 | regex | `SUBSTRING\s*\(` | MY, MDB, PG, SS | A |

**변환 매트릭스:**
- ORA SUBSTR → SS: SUBSTRING
- SS SUBSTRING → ORA: SUBSTR

### 5.3 문자열 위치 찾기 (그룹: string_position_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_instr | INSTR() | 5 | regex | `INSTR\s*\(` | ORA, MY, MDB | P |
| str_charindex | CHARINDEX() | 5 | regex | `CHARINDEX\s*\(` | SS | P |
| str_position | POSITION() | 5 | regex | `POSITION\s*\(` | PG | P |
| str_locate | LOCATE() | 5 | regex | `LOCATE\s*\(` | MY, MDB | P |

**변환 매트릭스:**
- ORA INSTR → SS: CHARINDEX (인자 순서 다름)
- ORA INSTR → PG: POSITION 또는 strpos()
- SS CHARINDEX → ORA: INSTR

### 5.4 문자열 길이 (그룹: string_length_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_length | LENGTH() | 5 | regex | `LENGTH\s*\(` | ORA, MY, MDB, PG, ALT | P |
| str_len | LEN() | 5 | regex | `LEN\s*\(` | SS | P |
| str_char_length | CHAR_LENGTH() | 5 | regex | `CHAR_LENGTH\s*\(` | MY, MDB, PG | P |
| str_datalength | DATALENGTH() | 5 | regex | `DATALENGTH\s*\(` | SS | P |

**변환 매트릭스:**
- ORA LENGTH → SS: LEN
- SS LEN → ORA: LENGTH

### 5.5 LEFT/RIGHT 함수 (그룹: left_right_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_left | LEFT() | 10 | regex | `LEFT\s*\(` | MY, MDB, SS, PG | P |
| str_right | RIGHT() | 10 | regex | `RIGHT\s*\(` | MY, MDB, SS, PG | P |

**변환 매트릭스:**
- MY/SS LEFT → ORA: SUBSTR(str, 1, n)
- MY/SS RIGHT → ORA: SUBSTR(str, -n)

### 5.6 특수 문자열 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_initcap | INITCAP() | 10 | regex | `INITCAP\s*\(` | ORA, PG | M |
| str_translate | TRANSLATE() | 10 | regex | `TRANSLATE\s*\(` | ORA, PG | M |
| str_reverse | REVERSE() | 5 | regex | `REVERSE\s*\(` | MY, MDB, SS | P |
| str_stuff | STUFF() | 10 | regex | `STUFF\s*\(` | SS | P |
| str_chr_oracle | CHR() | 5 | regex | `CHR\s*\(` | ORA, PG | A |
| str_char_mysql | CHAR() | 5 | regex | `CHAR\s*\(\d+` | MY, MDB, SS | A |

### 5.7 정규식 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_regexp_like | REGEXP_LIKE() | 10 | regex | `REGEXP_LIKE\s*\(` | ORA | P |
| str_regexp_replace | REGEXP_REPLACE() | 10 | regex | `REGEXP_REPLACE\s*\(` | ORA, PG, MY (8.0+) | P |
| str_regexp_substr | REGEXP_SUBSTR() | 10 | regex | `REGEXP_SUBSTR\s*\(` | ORA | P |
| str_regexp_instr | REGEXP_INSTR() | 10 | regex | `REGEXP_INSTR\s*\(` | ORA | P |
| str_regexp_mysql | REGEXP / RLIKE | 10 | regex | `(REGEXP\|RLIKE)\s+` | MY, MDB | P |
| str_regexp_pg | ~ 연산자 | 10 | regex | `~\s*'` | PG | P |

---


## # 6. 함수 - 날짜/시간

### 6.1 현재 날짜/시간 (그룹: current_datetime_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dt_now | NOW() | 3 | regex | `NOW\s*\(\s*\)` | MY, MDB, PG | A |
| dt_sysdate | SYSDATE | 3 | keyword | `SYSDATE` | ORA | A |
| dt_getdate | GETDATE() | 3 | regex | `GETDATE\s*\(\s*\)` | SS | A |
| dt_current_timestamp | CURRENT_TIMESTAMP | 5 | keyword | `CURRENT_TIMESTAMP` | ALL | A |
| dt_current_date | CURRENT_DATE | 5 | keyword | `CURRENT_DATE` | ALL (SS 제외) | A |
| dt_systimestamp | SYSTIMESTAMP | 5 | keyword | `SYSTIMESTAMP` | ORA | P |
| dt_sysdatetime | SYSDATETIME() | 5 | regex | `SYSDATETIME\s*\(\s*\)` | SS | P |

**변환 매트릭스:**
- ORA SYSDATE → MY: NOW()
- ORA SYSDATE → PG: CURRENT_TIMESTAMP 또는 NOW()
- ORA SYSDATE → SS: GETDATE()
- SS GETDATE → ORA: SYSDATE
- MY NOW → ORA: SYSDATE

### 6.2 날짜 포맷 변환 (그룹: date_format_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dt_to_char | TO_CHAR() | 10 | regex | `TO_CHAR\s*\(` | ORA, PG | P |
| dt_to_date | TO_DATE() | 10 | regex | `TO_DATE\s*\(` | ORA, PG | P |
| dt_to_timestamp | TO_TIMESTAMP() | 10 | regex | `TO_TIMESTAMP\s*\(` | ORA, PG | P |
| dt_to_number | TO_NUMBER() | 10 | regex | `TO_NUMBER\s*\(` | ORA | P |
| dt_date_format | DATE_FORMAT() | 10 | regex | `DATE_FORMAT\s*\(` | MY, MDB | P |
| dt_str_to_date | STR_TO_DATE() | 10 | regex | `STR_TO_DATE\s*\(` | MY, MDB | P |
| dt_format_ss | FORMAT() (날짜) | 10 | regex | `FORMAT\s*\(\s*\w+\s*,\s*'[^']*'` | SS | P |
| dt_convert_ss | CONVERT() (날짜) | 10 | regex | `CONVERT\s*\(\s*(VARCHAR\|DATETIME)` | SS | P |

**변환 매트릭스:**
- ORA TO_CHAR → MY: DATE_FORMAT (포맷 문자열 변환 필요)
- ORA TO_DATE → MY: STR_TO_DATE
- MY DATE_FORMAT → ORA: TO_CHAR

### 6.3 날짜 연산 (그룹: date_arithmetic_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dt_add_months | ADD_MONTHS() | 10 | regex | `ADD_MONTHS\s*\(` | ORA | P |
| dt_months_between | MONTHS_BETWEEN() | 10 | regex | `MONTHS_BETWEEN\s*\(` | ORA | P |
| dt_date_add | DATE_ADD() | 10 | regex | `DATE_ADD\s*\(` | MY, MDB | P |
| dt_date_sub | DATE_SUB() | 10 | regex | `DATE_SUB\s*\(` | MY, MDB | P |
| dt_dateadd | DATEADD() | 10 | regex | `DATEADD\s*\(` | SS | P |
| dt_datediff | DATEDIFF() | 10 | regex | `DATEDIFF\s*\(` | MY, MDB, SS | P |
| dt_interval | INTERVAL 연산 | 10 | regex | `INTERVAL\s+('?\d+'\s*)?(YEAR\|MONTH\|DAY\|HOUR\|MINUTE\|SECOND)` | ALL | P |

**변환 매트릭스:**
- ORA ADD_MONTHS → MY: DATE_ADD(date, INTERVAL n MONTH)
- ORA ADD_MONTHS → PG: date + INTERVAL 'n months'
- MY DATE_ADD → ORA: date + INTERVAL 또는 ADD_MONTHS

### 6.4 날짜 부분 추출 (그룹: date_part_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dt_extract | EXTRACT() | 5 | regex | `EXTRACT\s*\(\s*(YEAR\|MONTH\|DAY\|HOUR\|MINUTE\|SECOND)` | ALL | A |
| dt_year | YEAR() | 5 | regex | `YEAR\s*\(` | MY, MDB, SS | A |
| dt_month | MONTH() | 5 | regex | `MONTH\s*\(` | MY, MDB, SS | A |
| dt_day | DAY() | 5 | regex | `DAY\s*\(` | MY, MDB, SS | A |
| dt_datepart | DATEPART() | 10 | regex | `DATEPART\s*\(` | SS | P |
| dt_to_days | TO_DAYS() | 10 | regex | `TO_DAYS\s*\(` | MY, MDB | P |
| dt_from_days | FROM_DAYS() | 10 | regex | `FROM_DAYS\s*\(` | MY, MDB | P |

### 6.5 날짜 TRUNC (그룹: date_trunc_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dt_trunc_oracle | TRUNC() (날짜) | 10 | regex | `TRUNC\s*\(\s*\w+\s*,\s*'(YEAR\|MONTH\|DAY\|HH\|MI)'` | ORA | P |
| dt_date_trunc | DATE_TRUNC() | 10 | regex | `DATE_TRUNC\s*\(` | PG | P |

**변환 매트릭스:**
- ORA TRUNC(date, 'MM') → PG: DATE_TRUNC('month', date)
- PG DATE_TRUNC → ORA: TRUNC

---


## # 7. 함수 - 수학/집계

### 7.1 공통 집계 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| agg_count | COUNT() | 5 | regex | `COUNT\s*\(` | ALL | A |
| agg_sum | SUM() | 5 | regex | `SUM\s*\(` | ALL | A |
| agg_avg | AVG() | 5 | regex | `AVG\s*\(` | ALL | A |
| agg_min | MIN() | 5 | regex | `MIN\s*\(` | ALL | A |
| agg_max | MAX() | 5 | regex | `MAX\s*\(` | ALL | A |
| agg_stddev | STDDEV() | 10 | regex | `STDDEV\s*\(` | ALL | A |
| agg_variance | VARIANCE() | 10 | regex | `VARIANCE\s*\(` | ALL | A |

### 7.2 공통 수학 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| math_round | ROUND() | 10 | regex | `ROUND\s*\(` | ALL | P |
| math_floor | FLOOR() | 5 | regex | `FLOOR\s*\(` | ALL | A |
| math_ceil | CEIL() / CEILING() | 5 | regex | `CEIL(ING)?\s*\(` | ALL | A |
| math_abs | ABS() | 5 | regex | `ABS\s*\(` | ALL | A |
| math_sign | SIGN() | 5 | regex | `SIGN\s*\(` | ALL | A |
| math_power | POWER() | 5 | regex | `POWER\s*\(` | ALL | A |
| math_sqrt | SQRT() | 5 | regex | `SQRT\s*\(` | ALL | A |
| math_exp | EXP() | 5 | regex | `EXP\s*\(` | ALL | A |
| math_ln | LN() | 5 | regex | `LN\s*\(` | ALL | A |
| math_log | LOG() | 5 | regex | `LOG\s*\(` | ALL | P |

### 7.3 나머지 연산 (그룹: modulo_operation)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| math_mod_func | MOD() 함수 | 5 | regex | `MOD\s*\(` | ORA, MY, MDB, PG, ALT, DB2 | A |
| math_mod_operator | % 연산자 | 5 | regex | `\w+\s*%\s*\d+` | MY, MDB, PG, SS | A |

**변환 매트릭스:**
- ORA MOD(a,b) → SS: a % b
- SS a % b → ORA: MOD(a, b)
- MY a % b → ORA: MOD(a, b)

### 7.4 TRUNCATE (숫자) (그룹: numeric_truncate_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| math_truncate_mysql | TRUNCATE() (숫자) | 10 | regex | `TRUNCATE\s*\(\s*\w+\s*,\s*\d+\s*\)` | MY, MDB | P |
| math_trunc_oracle | TRUNC() (숫자) | 10 | regex | `TRUNC\s*\(\s*\w+\s*,\s*-?\d+\s*\)` | ORA, PG | P |

**변환 매트릭스:**
- MY TRUNCATE → ORA: TRUNC
- ORA TRUNC → MY: TRUNCATE

### 7.5 문자열 집계 (그룹: string_aggregation_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| agg_group_concat | GROUP_CONCAT() | 10 | regex | `GROUP_CONCAT\s*\(` | MY, MDB | P |
| agg_listagg | LISTAGG() | 15 | regex | `LISTAGG\s*\(` | ORA | P |
| agg_string_agg | STRING_AGG() | 10 | regex | `STRING_AGG\s*\(` | PG, SS (2017+) | P |
| agg_wm_concat | WM_CONCAT() | 15 | regex | `WM_CONCAT\s*\(` | ORA (비표준) | M |
| agg_xmlagg | XMLAGG() | 15 | regex | `XMLAGG\s*\(` | ORA | M |

**변환 매트릭스:**
- ORA LISTAGG → MY: GROUP_CONCAT
- ORA LISTAGG → PG: STRING_AGG
- MY GROUP_CONCAT → ORA: LISTAGG
- MY GROUP_CONCAT → PG: STRING_AGG

---

## # 8. 함수 - 변환/NULL처리

### 8.1 NULL 대체 함수 (그룹: null_replace_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| null_nvl | NVL() | 5 | regex | `NVL\s*\(` | ORA, ALT | A |
| null_nvl2 | NVL2() | 10 | regex | `NVL2\s*\(` | ORA | P |
| null_ifnull | IFNULL() | 5 | regex | `IFNULL\s*\(` | MY, MDB | A |
| null_isnull | ISNULL() | 5 | regex | `ISNULL\s*\(` | SS | A |
| null_coalesce | COALESCE() | 3 | regex | `COALESCE\s*\(` | ALL | A |
| null_nullif | NULLIF() | 5 | regex | `NULLIF\s*\(` | ALL | A |

**변환 매트릭스:**
- ORA NVL → MY: IFNULL 또는 COALESCE
- ORA NVL → SS: ISNULL 또는 COALESCE
- ORA NVL → PG: COALESCE
- MY IFNULL → ORA: NVL
- SS ISNULL → ORA: NVL
- 권장: COALESCE (ANSI 표준)

### 8.2 조건 분기 (그룹: conditional_func)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| cond_decode | DECODE() | 15 | regex | `DECODE\s*\(` | ORA | M |
| cond_if_mysql | IF() | 10 | regex | `IF\s*\(\s*\w+` | MY, MDB | P |
| cond_iif | IIF() | 10 | regex | `IIF\s*\(` | SS | P |
| cond_case | CASE WHEN | 3 | regex | `CASE\s+WHEN` | ALL | A |
| cond_case_simple | CASE expr WHEN | 3 | regex | `CASE\s+\w+\s+WHEN` | ALL | A |

**변환 매트릭스:**
- ORA DECODE → ALL: CASE WHEN
- MY IF → ORA: CASE WHEN 또는 DECODE
- SS IIF → ORA: CASE WHEN 또는 DECODE

### 8.3 GREATEST/LEAST

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| cond_greatest | GREATEST() | 10 | regex | `GREATEST\s*\(` | ORA, MY, MDB, PG | P |
| cond_least | LEAST() | 10 | regex | `LEAST\s*\(` | ORA, MY, MDB, PG | P |

**변환 매트릭스:**
- ORA/MY GREATEST → SS: CASE WHEN 또는 IIF 중첩

### 8.4 타입 캐스팅 (그룹: type_casting)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| cast_cast | CAST() | 10 | regex | `CAST\s*\(\s*\w+\s+AS\s+` | ALL | P |
| cast_convert_ss | CONVERT() (SQL Server) | 10 | regex | `CONVERT\s*\(\s*\w+\s*,\s*\w+` | SS | P |
| cast_pg_operator | :: 연산자 | 10 | regex | `\w+::\w+` | PG | P |

**변환 매트릭스:**
- PG col::int → ORA: CAST(col AS NUMBER)
- PG col::int → SS: CAST(col AS INT)
- SS CONVERT → ORA: CAST 또는 TO_CHAR/TO_NUMBER

---


## # 9. 함수 - 윈도우/분석

### 9.1 순위 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| win_row_number | ROW_NUMBER() | 10 | regex | `ROW_NUMBER\s*\(\s*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_rank | RANK() | 10 | regex | `RANK\s*\(\s*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_dense_rank | DENSE_RANK() | 10 | regex | `DENSE_RANK\s*\(\s*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_ntile | NTILE() | 10 | regex | `NTILE\s*\(\d+\)\s*OVER` | ALL (MY 8.0+) | P |
| win_percent_rank | PERCENT_RANK() | 10 | regex | `PERCENT_RANK\s*\(\s*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_cume_dist | CUME_DIST() | 10 | regex | `CUME_DIST\s*\(\s*\)\s*OVER` | ALL (MY 8.0+) | P |

### 9.2 오프셋 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| win_lag | LAG() | 10 | regex | `LAG\s*\(.*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_lead | LEAD() | 10 | regex | `LEAD\s*\(.*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_first_value | FIRST_VALUE() | 10 | regex | `FIRST_VALUE\s*\(.*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_last_value | LAST_VALUE() | 10 | regex | `LAST_VALUE\s*\(.*\)\s*OVER` | ALL (MY 8.0+) | P |
| win_nth_value | NTH_VALUE() | 10 | regex | `NTH_VALUE\s*\(.*\)\s*OVER` | ORA, PG, MY (8.0+) | P |

### 9.3 OVER 절

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| win_over_partition | OVER (PARTITION BY) | 10 | regex | `OVER\s*\(\s*PARTITION\s+BY` | ALL (MY 8.0+) | P |
| win_over_order | OVER (ORDER BY) | 10 | regex | `OVER\s*\(\s*ORDER\s+BY` | ALL (MY 8.0+) | P |
| win_rows_between | ROWS BETWEEN | 15 | regex | `ROWS\s+BETWEEN` | ALL (MY 8.0+) | P |
| win_range_between | RANGE BETWEEN | 15 | regex | `RANGE\s+BETWEEN` | ALL (MY 8.0+) | P |

### 9.4 Oracle 전용 분석 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| win_ratio_to_report | RATIO_TO_REPORT() | 15 | regex | `RATIO_TO_REPORT\s*\(` | ORA | M |
| win_keep_dense_rank | KEEP (DENSE_RANK) | 15 | regex | `KEEP\s*\(\s*DENSE_RANK` | ORA | M |

---

## # 10. 함수 - JSON/배열/기타

### 10.1 JSON 함수 (그룹: json_functions)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| json_extract_mysql | JSON_EXTRACT() | 15 | regex | `JSON_EXTRACT\s*\(` | MY, MDB | P |
| json_value | JSON_VALUE() | 15 | regex | `JSON_VALUE\s*\(` | SS, ORA | P |
| json_query | JSON_QUERY() | 15 | regex | `JSON_QUERY\s*\(` | SS, ORA | P |
| json_object | JSON_OBJECT() | 15 | regex | `JSON_OBJECT\s*\(` | MY, MDB, PG | P |
| json_array | JSON_ARRAY() | 15 | regex | `JSON_ARRAY\s*\(` | MY, MDB, PG | P |
| json_arrow_mysql | -> 연산자 (MySQL) | 15 | regex | `->\s*'` | MY, MDB | P |
| json_arrow_pg | -> 연산자 (PostgreSQL) | 15 | regex | `->\s*'[^']+'\s*` | PG | P |
| json_double_arrow | ->> 연산자 | 15 | regex | `->>\s*'` | MY, MDB, PG | P |
| json_path_pg | #> / #>> 연산자 | 15 | regex | `#>>\?\s*'` | PG | P |

### 10.2 배열 함수 (PostgreSQL)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| arr_array_literal | ARRAY[] | 15 | regex | `ARRAY\s*\[` | PG | M |
| arr_array_agg | ARRAY_AGG() | 15 | regex | `ARRAY_AGG\s*\(` | PG | M |
| arr_unnest | UNNEST() | 15 | regex | `UNNEST\s*\(` | PG | M |
| arr_any | ANY() (배열) | 15 | regex | `=\s*ANY\s*\(` | PG | M |
| arr_all | ALL() (배열) | 15 | regex | `=\s*ALL\s*\(` | PG | M |

### 10.3 비트/HEX 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| bit_and | BIT_AND() | 10 | regex | `BIT_AND\s*\(` | MY, MDB, PG | P |
| bit_or | BIT_OR() | 10 | regex | `BIT_OR\s*\(` | MY, MDB, PG | P |
| bit_xor | BIT_XOR() | 10 | regex | `BIT_XOR\s*\(` | MY, MDB | P |
| hex_func | HEX() | 10 | regex | `HEX\s*\(` | MY, MDB, ORA | P |
| unhex_func | UNHEX() | 10 | regex | `UNHEX\s*\(` | MY, MDB | P |
| rawtohex | RAWTOHEX() | 10 | regex | `RAWTOHEX\s*\(` | ORA | P |
| hextoraw | HEXTORAW() | 10 | regex | `HEXTORAW\s*\(` | ORA | P |

### 10.4 사용자 정의 함수

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| udf_call | 사용자 정의 함수 호출 | 15 | ast | 내장 함수 목록에 없는 함수 호출 | ALL | M |

---


## # 11. JOIN

### 11.1 INNER JOIN

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| join_inner_1 | INNER JOIN 0-1개 | 5 | ast | `(INNER\s+)?JOIN` 카운트 ≤ 1 | ALL | A |
| join_inner_2_3 | INNER JOIN 2-3개 | 10 | ast | `(INNER\s+)?JOIN` 카운트 2-3 | ALL | A |
| join_inner_4plus | INNER JOIN 4개 이상 | 15 | ast | `(INNER\s+)?JOIN` 카운트 ≥ 4 | ALL | A |

### 11.2 OUTER JOIN

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| join_left_1 | LEFT JOIN 0-1개 | 5 | regex | `LEFT\s+(OUTER\s+)?JOIN` 카운트 ≤ 1 | ALL | A |
| join_left_2_3 | LEFT JOIN 2-3개 | 10 | regex | `LEFT\s+(OUTER\s+)?JOIN` 카운트 2-3 | ALL | A |
| join_left_4plus | LEFT JOIN 4개 이상 | 15 | regex | `LEFT\s+(OUTER\s+)?JOIN` 카운트 ≥ 4 | ALL | A |
| join_right_1 | RIGHT JOIN 0-1개 | 5 | regex | `RIGHT\s+(OUTER\s+)?JOIN` 카운트 ≤ 1 | ALL | A |
| join_right_2_3 | RIGHT JOIN 2-3개 | 10 | regex | `RIGHT\s+(OUTER\s+)?JOIN` 카운트 2-3 | ALL | A |
| join_right_4plus | RIGHT JOIN 4개 이상 | 15 | regex | `RIGHT\s+(OUTER\s+)?JOIN` 카운트 ≥ 4 | ALL | A |
| join_full_outer | FULL OUTER JOIN | 15 | regex | `FULL\s+(OUTER\s+)?JOIN` | ALL | P |

### 11.3 특수 JOIN

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| join_cross | CROSS JOIN | 10 | regex | `CROSS\s+JOIN` | ALL | A |
| join_natural | NATURAL JOIN | 10 | regex | `NATURAL\s+(LEFT\|RIGHT\|INNER)?\s*JOIN` | ALL | P |
| join_self | SELF JOIN | 10 | ast | 동일 테이블 2회 이상 참조 | ALL | A |
| join_using | USING 절 | 5 | regex | `JOIN\s+\w+\s+USING\s*\(` | ALL | A |

### 11.4 LATERAL/APPLY

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| join_lateral | LATERAL | 15 | regex | `(,\s*)?LATERAL\s+` | PG, MY (8.0+), ORA (12c+) | P |
| join_cross_apply | CROSS APPLY | 15 | regex | `CROSS\s+APPLY` | SS | P |
| join_outer_apply | OUTER APPLY | 15 | regex | `OUTER\s+APPLY` | SS | P |

**변환 매트릭스:**
- SS CROSS APPLY → PG: LATERAL
- SS OUTER APPLY → PG: LEFT JOIN LATERAL
- PG LATERAL → SS: CROSS APPLY / OUTER APPLY

---

## # 12. 서브쿼리

### 12.1 서브쿼리 유형

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| sub_scalar | 스칼라 서브쿼리 | 10 | ast | SELECT 절 내 `(SELECT ... )` | ALL | A |
| sub_in | IN 서브쿼리 | 5 | regex | `IN\s*\(\s*SELECT` | ALL | A |
| sub_not_in | NOT IN 서브쿼리 | 10 | regex | `NOT\s+IN\s*\(\s*SELECT` | ALL | P |
| sub_exists | EXISTS 서브쿼리 | 5 | regex | `EXISTS\s*\(\s*SELECT` | ALL | A |
| sub_not_exists | NOT EXISTS 서브쿼리 | 10 | regex | `NOT\s+EXISTS\s*\(\s*SELECT` | ALL | A |
| sub_correlated | 상관 서브쿼리 | 15 | ast | 서브쿼리 내 외부 테이블 참조 | ALL | P |
| sub_inline_view | 인라인 뷰 | 10 | ast | FROM 절 서브쿼리 | ALL | A |
| sub_inline_group | 인라인 뷰 + GROUP BY | 15 | ast | FROM 절 서브쿼리 + GROUP BY | ALL | P |

### 12.2 서브쿼리 중첩

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| sub_depth_1 | 서브쿼리 중첩 1단계 | 5 | ast | 서브쿼리 깊이 = 1 | ALL | A |
| sub_depth_2 | 서브쿼리 중첩 2단계 | 10 | ast | 서브쿼리 깊이 = 2 | ALL | P |
| sub_depth_3plus | 서브쿼리 중첩 3단계+ | 15 | ast | 서브쿼리 깊이 ≥ 3 | ALL | P |

### 12.3 기타 절

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| clause_having | HAVING 절 | 3 | keyword | `HAVING` | ALL | A |
| clause_group_by | GROUP BY 절 | 3 | keyword | `GROUP\s+BY` | ALL | A |
| clause_order_by | ORDER BY 절 | 3 | keyword | `ORDER\s+BY` | ALL | A |
| clause_distinct | DISTINCT | 3 | keyword | `SELECT\s+DISTINCT` | ALL | A |

---

## # 13. 집합 연산 (그룹: set_operations)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| set_union_all | UNION ALL | 5 | regex | `UNION\s+ALL` | ALL | A |
| set_union | UNION (DISTINCT) | 5 | regex | `UNION(?!\s+ALL)` | ALL | A |
| set_except | EXCEPT | 15 | keyword | `EXCEPT` | PG, SS, MY (8.0+) | P |
| set_minus | MINUS | 15 | keyword | `MINUS` | ORA, ALT | P |
| set_intersect | INTERSECT | 15 | keyword | `INTERSECT` | ALL | P |

**변환 매트릭스:**
- ORA MINUS → PG/SS: EXCEPT
- PG/SS EXCEPT → ORA: MINUS

---


## # 14. 힌트 (그룹: optimizer_hints)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| hint_none | 힌트 없음 | 0 | - | 힌트 패턴 미검출 | ALL | A |
| hint_oracle | Oracle 힌트 | 10 | regex | `/\*\+.*\*/` | ORA | M |
| hint_mysql_index | MySQL 인덱스 힌트 | 10 | regex | `(USE\|FORCE\|IGNORE)\s+INDEX\s*\(` | MY, MDB | P |
| hint_mysql_opt | MySQL 옵티마이저 힌트 | 10 | regex | `/\*\+\s*(NO_)?[A-Z_]+\s*\(/` | MY (8.0+), MDB | P |
| hint_ss_table | SQL Server 테이블 힌트 | 10 | regex | `WITH\s*\(\s*(NOLOCK\|ROWLOCK\|TABLOCK\|INDEX)` | SS | P |
| hint_ss_query | SQL Server 쿼리 힌트 | 10 | regex | `OPTION\s*\(` | SS | P |
| hint_pg | PostgreSQL pg_hint_plan | 10 | regex | `/\*\+\s*(SeqScan\|IndexScan\|NestLoop)` | PG | P |
| hint_altibase | Altibase 힌트 | 10 | regex | `/\*\+.*\*/` | ALT | M |

**변환 매트릭스:**
- 힌트는 일반적으로 Target DB에서 제거하거나 해당 DB의 힌트 문법으로 재작성 필요
- 성능 테스트 후 필요시 Target DB 힌트 추가 권장

---

## # 15. 데이터 타입 - 기본

### 15.1 문자열 타입

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_varchar | VARCHAR | 0 | keyword | `VARCHAR\s*\(\d+\)` | ALL | A |
| type_varchar2 | VARCHAR2 | 5 | keyword | `VARCHAR2` | ORA | A |
| type_char | CHAR | 5 | keyword | `CHAR\s*\(\d+\)` | ALL | A |
| type_nchar | NCHAR | 5 | keyword | `NCHAR` | ALL | A |
| type_nvarchar | NVARCHAR | 5 | keyword | `NVARCHAR` | ALL | A |
| type_nvarchar2 | NVARCHAR2 | 5 | keyword | `NVARCHAR2` | ORA | A |
| type_text | TEXT | 5 | keyword | `TEXT` | MY, MDB, PG, SS | P |

### 15.2 숫자 타입

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_int | INT / INTEGER | 0 | keyword | `INT(EGER)?` | ALL | A |
| type_bigint | BIGINT | 0 | keyword | `BIGINT` | ALL | A |
| type_smallint | SMALLINT | 0 | keyword | `SMALLINT` | ALL | A |
| type_tinyint | TINYINT | 5 | keyword | `TINYINT` | MY, MDB, SS | P |
| type_number | NUMBER(p,s) | 5 | regex | `NUMBER\s*\(\s*\d+\s*(,\s*\d+)?\s*\)` | ORA | A |
| type_decimal | DECIMAL / NUMERIC | 5 | keyword | `(DECIMAL\|NUMERIC)\s*\(\d+` | ALL | A |
| type_float | FLOAT | 5 | keyword | `FLOAT` | ALL | A |
| type_double | DOUBLE | 5 | keyword | `DOUBLE` | MY, MDB, PG | A |
| type_real | REAL | 5 | keyword | `REAL` | ALL | A |

### 15.3 특수 타입

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_bit | BIT | 5 | keyword | `BIT` | MY, MDB, SS | P |
| type_boolean | BOOLEAN | 5 | keyword | `BOOL(EAN)?` | PG, MY (alias) | P |
| type_enum | ENUM | 5 | regex | `ENUM\s*\(` | MY, MDB | P |
| type_set | SET (타입) | 5 | regex | `SET\s*\('[^']+` | MY, MDB | P |

**변환 매트릭스:**
- ORA NUMBER → PG: NUMERIC
- ORA NUMBER → MY: DECIMAL
- ORA VARCHAR2 → ALL: VARCHAR
- MY TINYINT → PG: SMALLINT
- MY ENUM → PG: CHECK 제약조건 또는 별도 테이블

---

## # 16. 데이터 타입 - 날짜/시간

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_date | DATE | 5 | keyword | `DATE` | ALL | P |
| type_datetime | DATETIME | 5 | keyword | `DATETIME` | MY, MDB, SS | A |
| type_datetime2 | DATETIME2 | 10 | keyword | `DATETIME2` | SS | P |
| type_timestamp | TIMESTAMP | 5 | keyword | `TIMESTAMP` | ALL | P |
| type_timestamp_tz | TIMESTAMP WITH TIME ZONE | 15 | regex | `TIMESTAMP\s+WITH\s+TIME\s+ZONE` | ORA, PG | P |
| type_timestamp_ltz | TIMESTAMP WITH LOCAL TIME ZONE | 15 | regex | `TIMESTAMP\s+WITH\s+LOCAL\s+TIME\s+ZONE` | ORA | P |
| type_datetimeoffset | DATETIMEOFFSET | 15 | keyword | `DATETIMEOFFSET` | SS | P |
| type_time | TIME | 5 | keyword | `TIME` | MY, MDB, PG, SS | A |
| type_interval | INTERVAL (타입) | 15 | keyword | `INTERVAL` (DDL 컨텍스트) | PG, ORA | M |
| type_rowversion | ROWVERSION | 10 | keyword | `ROWVERSION` | SS | P |

**변환 매트릭스:**
- ORA DATE (시간 포함) → MY: DATETIME
- ORA DATE → PG: TIMESTAMP
- SS DATETIME2 → ORA: TIMESTAMP
- ORA TIMESTAMP WITH TIME ZONE → MY: DATETIME + 별도 타임존 컬럼

---


## # 17. 데이터 타입 - 대용량/특수

### 17.1 LOB 타입 (그룹: lob_types)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_blob | BLOB | 10 | keyword | `BLOB` | ORA, MY, MDB | P |
| type_clob | CLOB | 10 | keyword | `CLOB` | ORA | P |
| type_nclob | NCLOB | 10 | keyword | `NCLOB` | ORA | P |
| type_bytea | BYTEA | 10 | keyword | `BYTEA` | PG | P |
| type_varbinary | VARBINARY | 10 | keyword | `VARBINARY` | SS | P |
| type_image | IMAGE | 10 | keyword | `IMAGE` | SS (레거시) | P |
| type_longtext | LONGTEXT | 10 | keyword | `LONGTEXT` | MY, MDB | P |
| type_longblob | LONGBLOB | 10 | keyword | `LONGBLOB` | MY, MDB | P |

**변환 매트릭스:**
- ORA CLOB → PG: TEXT
- ORA BLOB → PG: BYTEA
- ORA CLOB → MY: LONGTEXT
- SS VARBINARY → PG: BYTEA

### 17.2 JSON/XML 타입

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_json | JSON | 10 | keyword | `JSON` | MY, MDB, PG | P |
| type_jsonb | JSONB | 10 | keyword | `JSONB` | PG | P |
| type_xml | XML | 15 | keyword | `XML` | SS | M |
| type_xmltype | XMLTYPE | 15 | keyword | `XMLTYPE` | ORA | M |

### 17.3 공간 타입

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_geometry | GEOMETRY | 15 | keyword | `GEOMETRY` | MY, MDB, PG, SS | M |
| type_geography | GEOGRAPHY | 15 | keyword | `GEOGRAPHY` | SS, PG | M |
| type_sdo_geometry | SDO_GEOMETRY | 15 | keyword | `SDO_GEOMETRY` | ORA | M |

### 17.4 기타 특수 타입

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_array | ARRAY | 15 | regex | `\w+\s*\[\s*\]` | PG | M |
| type_hstore | HSTORE | 15 | keyword | `HSTORE` | PG | M |

---

## # 18. 데이터 타입 - 식별자/네트워크

### 18.1 자동 증가 (그룹: auto_increment_types)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_serial | SERIAL | 10 | keyword | `SERIAL` | PG | P |
| type_bigserial | BIGSERIAL | 10 | keyword | `BIGSERIAL` | PG | P |
| type_auto_increment | AUTO_INCREMENT | 10 | keyword | `AUTO_INCREMENT` | MY, MDB | P |
| type_identity_ss | IDENTITY (SQL Server) | 10 | regex | `IDENTITY\s*\(\s*\d+\s*,\s*\d+\s*\)` | SS | P |
| type_identity_ora | GENERATED AS IDENTITY | 10 | regex | `GENERATED.*AS\s+IDENTITY` | ORA (12c+), PG | P |

**변환 매트릭스:**
- PG SERIAL → MY: INT AUTO_INCREMENT
- PG SERIAL → ORA: NUMBER + SEQUENCE + TRIGGER 또는 IDENTITY (12c+)
- MY AUTO_INCREMENT → PG: SERIAL
- MY AUTO_INCREMENT → ORA: SEQUENCE + TRIGGER 또는 IDENTITY

### 18.2 UUID/GUID (그룹: uuid_types)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_uuid | UUID | 10 | keyword | `UUID` | PG | P |
| type_uniqueidentifier | UNIQUEIDENTIFIER | 10 | keyword | `UNIQUEIDENTIFIER` | SS | P |
| type_raw_guid | RAW(16) (GUID) | 10 | regex | `RAW\s*\(\s*16\s*\)` | ORA | P |

**변환 매트릭스:**
- PG UUID → ORA: RAW(16)
- PG UUID → SS: UNIQUEIDENTIFIER
- SS UNIQUEIDENTIFIER → PG: UUID

### 18.3 네트워크 타입 (PostgreSQL 전용)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_inet | INET | 10 | keyword | `INET` | PG | M |
| type_cidr | CIDR | 10 | keyword | `CIDR` | PG | M |
| type_macaddr | MACADDR | 10 | keyword | `MACADDR` | PG | M |

### 18.4 금액 타입

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| type_money_pg | MONEY (PostgreSQL) | 10 | keyword | `MONEY` | PG | P |
| type_money_ss | MONEY (SQL Server) | 10 | keyword | `MONEY` | SS | P |
| type_smallmoney | SMALLMONEY | 10 | keyword | `SMALLMONEY` | SS | P |

---


## # 19. 데이터 처리 특성

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 | 비고 |
|----|-----|-------|---------|------|---------------|---------|------|
| data_implicit_num_str | 숫자-문자열 암시적 변환 | 5 | ast | 숫자 컬럼과 문자열 비교 | ALL | P | 정적 분석 어려움 |
| data_implicit_date_str | 날짜-문자열 암시적 변환 | 5 | ast | 날짜 컬럼과 문자열 비교 | ALL | P | 정적 분석 어려움 |
| data_date_string_compare | 날짜 문자열 비교 | 5 | regex | `\w+\s*(=\|<\|>)\s*'[0-9]{4}-[0-9]{2}-[0-9]{2}'` | ALL | P | |
| data_null_sort | NULL 정렬 순서 | 10 | regex | `ORDER\s+BY.*NULLS\s+(FIRST\|LAST)` | ORA, PG | P | |
| data_empty_string_null | 빈 문자열 = NULL | 10 | ast | `''` 사용 | ORA | M | Oracle 특유 동작 |
| data_null_arithmetic | NULL 연산 결과 | 5 | ast | NULL과의 산술 연산 | ALL | P | |

**주의사항:**
- Oracle에서 빈 문자열 `''`은 NULL로 처리됨 (다른 DBMS와 다름)
- 이 특성은 정적 분석으로 완전히 검출하기 어려우며, 런타임 동작 차이 발생 가능

---

## # 20. 트랜잭션/락

### 20.1 SELECT FOR UPDATE (그룹: select_for_update)

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| lock_for_update | SELECT FOR UPDATE | 10 | regex | `SELECT.*FOR\s+UPDATE` | ALL | P |
| lock_for_update_nowait | FOR UPDATE NOWAIT | 15 | regex | `FOR\s+UPDATE\s+NOWAIT` | ORA, PG | P |
| lock_for_update_wait | FOR UPDATE WAIT n | 15 | regex | `FOR\s+UPDATE\s+WAIT\s+\d+` | ORA | P |
| lock_for_update_skip | FOR UPDATE SKIP LOCKED | 15 | regex | `FOR\s+UPDATE\s+SKIP\s+LOCKED` | ORA, PG, MY (8.0+) | P |
| lock_for_share | FOR SHARE | 10 | regex | `FOR\s+SHARE` | PG, MY | P |
| lock_for_key_share | FOR KEY SHARE | 10 | regex | `FOR\s+KEY\s+SHARE` | PG | P |

### 20.2 SQL Server 락 힌트

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| lock_nolock | WITH (NOLOCK) | 10 | regex | `WITH\s*\(\s*NOLOCK\s*\)` | SS | P |
| lock_rowlock | WITH (ROWLOCK) | 10 | regex | `WITH\s*\(\s*ROWLOCK\s*\)` | SS | P |
| lock_tablock | WITH (TABLOCK) | 10 | regex | `WITH\s*\(\s*TABLOCK\s*\)` | SS | P |
| lock_updlock | WITH (UPDLOCK) | 10 | regex | `WITH\s*\(\s*UPDLOCK\s*\)` | SS | P |
| lock_holdlock | WITH (HOLDLOCK) | 10 | regex | `WITH\s*\(\s*HOLDLOCK\s*\)` | SS | P |

### 20.3 테이블 락

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| lock_table | LOCK TABLE | 15 | regex | `LOCK\s+TABLE` | ALL | P |
| lock_table_mode | LOCK TABLE ... IN ... MODE | 15 | regex | `LOCK\s+TABLE.*IN\s+(SHARE\|EXCLUSIVE)` | ORA, PG | P |

### 20.4 트랜잭션 제어

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| tx_begin | BEGIN TRANSACTION | 5 | regex | `BEGIN(\s+TRAN(SACTION)?\|\s+WORK)?` | ALL | A |
| tx_commit | COMMIT | 5 | keyword | `COMMIT` | ALL | A |
| tx_rollback | ROLLBACK | 5 | keyword | `ROLLBACK` | ALL | A |
| tx_savepoint | SAVEPOINT | 10 | regex | `SAVEPOINT\s+\w+` | ALL | A |
| tx_rollback_to | ROLLBACK TO SAVEPOINT | 10 | regex | `ROLLBACK\s+(TO\s+)?(SAVEPOINT\s+)?\w+` | ALL | A |
| tx_isolation | SET TRANSACTION ISOLATION LEVEL | 10 | regex | `SET\s+TRANSACTION\s+ISOLATION\s+LEVEL` | ALL | P |

---

## # 21. 문자열/인코딩 (그룹: string_concat_operators)

### 21.1 문자열 연결 연산자

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_concat_pipe | \|\| 연산자 (문자열 연결) | 10 | regex | `'[^']*'\s*\|\|\s*'[^']*'` 또는 `\w+\s*\|\|\s*\w+` | ORA, PG, ALT, DB2 | P |
| str_concat_plus | + 연산자 (문자열 연결) | 10 | regex | `'[^']*'\s*\+\s*'[^']*'` | SS | P |
| str_concat_func_all | CONCAT() 함수 | 5 | regex | `CONCAT\s*\(` | ALL | A |

**변환 매트릭스:**
- ORA `a || b` → MY: CONCAT(a, b)
- ORA `a || b` → SS: a + b
- SS `a + b` → ORA: a || b
- SS `a + b` → MY: CONCAT(a, b)
- 권장: CONCAT() 함수 사용 (대부분 DBMS 지원)

**주의사항:**
- MySQL에서 `||`는 기본적으로 논리 OR 연산자 (PIPES_AS_CONCAT 모드 필요)
- SQL Server에서 `+`는 숫자 덧셈과 문자열 연결 모두 사용 (컨텍스트 구분 필요)

### 21.2 Collation/인코딩

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_collate | COLLATE 절 | 10 | regex | `COLLATE\s+\w+` | ALL | P |
| str_binary_mysql | BINARY (대소문자 구분) | 10 | regex | `BINARY\s+\w+` | MY, MDB | P |
| str_collate_cs | 대소문자 구분 Collation | 10 | regex | `COLLATE\s+\w+_CS` | SS | P |

### 21.3 패턴 매칭

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| str_like | LIKE | 5 | regex | `LIKE\s+'[^']*[%_][^']*'` | ALL | A |
| str_escape | ESCAPE 절 | 5 | regex | `ESCAPE\s+'.'` | ALL | P |
| str_similar_to | SIMILAR TO | 10 | regex | `SIMILAR\s+TO` | PG | P |
| str_glob | GLOB | 10 | keyword | `GLOB` | SQLite | P |

---


## # 22. 에러 처리

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| err_try_catch | TRY...CATCH | 15 | regex | `BEGIN\s+TRY` | SS | M |
| err_exception_when | EXCEPTION WHEN | 15 | regex | `EXCEPTION\s+WHEN` | ORA, PG | M |
| err_declare_handler | DECLARE HANDLER | 15 | regex | `DECLARE\s+(CONTINUE\|EXIT)\s+HANDLER` | MY, MDB | M |
| err_raise_pg | RAISE (PostgreSQL) | 15 | regex | `RAISE\s+(NOTICE\|WARNING\|EXCEPTION)` | PG | M |
| err_raise_app_error | RAISE_APPLICATION_ERROR | 15 | regex | `RAISE_APPLICATION_ERROR\s*\(` | ORA | M |
| err_raiserror | RAISERROR | 15 | regex | `RAISERROR\s*\(` | SS | M |
| err_throw | THROW | 15 | keyword | `THROW` | SS | M |
| err_signal | SIGNAL SQLSTATE | 15 | regex | `SIGNAL\s+SQLSTATE` | MY, MDB | M |

**변환 매트릭스:**
- ORA EXCEPTION WHEN → PG: EXCEPTION WHEN (유사)
- ORA EXCEPTION WHEN → SS: TRY...CATCH
- SS TRY...CATCH → ORA: EXCEPTION WHEN
- MY DECLARE HANDLER → PG: EXCEPTION WHEN

---

## # 23. 동적 SQL

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| dyn_execute_immediate | EXECUTE IMMEDIATE | 15 | regex | `EXECUTE\s+IMMEDIATE` | ORA, PG | M |
| dyn_prepare | PREPARE | 15 | regex | `PREPARE\s+\w+\s+FROM` | MY, MDB | M |
| dyn_execute_mysql | EXECUTE (MySQL) | 15 | regex | `EXECUTE\s+\w+(\s+USING)?` | MY, MDB | M |
| dyn_sp_executesql | sp_executesql | 15 | regex | `sp_executesql\s+` | SS | M |
| dyn_exec_string | EXEC() / EXECUTE() | 15 | regex | `EXEC(UTE)?\s*\(\s*'` | SS | M |
| dyn_dbms_sql | DBMS_SQL | 20 | regex | `DBMS_SQL\.\w+` | ORA | M |

**변환 매트릭스:**
- ORA EXECUTE IMMEDIATE → PG: EXECUTE (유사)
- ORA EXECUTE IMMEDIATE → SS: sp_executesql
- SS sp_executesql → ORA: EXECUTE IMMEDIATE

---

## # 24. 커서

| ID | 항목 | 가중치 | 검출방식 | 패턴 | applicable_db | 변환등급 |
|----|-----|-------|---------|------|---------------|---------|
| cur_declare | DECLARE CURSOR | 15 | regex | `DECLARE\s+\w+\s+CURSOR` | ALL | M |
| cur_cursor_is | CURSOR ... IS SELECT | 15 | regex | `CURSOR\s+\w+\s+IS\s+SELECT` | ORA | M |
| cur_cursor_for | CURSOR FOR | 15 | regex | `\w+\s+CURSOR\s+FOR` | PG | M |
| cur_open | OPEN CURSOR | 10 | regex | `OPEN\s+\w+` | ALL | M |
| cur_fetch | FETCH CURSOR | 15 | regex | `FETCH\s+(NEXT\s+)?FROM\s+\w+` | ALL | M |
| cur_fetch_into | FETCH INTO | 15 | regex | `FETCH\s+\w+\s+INTO` | ORA | M |
| cur_close | CLOSE CURSOR | 10 | regex | `CLOSE\s+\w+` | ALL | M |
| cur_deallocate | DEALLOCATE CURSOR | 10 | regex | `DEALLOCATE\s+\w+` | SS | M |
| cur_for_loop | FOR ... IN CURSOR LOOP | 15 | regex | `FOR\s+\w+\s+IN\s+\w+\s+LOOP` | ORA, PG | M |
| cur_ref_cursor | REF CURSOR | 20 | regex | `REF\s+CURSOR` | ORA | M |
| cur_sys_refcursor | SYS_REFCURSOR | 20 | keyword | `SYS_REFCURSOR` | ORA | M |

---

## 범례

### 자동변환 등급

| 등급 | 코드 | 설명 | 복잡도 계수 |
|-----|------|------|-----------|
| 자동 | A | 단순 치환으로 자동 변환 가능 | 0.5 |
| 부분 | P | 부분 자동 변환 (검증 필요) | 1.0 |
| 수동 | M | 수동 변환 필요 | 1.5 |

### 검출방식

| 방식 | 설명 |
|-----|------|
| regex | 정규식 패턴 매칭 |
| keyword | 단순 키워드 존재 여부 |
| ast | AST 파싱 필요 (구조적 분석) |

### applicable_db 약어

| 약어 | DBMS |
|-----|------|
| ALL | 모든 DBMS |
| ORA | Oracle |
| MY | MySQL |
| MDB | MariaDB |
| PG | PostgreSQL |
| SS | SQL Server |
| ALT | Altibase |
| DB2 | IBM DB2 |
