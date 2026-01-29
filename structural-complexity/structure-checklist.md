# SQL 복잡도 체크리스트 (Complexity Checklist)

## 개요

이 체크리스트는 **SQL 자체의 구조적 복잡도**를 측정합니다. Hybrid 구조를 채택하여 공통 항목과 DBMS별 항목을 분리합니다.

### 입력 파라미터

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| query_list | O | SQL 쿼리 목록 파일 |
| source_db | O | Source DBMS (ORA, MY, MDB, PG, SS, ALT, DB2) |

### 지원 DBMS

| 약어 | DBMS |
|-----|------|
| ORA | Oracle |
| MY | MySQL |
| MDB | MariaDB |
| PG | PostgreSQL |
| SS | SQL Server |
| ALT | Altibase |
| DB2 | IBM DB2 |

### 검출 방식

| 방식 | 설명 |
|------|------|
| ast | AST 파싱 (sqlparse 등) |
| regex | 정규식 패턴 매칭 |
| metric | 문자열 메트릭 계산 |

---

## Part 1: 공통 항목 (Common Rules)

모든 DBMS에 공통으로 적용됩니다.

---

### 1.1 구조적 복잡성 - JOIN

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_join_0 | JOIN 없음 | 0 | ast | JOIN 카운트 = 0 |
| c_join_1 | JOIN 1개 | 5 | ast | JOIN 카운트 = 1 |
| c_join_2_3 | JOIN 2-3개 | 10 | ast | JOIN 카운트 2-3 |
| c_join_4_5 | JOIN 4-5개 | 15 | ast | JOIN 카운트 4-5 |
| c_join_6plus | JOIN 6개 이상 | 20 | ast | JOIN 카운트 ≥ 6 |

### 1.2 구조적 복잡성 - 서브쿼리

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_subq_0 | 서브쿼리 없음 | 0 | ast | 깊이 = 0 |
| c_subq_depth_1 | 서브쿼리 깊이 1 | 10 | ast | 깊이 = 1 |
| c_subq_depth_2 | 서브쿼리 깊이 2 | 20 | ast | 깊이 = 2 |
| c_subq_depth_3plus | 서브쿼리 깊이 3+ | 30 | ast | 깊이 ≥ 3 |
| c_subq_count | 서브쿼리 개수 | 5/개 | ast | 서브쿼리 총 개수 × 5 |
| c_subq_correlated | 상관 서브쿼리 | 15 | ast | 외부 테이블 참조 |

### 1.3 구조적 복잡성 - CTE

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_cte_1 | CTE 1개 | 10 | regex | `WITH\s+\w+\s+AS\s*\(` 카운트 = 1 |
| c_cte_2_3 | CTE 2-3개 | 15 | regex | CTE 카운트 2-3 |
| c_cte_4plus | CTE 4개 이상 | 20 | regex | CTE 카운트 ≥ 4 |

### 1.4 구조적 복잡성 - 집합 연산

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_union | UNION | 10 | regex | `\bUNION\b(?!\s+ALL)` 카운트 |
| c_union_all | UNION ALL | 5 | regex | `\bUNION\s+ALL\b` 카운트 |
| c_intersect | INTERSECT | 10 | regex | `\bINTERSECT\b` 카운트 |

---

### 1.5 절 복잡성 - SELECT

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_select_cols_1_5 | 컬럼 1-5개 | 0 | ast | SELECT 컬럼 수 1-5 |
| c_select_cols_6_10 | 컬럼 6-10개 | 5 | ast | SELECT 컬럼 수 6-10 |
| c_select_cols_11_20 | 컬럼 11-20개 | 10 | ast | SELECT 컬럼 수 11-20 |
| c_select_cols_21plus | 컬럼 21개 이상 | 15 | ast | SELECT 컬럼 수 ≥ 21 |
| c_select_star | SELECT * | 5 | regex | `SELECT\s+\*` |
| c_distinct | DISTINCT | 5 | regex | `SELECT\s+(ALL\s+)?DISTINCT` |

### 1.6 절 복잡성 - WHERE

> 조건의 복잡도는 조건 수(AND/OR)로 측정합니다. 개별 비교 연산자(=, >=, <=, BETWEEN, LIKE 등)는 구조적 복잡도에 영향을 주지 않으므로 별도 카운팅하지 않습니다.

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_where_cond_1_3 | 조건 1-3개 | 0 | ast | 조건 수 1-3 |
| c_where_cond_4_6 | 조건 4-6개 | 5 | ast | 조건 수 4-6 |
| c_where_cond_7_10 | 조건 7-10개 | 10 | ast | 조건 수 7-10 |
| c_where_cond_11plus | 조건 11개 이상 | 15 | ast | 조건 수 ≥ 11 |
| c_where_in_list | IN (값 목록) | 5 | regex | `IN\s*\([^)]+\)` (서브쿼리 제외) |

### 1.7 절 복잡성 - GROUP BY / HAVING / ORDER BY

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_group_by | GROUP BY 사용 | 5 | regex | `\bGROUP\s+BY\b` |
| c_group_cols_4plus | GROUP BY 컬럼 4개+ | 5 | ast | GROUP BY 컬럼 수 ≥ 4 |
| c_having | HAVING 사용 | 10 | regex | `\bHAVING\b` |
| c_order_by | ORDER BY 사용 | 3 | regex | `\bORDER\s+BY\b` |
| c_order_cols_4plus | ORDER BY 컬럼 4개+ | 5 | ast | ORDER BY 컬럼 수 ≥ 4 |

---

### 1.8 함수/표현식 - 집계 함수

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_agg_count | COUNT() | 3/개 | regex | `\bCOUNT\s*\(` 카운트 × 3 |
| c_agg_sum | SUM() | 3/개 | regex | `\bSUM\s*\(` 카운트 × 3 |
| c_agg_avg | AVG() | 3/개 | regex | `\bAVG\s*\(` 카운트 × 3 |
| c_agg_min_max | MIN()/MAX() | 3/개 | regex | `\b(MIN\|MAX)\s*\(` 카운트 × 3 |
| c_agg_distinct | 집계 내 DISTINCT | 5/개 | regex | `(COUNT\|SUM\|AVG)\s*\(\s*DISTINCT` |

### 1.9 함수/표현식 - 윈도우 함수

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_window_over | OVER 절 | 10/개 | regex | `\bOVER\s*\(` 카운트 × 10 |
| c_window_partition | PARTITION BY | 5/개 | regex | `\bPARTITION\s+BY\b` 카운트 × 5 |
| c_window_frame | ROWS/RANGE BETWEEN | 10/개 | regex | `(ROWS\|RANGE)\s+BETWEEN` 카운트 × 10 |

### 1.10 함수/표현식 - CASE

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_case | CASE 표현식 | 5/개 | regex | `\bCASE\b` 카운트 × 5 |
| c_case_when | WHEN 절 | 2/개 | regex | `\bWHEN\b` 카운트 × 2 |
| c_case_nested | 중첩 CASE | 15 | ast | CASE 내부에 CASE 존재 |

### 1.11 함수/표현식 - 공통 함수

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_func_string | 문자열 함수 | 2/개 | regex | `(SUBSTR\|SUBSTRING\|CONCAT\|REPLACE\|TRIM\|UPPER\|LOWER)\s*\(` |
| c_func_math | 수학 함수 | 2/개 | regex | `(ROUND\|FLOOR\|CEIL\|ABS\|MOD)\s*\(` |
| c_func_null | NULL 처리 함수 | 2/개 | regex | `(COALESCE\|NULLIF)\s*\(` |
| c_func_cast | CAST 함수 | 3/개 | regex | `\bCAST\s*\(` |

---

### 1.12 쿼리 메트릭

| ID | 항목 | 가중치 | 검출방식 | 검출 로직 |
|----|------|--------|---------|----------|
| c_len_short | 짧은 쿼리 (< 200자) | 0 | metric | len(sql) < 200 |
| c_len_medium | 중간 쿼리 (200-500자) | 5 | metric | 200 ≤ len(sql) < 500 |
| c_len_long | 긴 쿼리 (500-1000자) | 10 | metric | 500 ≤ len(sql) < 1000 |
| c_len_very_long | 매우 긴 쿼리 (1000-2000자) | 15 | metric | 1000 ≤ len(sql) < 2000 |
| c_len_huge | 초대형 쿼리 (2000자+) | 20 | metric | len(sql) ≥ 2000 |
| c_tables_3_5 | 테이블 3-5개 | 5 | ast | 참조 테이블 수 3-5 |
| c_tables_6_10 | 테이블 6-10개 | 10 | ast | 참조 테이블 수 6-10 |
| c_tables_11plus | 테이블 11개 이상 | 15 | ast | 참조 테이블 수 ≥ 11 |

---


## Part 2: DBMS별 항목 (DBMS-Specific Rules)

Source DB에 따라 선택적으로 적용됩니다.

---

### 2.1 Oracle (ORA)

| ID | 항목 | 가중치 | 검출방식 | 패턴 |
|----|------|--------|---------|------|
| ora_plus_join | (+) 조인 문법 | 10 | regex | `\w+\s*\(\+\)` |
| ora_connect_by | CONNECT BY | 25 | regex | `\bCONNECT\s+BY\b` |
| ora_start_with | START WITH | 20 | regex | `\bSTART\s+WITH\b` |
| ora_prior | PRIOR | 15 | regex | `\bPRIOR\s+\w+` |
| ora_sys_connect_path | SYS_CONNECT_BY_PATH | 20 | regex | `SYS_CONNECT_BY_PATH\s*\(` |
| ora_connect_by_root | CONNECT_BY_ROOT | 20 | regex | `CONNECT_BY_ROOT\s+\w+` |
| ora_level | LEVEL (계층) | 10 | regex | `\bLEVEL\b` |
| ora_rownum | ROWNUM | 15 | regex | `\bROWNUM\b` |
| ora_rowid | ROWID | 15 | regex | `\bROWID\b` |
| ora_decode | DECODE() | 10 | regex | `\bDECODE\s*\(` |
| ora_nvl | NVL() | 3 | regex | `\bNVL\s*\(` |
| ora_nvl2 | NVL2() | 5 | regex | `\bNVL2\s*\(` |
| ora_to_char | TO_CHAR() | 3 | regex | `\bTO_CHAR\s*\(` |
| ora_to_date | TO_DATE() | 3 | regex | `\bTO_DATE\s*\(` |
| ora_to_number | TO_NUMBER() | 3 | regex | `\bTO_NUMBER\s*\(` |
| ora_sysdate | SYSDATE | 2 | regex | `\bSYSDATE\b` |
| ora_dual | DUAL 테이블 | 2 | regex | `\bFROM\s+DUAL\b` |
| ora_listagg | LISTAGG() | 10 | regex | `\bLISTAGG\s*\(` |
| ora_pivot | PIVOT | 20 | regex | `\bPIVOT\s*\(` |
| ora_unpivot | UNPIVOT | 20 | regex | `\bUNPIVOT\s*\(` |
| ora_model | MODEL 절 | 25 | regex | `\bMODEL\s+(RETURN\|DIMENSION\|MEASURES)` |
| ora_hint | Oracle 힌트 | 10 | regex | `/\*\+.*\*/` |
| ora_merge | MERGE INTO | 15 | regex | `\bMERGE\s+INTO\b` |
| ora_returning | RETURNING INTO | 10 | regex | `\bRETURNING\b.*\bINTO\b` |
| ora_bulk_collect | BULK COLLECT | 15 | regex | `\bBULK\s+COLLECT\b` |
| ora_forall | FORALL | 15 | regex | `\bFORALL\b` |
| ora_execute_immediate | EXECUTE IMMEDIATE | 20 | regex | `\bEXECUTE\s+IMMEDIATE\b` |
| ora_ref_cursor | REF CURSOR | 20 | regex | `\bREF\s+CURSOR\b\|SYS_REFCURSOR` |
| ora_exception | EXCEPTION WHEN | 15 | regex | `\bEXCEPTION\s+WHEN\b` |
| ora_minus | MINUS | 10 | regex | `\bMINUS\b` |

---

### 2.2 MySQL / MariaDB (MY, MDB)

| ID | 항목 | 가중치 | 검출방식 | 패턴 |
|----|------|--------|---------|------|
| my_limit | LIMIT | 5 | regex | `\bLIMIT\s+\d+` |
| my_limit_offset | LIMIT OFFSET | 5 | regex | `\bLIMIT\s+\d+\s+OFFSET\s+\d+` |
| my_ifnull | IFNULL() | 3 | regex | `\bIFNULL\s*\(` |
| my_if_func | IF() 함수 | 5 | regex | `\bIF\s*\(\s*\w+` |
| my_group_concat | GROUP_CONCAT() | 10 | regex | `\bGROUP_CONCAT\s*\(` |
| my_date_format | DATE_FORMAT() | 5 | regex | `\bDATE_FORMAT\s*\(` |
| my_str_to_date | STR_TO_DATE() | 5 | regex | `\bSTR_TO_DATE\s*\(` |
| my_date_add | DATE_ADD() | 5 | regex | `\bDATE_ADD\s*\(` |
| my_date_sub | DATE_SUB() | 5 | regex | `\bDATE_SUB\s*\(` |
| my_now | NOW() | 2 | regex | `\bNOW\s*\(\s*\)` |
| my_curdate | CURDATE() | 2 | regex | `\bCURDATE\s*\(\s*\)` |
| my_on_duplicate | ON DUPLICATE KEY UPDATE | 10 | regex | `\bON\s+DUPLICATE\s+KEY\s+UPDATE\b` |
| my_insert_ignore | INSERT IGNORE | 10 | regex | `\bINSERT\s+IGNORE\b` |
| my_replace_into | REPLACE INTO | 10 | regex | `\bREPLACE\s+INTO\b` |
| my_straight_join | STRAIGHT_JOIN | 10 | regex | `\bSTRAIGHT_JOIN\b` |
| my_use_index | USE INDEX | 10 | regex | `\bUSE\s+INDEX\s*\(` |
| my_force_index | FORCE INDEX | 10 | regex | `\bFORCE\s+INDEX\s*\(` |
| my_ignore_index | IGNORE INDEX | 10 | regex | `\bIGNORE\s+INDEX\s*\(` |
| my_regexp | REGEXP / RLIKE | 5 | regex | `\b(REGEXP\|RLIKE)\b` |
| my_binary | BINARY (비교) | 5 | regex | `\bBINARY\s+\w+` |
| my_handler | DECLARE HANDLER | 15 | regex | `\bDECLARE\s+(CONTINUE\|EXIT)\s+HANDLER\b` |
| my_prepare | PREPARE / EXECUTE | 15 | regex | `\bPREPARE\s+\w+\s+FROM\b` |

---

### 2.3 PostgreSQL (PG)

| ID | 항목 | 가중치 | 검출방식 | 패턴 |
|----|------|--------|---------|------|
| pg_limit | LIMIT | 5 | regex | `\bLIMIT\s+\d+` |
| pg_offset | OFFSET | 5 | regex | `\bOFFSET\s+\d+` |
| pg_returning | RETURNING | 10 | regex | `\bRETURNING\b` |
| pg_lateral | LATERAL | 15 | regex | `\bLATERAL\b` |
| pg_array | ARRAY[] | 15 | regex | `\bARRAY\s*\[` |
| pg_array_agg | ARRAY_AGG() | 15 | regex | `\bARRAY_AGG\s*\(` |
| pg_unnest | UNNEST() | 15 | regex | `\bUNNEST\s*\(` |
| pg_string_agg | STRING_AGG() | 10 | regex | `\bSTRING_AGG\s*\(` |
| pg_json_extract | JSON 연산자 (->, ->>) | 10 | regex | `->\|->>'` |
| pg_jsonb | JSONB 연산자 | 10 | regex | `@>\|<@\|\?\|\|\?&` |
| pg_cast_operator | :: 캐스팅 | 5 | regex | `\w+::\w+` |
| pg_similar_to | SIMILAR TO | 10 | regex | `\bSIMILAR\s+TO\b` |
| pg_regex_operator | ~ 정규식 | 10 | regex | `~\s*'\|~\*\s*'\|!~` |
| pg_ilike | ILIKE | 5 | regex | `\bILIKE\b` |
| pg_distinct_on | DISTINCT ON | 10 | regex | `\bDISTINCT\s+ON\s*\(` |
| pg_for_update_skip | FOR UPDATE SKIP LOCKED | 15 | regex | `\bFOR\s+UPDATE\s+SKIP\s+LOCKED\b` |
| pg_on_conflict | ON CONFLICT | 10 | regex | `\bON\s+CONFLICT\b` |
| pg_with_recursive | WITH RECURSIVE | 20 | regex | `\bWITH\s+RECURSIVE\b` |
| pg_exception | EXCEPTION WHEN | 15 | regex | `\bEXCEPTION\s+WHEN\b` |
| pg_raise | RAISE | 15 | regex | `\bRAISE\s+(NOTICE\|WARNING\|EXCEPTION)\b` |
| pg_execute | EXECUTE (동적) | 15 | regex | `\bEXECUTE\s+'` |

---

### 2.4 SQL Server (SS)

| ID | 항목 | 가중치 | 검출방식 | 패턴 |
|----|------|--------|---------|------|
| ss_top | TOP | 10 | regex | `\bSELECT\s+TOP\s+\d+` |
| ss_top_percent | TOP PERCENT | 10 | regex | `\bTOP\s+\d+\s+PERCENT\b` |
| ss_offset_fetch | OFFSET FETCH | 5 | regex | `\bOFFSET\s+\d+\s+ROWS\s+FETCH\b` |
| ss_cross_apply | CROSS APPLY | 15 | regex | `\bCROSS\s+APPLY\b` |
| ss_outer_apply | OUTER APPLY | 15 | regex | `\bOUTER\s+APPLY\b` |
| ss_isnull | ISNULL() | 3 | regex | `\bISNULL\s*\(` |
| ss_iif | IIF() | 5 | regex | `\bIIF\s*\(` |
| ss_string_agg | STRING_AGG() | 10 | regex | `\bSTRING_AGG\s*\(` |
| ss_getdate | GETDATE() | 2 | regex | `\bGETDATE\s*\(\s*\)` |
| ss_dateadd | DATEADD() | 5 | regex | `\bDATEADD\s*\(` |
| ss_datediff | DATEDIFF() | 5 | regex | `\bDATEDIFF\s*\(` |
| ss_datepart | DATEPART() | 5 | regex | `\bDATEPART\s*\(` |
| ss_convert | CONVERT() | 5 | regex | `\bCONVERT\s*\(` |
| ss_nolock | WITH (NOLOCK) | 10 | regex | `\bWITH\s*\(\s*NOLOCK\s*\)` |
| ss_rowlock | WITH (ROWLOCK) | 10 | regex | `\bWITH\s*\(\s*ROWLOCK\s*\)` |
| ss_tablock | WITH (TABLOCK) | 10 | regex | `\bWITH\s*\(\s*TABLOCK\s*\)` |
| ss_option | OPTION 힌트 | 10 | regex | `\bOPTION\s*\(` |
| ss_merge | MERGE | 15 | regex | `\bMERGE\s+\w+` |
| ss_output | OUTPUT 절 | 10 | regex | `\bOUTPUT\s+(INSERTED\|DELETED)\.` |
| ss_try_catch | TRY...CATCH | 15 | regex | `\bBEGIN\s+TRY\b` |
| ss_throw | THROW | 15 | regex | `\bTHROW\b` |
| ss_raiserror | RAISERROR | 15 | regex | `\bRAISERROR\s*\(` |
| ss_sp_executesql | sp_executesql | 20 | regex | `\bsp_executesql\b` |
| ss_exec_string | EXEC() | 15 | regex | `\bEXEC(UTE)?\s*\(\s*'` |
| ss_pivot | PIVOT | 20 | regex | `\bPIVOT\s*\(` |
| ss_unpivot | UNPIVOT | 20 | regex | `\bUNPIVOT\s*\(` |

---

### 2.5 Altibase (ALT)

| ID | 항목 | 가중치 | 검출방식 | 패턴 |
|----|------|--------|---------|------|
| alt_limit | LIMIT | 5 | regex | `\bLIMIT\s+\d+` |
| alt_rownum | ROWNUM | 15 | regex | `\bROWNUM\b` |
| alt_nvl | NVL() | 3 | regex | `\bNVL\s*\(` |
| alt_decode | DECODE() | 10 | regex | `\bDECODE\s*\(` |
| alt_connect_by | CONNECT BY | 25 | regex | `\bCONNECT\s+BY\b` |
| alt_hint | Altibase 힌트 | 10 | regex | `/\*\+.*\*/` |
| alt_upsert | UPSERT | 10 | regex | `\bUPSERT\b` |
| alt_enqueue | ENQUEUE | 15 | regex | `\bENQUEUE\b` |
| alt_dequeue | DEQUEUE | 15 | regex | `\bDEQUEUE\b` |

---

## Part 3: 점수 계산

### 카테고리별 가중치

| 카테고리 | 비중 | 최대 점수 |
|----------|------|----------|
| 구조적 복잡성 | 30% | 100 |
| 절 복잡성 | 15% | 50 |
| 함수/표현식 | 20% | 80 |
| 쿼리 메트릭 | 10% | 40 |
| DBMS 특화 | 25% | 100 |
| **합계** | **100%** | **370** |

### 복잡도 등급

| 점수 | 등급 | 설명 |
|------|------|------|
| 0-2 | 매우 단순 | 단순 CRUD |
| 2-4 | 단순 | 기본 JOIN/조건 |
| 4-6 | 보통 | 복합 JOIN, 서브쿼리 |
| 6-8 | 복잡 | 다중 서브쿼리, 윈도우 함수 |
| 8-10 | 매우 복잡 | 계층 쿼리, 동적 SQL |
