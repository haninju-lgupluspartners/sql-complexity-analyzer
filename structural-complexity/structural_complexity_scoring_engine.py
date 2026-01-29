#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL Structural Complexity Scoring Engine

SQL 자체의 구조적 복잡도를 측정하는 스코어링 엔진입니다.
YML 룰 파일을 읽어서 각 SQL 쿼리의 구조적 복잡도를 산출합니다.

Usage:
    python3 structural_complexity_scoring_engine.py \
        --source-db ORA \
        --input file1.json file2.json \
        --output result.json

Author: SQL Structural Complexity Scoring Engine
Version: 1.0.0
"""

import argparse
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RuleMatch:
    """룰 매칭 결과"""
    rule_id: str
    rule_name: str
    weight: int
    category: str
    subcategory: str
    match_count: int = 1
    matched_patterns: List[str] = field(default_factory=list)


@dataclass
class QueryScore:
    """쿼리별 스코어 결과"""
    query_name: str
    sql: str
    raw_score: float
    normalized_score: float  # 0-10 정규화 점수
    complexity_level: str
    matched_rules: List[RuleMatch] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileScore:
    """파일별 스코어 결과"""
    file_name: str
    file_path: str
    query_count: int
    total_raw_score: float
    avg_score: float
    avg_normalized_score: float
    complexity_distribution: Dict[str, int] = field(default_factory=dict)
    queries: List[QueryScore] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """전체 분석 결과"""
    metadata: Dict[str, Any]
    summary: Dict[str, Any]
    files: List[FileScore] = field(default_factory=list)
    rule_statistics: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# Scoring Engine
# =============================================================================

class SQLStructuralScoringEngine:
    """SQL 구조적 복잡도 스코어링 엔진"""
    
    # 복잡도 레벨 정의 (0-10 정규화 점수 기준)
    COMPLEXITY_LEVELS = [
        {'level': '매우 단순', 'min': 0, 'max': 2, 'description': '단순 CRUD'},
        {'level': '단순', 'min': 2, 'max': 4, 'description': '기본 JOIN/조건'},
        {'level': '보통', 'min': 4, 'max': 6, 'description': '복합 JOIN, 서브쿼리'},
        {'level': '복잡', 'min': 6, 'max': 8, 'description': '다중 서브쿼리, 윈도우 함수'},
        {'level': '매우 복잡', 'min': 8, 'max': 10, 'description': '계층 쿼리, 동적 SQL'}
    ]
    
    # 카테고리별 가중치 (합계 100%)
    CATEGORY_WEIGHTS = {
        'structural': 0.30,      # 구조적 복잡성 30%
        'clause': 0.15,          # 절 복잡성 15%
        'function_expression': 0.20,  # 함수/표현식 20%
        'query_metric': 0.10,    # 쿼리 메트릭 10%
        'dbms_specific': 0.25    # DBMS 특화 25%
    }
    
    # 카테고리별 최대 점수
    CATEGORY_MAX_SCORES = {
        'structural': 100,
        'clause': 50,
        'function_expression': 80,
        'query_metric': 40,
        'dbms_specific': 100
    }
    
    # 지원 DBMS 매핑
    DB_ALIASES = {
        'ORA': ['ORA', 'ORACLE'],
        'MY': ['MY', 'MYSQL'],
        'MDB': ['MDB', 'MARIADB'],
        'PG': ['PG', 'POSTGRESQL', 'POSTGRES'],
        'SS': ['SS', 'SQLSERVER', 'MSSQL'],
        'ALT': ['ALT', 'ALTIBASE'],
        'DB2': ['DB2', 'IBM DB2']
    }
    
    def __init__(self, rules_path: str, source_db: str):
        """
        Args:
            rules_path: YML 룰 파일 경로
            source_db: Source DBMS 종류 (ORA, MY, MDB, PG, SS, ALT, DB2)
        """
        self.rules_path = rules_path
        self.source_db = self._normalize_db_name(source_db)
        self.rules = self._load_rules()
        self.common_rules = self._compile_common_rules()
        self.dbms_rules = self._compile_dbms_rules()
        self.rule_match_counts = defaultdict(int)
        
    def _normalize_db_name(self, db_name: str) -> str:
        """DB 이름 정규화"""
        db_upper = db_name.upper()
        for canonical, aliases in self.DB_ALIASES.items():
            if db_upper in aliases:
                return canonical
        return db_upper
    
    def _load_rules(self) -> Dict:
        """YML 룰 파일 로드"""
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _compile_common_rules(self) -> List[Dict]:
        """공통 룰 컴파일"""
        compiled = []
        common_rules = self.rules.get('common_rules', {})
        
        for category_name, rules_list in common_rules.items():
            if not isinstance(rules_list, list):
                continue
            
            # 카테고리 매핑
            category = self._map_category(category_name)
            
            for rule in rules_list:
                compiled_rule = self._compile_rule(rule, category, category_name)
                if compiled_rule:
                    compiled.append(compiled_rule)
        
        return compiled
    
    def _compile_dbms_rules(self) -> List[Dict]:
        """DBMS별 룰 컴파일 (source_db에 해당하는 것만)"""
        compiled = []
        dbms_rules = self.rules.get('dbms_specific_rules', {})
        
        # source_db에 해당하는 룰만 로드 (대소문자 모두 시도)
        db_keys = [self.source_db, self.source_db.lower(), self.source_db.upper()]
        
        for db_key in db_keys:
            if db_key in dbms_rules:
                rules_list = dbms_rules[db_key]
                if isinstance(rules_list, list):
                    for rule in rules_list:
                        compiled_rule = self._compile_rule(rule, 'dbms_specific', db_key)
                        if compiled_rule:
                            compiled.append(compiled_rule)
                break
        
        return compiled
    
    def _map_category(self, category_name: str) -> str:
        """카테고리 이름을 표준 카테고리로 매핑"""
        category_mapping = {
            'structural_join': 'structural',
            'structural_subquery': 'structural',
            'structural_cte': 'structural',
            'structural_set_operation': 'structural',
            'clause_select': 'clause',
            'clause_where': 'clause',
            'clause_group_order': 'clause',
            'function_aggregate': 'function_expression',
            'function_window': 'function_expression',
            'function_case': 'function_expression',
            'function_common': 'function_expression',
            'query_metric': 'query_metric'
        }
        return category_mapping.get(category_name, 'structural')
    
    def _compile_rule(self, rule: Dict, category: str, subcategory: str) -> Optional[Dict]:
        """단일 룰 컴파일"""
        compiled_rule = {
            'id': rule.get('id', ''),
            'name': rule.get('name', ''),
            'weight': rule.get('weight', 0),
            'detection_method': rule.get('detection_method', 'regex'),
            'pattern': rule.get('pattern', ''),
            'logic': rule.get('logic', ''),
            'category': category,
            'subcategory': subcategory,
            'note': rule.get('note', '')
        }
        
        # 정규식 패턴 컴파일
        if compiled_rule['detection_method'] == 'regex' and compiled_rule['pattern']:
            try:
                compiled_rule['compiled_pattern'] = re.compile(
                    compiled_rule['pattern'], 
                    re.IGNORECASE | re.DOTALL
                )
            except re.error as e:
                print(f"Warning: Invalid regex pattern for rule {rule.get('id')}: {e}")
                compiled_rule['compiled_pattern'] = None
        elif compiled_rule['detection_method'] == 'keyword' and compiled_rule['pattern']:
            try:
                compiled_rule['compiled_pattern'] = re.compile(
                    r'\b' + re.escape(compiled_rule['pattern']) + r'\b',
                    re.IGNORECASE
                )
            except re.error:
                compiled_rule['compiled_pattern'] = None
        else:
            compiled_rule['compiled_pattern'] = None
        
        return compiled_rule
    
    def _preprocess_sql(self, sql: str) -> str:
        """SQL 전처리 (MyBatis 태그 제거 등)"""
        # MyBatis 동적 SQL 태그 제거
        sql = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', sql, flags=re.DOTALL)
        sql = re.sub(r'<(if|choose|when|otherwise|foreach|where|set|trim)[^>]*>', ' ', sql, flags=re.IGNORECASE)
        sql = re.sub(r'</(if|choose|when|otherwise|foreach|where|set|trim)>', ' ', sql, flags=re.IGNORECASE)
        
        # MyBatis 파라미터 치환
        sql = re.sub(r'#\{[^}]+\}', '?', sql)
        sql = re.sub(r'\$\{[^}]+\}', '?', sql)
        
        # 연속 공백 정리
        sql = re.sub(r'\s+', ' ', sql).strip()
        
        return sql
    
    def _count_pattern_matches(self, sql: str, pattern: re.Pattern) -> Tuple[int, List[str]]:
        """패턴 매칭 횟수와 매칭된 문자열 반환"""
        matches = pattern.findall(sql)
        if isinstance(matches, list) and matches:
            if isinstance(matches[0], tuple):
                matched_strings = [m[0] if m[0] else str(m) for m in matches]
            else:
                matched_strings = matches
            return len(matches), matched_strings[:5]
        return 0, []
    
    def _calculate_metrics(self, sql: str) -> Dict[str, Any]:
        """SQL 메트릭 계산"""
        metrics = {}
        
        # 길이
        metrics['length'] = len(sql)
        
        # JOIN 카운트
        join_pattern = re.compile(r'\bJOIN\b', re.IGNORECASE)
        metrics['join_count'] = len(join_pattern.findall(sql))
        
        # 서브쿼리 깊이 (순차 스캔 방식)
        max_depth = 0
        current_depth = 0
        sql_upper = sql.upper()
        i = 0
        while i < len(sql):
            # (SELECT 패턴 발견 시 깊이 증가
            if sql[i] == '(' and sql_upper[i:i+10].startswith('(SELECT'):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            # ) 발견 시 서브쿼리 내부라면 깊이 감소
            elif sql[i] == ')' and current_depth > 0:
                current_depth -= 1
            i += 1
        metrics['subquery_depth'] = min(max_depth, 5)
        
        # 테이블 수 추정 (개선된 로직)
        # - 콤마로 구분된 테이블 지원
        # - 스키마.테이블 형식에서 실제 테이블명 추출
        # - SQL 키워드(LATERAL 등) 필터링
        tables = set()
        sql_keywords = {
            'LATERAL', 'NATURAL', 'OUTER', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS',
            'SELECT', 'WHERE', 'AND', 'OR', 'ON', 'AS', 'SET', 'VALUES', 'INTO'
        }
        
        # FROM 절 처리 (콤마로 구분된 테이블 포함)
        from_pattern = re.compile(
            r'\bFROM\s+(?!\s*\()([\w.]+(?:\s+\w+)?(?:\s*,\s*[\w.]+(?:\s+\w+)?)*)',
            re.IGNORECASE
        )
        for match in from_pattern.finditer(sql):
            from_clause = match.group(1)
            table_parts = from_clause.split(',')
            for part in table_parts:
                part = part.strip()
                if part:
                    tokens = part.split()
                    if tokens:
                        table_name = tokens[0]
                        if '.' in table_name:
                            table_name = table_name.split('.')[-1]
                        if table_name.upper() not in sql_keywords:
                            tables.add(table_name.upper())
        
        # JOIN 절 처리 (LATERAL 등 키워드 제외)
        join_pattern = re.compile(
            r'\bJOIN\s+(?!LATERAL\b)(?!\s*\()([\w.]+)',
            re.IGNORECASE
        )
        for match in join_pattern.finditer(sql):
            table_name = match.group(1)
            if '.' in table_name:
                table_name = table_name.split('.')[-1]
            if table_name.upper() not in sql_keywords:
                tables.add(table_name.upper())
        
        # LATERAL 서브쿼리 내부 테이블 추출
        lateral_pattern = re.compile(r'\bLATERAL\s*\(([^)]+)\)', re.IGNORECASE)
        for match in lateral_pattern.finditer(sql):
            inner_sql = match.group(1)
            inner_from = re.findall(r'\bFROM\s+([\w.]+)', inner_sql, re.IGNORECASE)
            for table_name in inner_from:
                if '.' in table_name:
                    table_name = table_name.split('.')[-1]
                if table_name.upper() not in sql_keywords:
                    tables.add(table_name.upper())
        
        metrics['table_count'] = len(tables)
        
        # SELECT 컬럼 수 추정 (개선된 로직)
        # - 순차 스캔으로 최상위 레벨의 FROM 찾기 (서브쿼리 내 FROM 무시)
        # - SELECT * 검사 개선 (단독 * 또는 table.* 만)
        # - 괄호 내 콤마 무시
        sql_upper = sql.upper()
        select_start = sql_upper.find('SELECT')
        
        if select_start == -1:
            metrics['select_column_count'] = 0
        else:
            # SELECT 뒤부터 순차 스캔으로 최상위 레벨의 FROM 찾기
            start_pos = select_start + 6  # len('SELECT')
            depth = 0
            from_pos = -1
            i = start_pos
            
            while i < len(sql) - 3:
                char = sql[i]
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                elif depth == 0 and sql_upper[i:i+4] == 'FROM':
                    # 단어 경계 확인
                    before_ok = i == 0 or not sql[i-1].isalnum()
                    after_ok = i + 4 >= len(sql) or not sql[i+4].isalnum()
                    if before_ok and after_ok:
                        from_pos = i
                        break
                i += 1
            
            if from_pos == -1:
                metrics['select_column_count'] = 0
            else:
                select_clause = sql[start_pos:from_pos].strip()
                # DISTINCT 제거
                select_clause_clean = re.sub(r'^\s*(ALL\s+)?DISTINCT\s+', '', select_clause, flags=re.IGNORECASE)
                
                # SELECT * 검사 (단독 * 또는 table.* 만)
                if re.match(r'^\s*\*\s*$', select_clause_clean):
                    metrics['select_column_count'] = -1
                elif re.match(r'^\s*\w+\.\*\s*$', select_clause_clean):
                    metrics['select_column_count'] = -1
                else:
                    # 괄호 내용을 플레이스홀더로 치환하여 내부 콤마 무시
                    processed = select_clause_clean
                    for _ in range(50):  # 무한루프 방지
                        match = re.search(r'\([^()]*\)', processed)
                        if not match:
                            break
                        processed = processed[:match.start()] + '__PH__' + processed[match.end():]
                    
                    metrics['select_column_count'] = processed.count(',') + 1
        
        # WHERE 조건 수 (서브쿼리 제외, 순차 스캔 방식)
        sql_upper = sql.upper()
        where_start = sql_upper.find('WHERE')
        if where_start == -1:
            metrics['where_condition_count'] = 0
        else:
            # WHERE 종료 위치 찾기
            end_keywords = ['GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT']
            where_end = len(sql)
            for keyword in end_keywords:
                pos = sql_upper.find(keyword, where_start)
                if pos != -1 and pos < where_end:
                    where_end = pos
            
            where_clause = sql[where_start + 5:where_end]
            where_upper = where_clause.upper()
            
            # 서브쿼리 깊이 추적하며 AND/OR 카운트
            and_or_count = 0
            subquery_depth = 0
            i = 0
            while i < len(where_clause):
                if where_clause[i] == '(':
                    # ( 이후 공백 건너뛰고 SELECT 확인
                    j = i + 1
                    while j < len(where_clause) and where_clause[j] in ' \t\n':
                        j += 1
                    if where_upper[j:j+6] == 'SELECT':
                        subquery_depth += 1
                elif where_clause[i] == ')' and subquery_depth > 0:
                    subquery_depth -= 1
                elif subquery_depth == 0:
                    if where_upper[i:i+4] == 'AND ' or where_upper[i:i+3] == 'OR ':
                        and_or_count += 1
                i += 1
            
            metrics['where_condition_count'] = and_or_count + 1 if where_clause.strip() else 0
        
        return metrics
    
    def _apply_metric_rules(self, metrics: Dict[str, Any]) -> List[RuleMatch]:
        """메트릭 기반 룰 적용"""
        matched_rules = []
        
        # 길이 기반 점수
        length = metrics.get('length', 0)
        if length < 200:
            matched_rules.append(RuleMatch('c_len_short', '짧은 쿼리', 0, 'query_metric', 'length'))
        elif length < 500:
            matched_rules.append(RuleMatch('c_len_medium', '중간 쿼리', 5, 'query_metric', 'length'))
        elif length < 1000:
            matched_rules.append(RuleMatch('c_len_long', '긴 쿼리', 10, 'query_metric', 'length'))
        elif length < 2000:
            matched_rules.append(RuleMatch('c_len_very_long', '매우 긴 쿼리', 15, 'query_metric', 'length'))
        else:
            matched_rules.append(RuleMatch('c_len_huge', '초대형 쿼리', 20, 'query_metric', 'length'))
        
        # JOIN 카운트 기반 점수
        join_count = metrics.get('join_count', 0)
        if join_count == 0:
            matched_rules.append(RuleMatch('c_join_0', 'JOIN 없음', 0, 'structural', 'join'))
        elif join_count == 1:
            matched_rules.append(RuleMatch('c_join_1', 'JOIN 1개', 5, 'structural', 'join'))
        elif join_count <= 3:
            matched_rules.append(RuleMatch('c_join_2_3', 'JOIN 2-3개', 10, 'structural', 'join'))
        elif join_count <= 5:
            matched_rules.append(RuleMatch('c_join_4_5', 'JOIN 4-5개', 15, 'structural', 'join'))
        else:
            matched_rules.append(RuleMatch('c_join_6plus', 'JOIN 6개 이상', 20, 'structural', 'join'))
        
        # 서브쿼리 깊이 기반 점수
        subquery_depth = metrics.get('subquery_depth', 0)
        if subquery_depth == 0:
            matched_rules.append(RuleMatch('c_subq_0', '서브쿼리 없음', 0, 'structural', 'subquery'))
        elif subquery_depth == 1:
            matched_rules.append(RuleMatch('c_subq_depth_1', '서브쿼리 깊이 1', 10, 'structural', 'subquery'))
        elif subquery_depth == 2:
            matched_rules.append(RuleMatch('c_subq_depth_2', '서브쿼리 깊이 2', 20, 'structural', 'subquery'))
        else:
            matched_rules.append(RuleMatch('c_subq_depth_3plus', '서브쿼리 깊이 3+', 30, 'structural', 'subquery'))
        
        # 테이블 수 기반 점수
        table_count = metrics.get('table_count', 0)
        if 3 <= table_count <= 5:
            matched_rules.append(RuleMatch('c_tables_3_5', '테이블 3-5개', 5, 'query_metric', 'tables'))
        elif 6 <= table_count <= 10:
            matched_rules.append(RuleMatch('c_tables_6_10', '테이블 6-10개', 10, 'query_metric', 'tables'))
        elif table_count >= 11:
            matched_rules.append(RuleMatch('c_tables_11plus', '테이블 11개 이상', 15, 'query_metric', 'tables'))
        
        # SELECT 컬럼 수 기반 점수
        col_count = metrics.get('select_column_count', 0)
        if col_count == -1:
            matched_rules.append(RuleMatch('c_select_star', 'SELECT *', 5, 'clause', 'select'))
        elif 6 <= col_count <= 10:
            matched_rules.append(RuleMatch('c_select_cols_6_10', '컬럼 6-10개', 5, 'clause', 'select'))
        elif 11 <= col_count <= 20:
            matched_rules.append(RuleMatch('c_select_cols_11_20', '컬럼 11-20개', 10, 'clause', 'select'))
        elif col_count >= 21:
            matched_rules.append(RuleMatch('c_select_cols_21plus', '컬럼 21개 이상', 15, 'clause', 'select'))
        
        # WHERE 조건 수 기반 점수
        cond_count = metrics.get('where_condition_count', 0)
        if 4 <= cond_count <= 6:
            matched_rules.append(RuleMatch('c_where_cond_4_6', '조건 4-6개', 5, 'clause', 'where'))
        elif 7 <= cond_count <= 10:
            matched_rules.append(RuleMatch('c_where_cond_7_10', '조건 7-10개', 10, 'clause', 'where'))
        elif cond_count >= 11:
            matched_rules.append(RuleMatch('c_where_cond_11plus', '조건 11개 이상', 15, 'clause', 'where'))
        
        return matched_rules

    def score_query(self, sql: str, query_name: str = '') -> QueryScore:
        """단일 쿼리 스코어링"""
        preprocessed_sql = self._preprocess_sql(sql)
        matched_rules = []
        category_scores = defaultdict(float)
        
        # 메트릭 계산
        metrics = self._calculate_metrics(preprocessed_sql)
        
        # 메트릭 기반 룰 적용
        metric_rules = self._apply_metric_rules(metrics)
        matched_rules.extend(metric_rules)
        
        # 공통 룰 적용 (regex/keyword 기반)
        for rule in self.common_rules:
            if rule['compiled_pattern'] is None:
                continue
            
            match_count, matched_patterns = self._count_pattern_matches(
                preprocessed_sql, 
                rule['compiled_pattern']
            )
            
            if match_count > 0:
                rule_match = RuleMatch(
                    rule_id=rule['id'],
                    rule_name=rule['name'],
                    weight=rule['weight'],
                    category=rule['category'],
                    subcategory=rule['subcategory'],
                    match_count=match_count,
                    matched_patterns=matched_patterns
                )
                matched_rules.append(rule_match)
                self.rule_match_counts[rule['id']] += match_count
        
        # DBMS 특화 룰 적용
        for rule in self.dbms_rules:
            if rule['compiled_pattern'] is None:
                continue
            
            match_count, matched_patterns = self._count_pattern_matches(
                preprocessed_sql, 
                rule['compiled_pattern']
            )
            
            if match_count > 0:
                rule_match = RuleMatch(
                    rule_id=rule['id'],
                    rule_name=rule['name'],
                    weight=rule['weight'],
                    category=rule['category'],
                    subcategory=rule['subcategory'],
                    match_count=match_count,
                    matched_patterns=matched_patterns
                )
                matched_rules.append(rule_match)
                self.rule_match_counts[rule['id']] += match_count
        
        # 카테고리별 점수 계산
        for rule_match in matched_rules:
            category = rule_match.category
            score = rule_match.weight * rule_match.match_count
            category_scores[category] += score
        
        # Raw 점수 계산
        raw_score = sum(r.weight * r.match_count for r in matched_rules)
        
        # 정규화 점수 계산 (0-10)
        normalized_score = self._calculate_normalized_score(dict(category_scores))
        
        # 복잡도 레벨 결정
        complexity_level = self._get_complexity_level(normalized_score)
        
        return QueryScore(
            query_name=query_name,
            sql=sql[:500] + '...' if len(sql) > 500 else sql,
            raw_score=raw_score,
            normalized_score=round(normalized_score, 2),
            complexity_level=complexity_level,
            matched_rules=matched_rules,
            category_scores=dict(category_scores),
            metrics=metrics
        )
    
    def _calculate_normalized_score(self, category_scores: Dict[str, float]) -> float:
        """카테고리별 점수를 0-10 정규화 점수로 변환"""
        weighted_sum = 0.0
        
        for category, weight in self.CATEGORY_WEIGHTS.items():
            raw_score = category_scores.get(category, 0)
            max_score = self.CATEGORY_MAX_SCORES.get(category, 100)
            
            # 카테고리별 정규화 (0-10)
            normalized = min(raw_score / max_score * 10, 10)
            weighted_sum += normalized * weight
        
        return weighted_sum
    
    def _get_complexity_level(self, score: float) -> str:
        """점수에 따른 복잡도 레벨 반환"""
        for level in self.COMPLEXITY_LEVELS:
            if level['min'] <= score < level['max']:
                return level['level']
        return '매우 복잡'
    
    def analyze_file(self, file_data: Dict) -> FileScore:
        """파일 단위 분석"""
        queries = file_data.get('queries', [])
        query_scores = []
        complexity_dist = defaultdict(int)
        
        for query in queries:
            query_name = query.get('name', query.get('type', 'unknown'))
            sql = query.get('sql', '')
            
            if not sql:
                continue
            
            score = self.score_query(sql, query_name)
            query_scores.append(score)
            complexity_dist[score.complexity_level] += 1
        
        total_raw = sum(q.raw_score for q in query_scores)
        avg_score = total_raw / len(query_scores) if query_scores else 0
        avg_normalized = sum(q.normalized_score for q in query_scores) / len(query_scores) if query_scores else 0
        
        return FileScore(
            file_name=file_data.get('file_name', ''),
            file_path=file_data.get('file_path', ''),
            query_count=len(query_scores),
            total_raw_score=round(total_raw, 2),
            avg_score=round(avg_score, 2),
            avg_normalized_score=round(avg_normalized, 2),
            complexity_distribution=dict(complexity_dist),
            queries=query_scores
        )
    
    def analyze_json_files(self, json_paths: List[str]) -> AnalysisResult:
        """여러 JSON 파일 분석"""
        all_files = []
        total_queries = 0
        total_score = 0
        total_normalized = 0
        overall_complexity_dist = defaultdict(int)
        
        for json_path in json_paths:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            files = data.get('files', [])
            for file_data in files:
                file_score = self.analyze_file(file_data)
                all_files.append(file_score)
                total_queries += file_score.query_count
                total_score += file_score.total_raw_score
                total_normalized += file_score.avg_normalized_score * file_score.query_count
                
                for level, count in file_score.complexity_distribution.items():
                    overall_complexity_dist[level] += count
        
        # 메타데이터
        metadata = {
            'analysis_date': datetime.now().isoformat(),
            'source_db': self.source_db,
            'rules_file': self.rules_path,
            'input_files': json_paths,
            'total_files_analyzed': len(all_files),
            'total_queries_analyzed': total_queries
        }
        
        # 요약
        avg_score = total_score / total_queries if total_queries > 0 else 0
        avg_normalized = total_normalized / total_queries if total_queries > 0 else 0
        summary = {
            'total_queries': total_queries,
            'total_raw_score': round(total_score, 2),
            'average_raw_score': round(avg_score, 2),
            'average_normalized_score': round(avg_normalized, 2),
            'overall_complexity_level': self._get_complexity_level(avg_normalized),
            'complexity_distribution': dict(overall_complexity_dist)
        }
        
        # 룰 통계 (상위 20개)
        sorted_rules = sorted(
            self.rule_match_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:20]
        
        return AnalysisResult(
            metadata=metadata,
            summary=summary,
            files=all_files,
            rule_statistics=dict(sorted_rules)
        )


# =============================================================================
# Report Generator
# =============================================================================

class ReportGenerator:
    """분석 결과 리포트 생성기"""
    
    @staticmethod
    def to_json(result: AnalysisResult, output_path: str):
        """JSON 형식으로 저장"""
        def convert_dataclass(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return asdict(obj)
            elif isinstance(obj, list):
                return [convert_dataclass(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_dataclass(v) for k, v in obj.items()}
            return obj
        
        output_data = convert_dataclass(result)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"JSON report saved to: {output_path}")
    
    @staticmethod
    def to_markdown(result: AnalysisResult, output_path: str):
        """Markdown 형식으로 저장"""
        lines = []
        
        # 헤더
        lines.append("# SQL 구조적 복잡도 분석 리포트")
        lines.append("")
        lines.append(f"**분석 일시**: {result.metadata['analysis_date']}")
        lines.append(f"**Source DB**: {result.metadata['source_db']}")
        lines.append(f"**분석 파일 수**: {result.metadata['total_files_analyzed']}")
        lines.append(f"**분석 쿼리 수**: {result.metadata['total_queries_analyzed']}")
        lines.append("")
        
        # 요약
        lines.append("## 요약")
        lines.append("")
        lines.append(f"| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 총 쿼리 수 | {result.summary['total_queries']} |")
        lines.append(f"| 총 Raw 점수 | {result.summary['total_raw_score']} |")
        lines.append(f"| 평균 Raw 점수 | {result.summary['average_raw_score']} |")
        lines.append(f"| 평균 정규화 점수 (0-10) | {result.summary['average_normalized_score']} |")
        lines.append(f"| 전체 복잡도 | {result.summary['overall_complexity_level']} |")
        lines.append("")
        
        # 복잡도 분포
        lines.append("### 복잡도 분포")
        lines.append("")
        lines.append("| 복잡도 | 쿼리 수 | 비율 |")
        lines.append("|--------|---------|------|")
        total = result.summary['total_queries']
        for level in ['매우 단순', '단순', '보통', '복잡', '매우 복잡']:
            count = result.summary['complexity_distribution'].get(level, 0)
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"| {level} | {count} | {pct:.1f}% |")
        lines.append("")
        
        # 자주 매칭된 룰
        if result.rule_statistics:
            lines.append("### 자주 매칭된 룰 (Top 20)")
            lines.append("")
            lines.append("| 룰 ID | 매칭 횟수 |")
            lines.append("|-------|----------|")
            for rule_id, count in result.rule_statistics.items():
                lines.append(f"| {rule_id} | {count} |")
            lines.append("")
        
        # 파일별 상세
        lines.append("## 파일별 분석 결과")
        lines.append("")
        
        for file_score in result.files:
            lines.append(f"### {file_score.file_name}")
            lines.append("")
            lines.append(f"- **경로**: `{file_score.file_path}`")
            lines.append(f"- **쿼리 수**: {file_score.query_count}")
            lines.append(f"- **총 Raw 점수**: {file_score.total_raw_score}")
            lines.append(f"- **평균 정규화 점수**: {file_score.avg_normalized_score}")
            lines.append("")
            
            # 쿼리별 상세 (복잡도 높은 순)
            sorted_queries = sorted(
                file_score.queries, 
                key=lambda x: x.normalized_score, 
                reverse=True
            )
            
            lines.append("| 쿼리명 | Raw 점수 | 정규화 점수 | 복잡도 |")
            lines.append("|--------|----------|-------------|--------|")
            
            for q in sorted_queries[:20]:
                lines.append(
                    f"| {q.query_name[:30]} | {q.raw_score} | {q.normalized_score} | {q.complexity_level} |"
                )
            
            if len(sorted_queries) > 20:
                lines.append(f"| ... ({len(sorted_queries) - 20}개 더) | | | |")
            
            lines.append("")
        
        # 고복잡도 쿼리 목록
        lines.append("## 고복잡도 쿼리 목록 (정규화 점수 >= 6)")
        lines.append("")
        
        high_complexity_queries = []
        for file_score in result.files:
            for q in file_score.queries:
                if q.normalized_score >= 6:
                    high_complexity_queries.append({
                        'file': file_score.file_name,
                        'query': q
                    })
        
        high_complexity_queries.sort(key=lambda x: x['query'].normalized_score, reverse=True)
        
        if high_complexity_queries:
            lines.append("| 파일 | 쿼리명 | 정규화 점수 | 복잡도 | 주요 매칭 룰 |")
            lines.append("|------|--------|-------------|--------|-------------|")
            
            for item in high_complexity_queries[:50]:
                q = item['query']
                top_rules = sorted(q.matched_rules, key=lambda r: r.weight * r.match_count, reverse=True)[:3]
                rule_names = ', '.join([r.rule_name for r in top_rules])
                lines.append(
                    f"| {item['file'][:20]} | {q.query_name[:25]} | {q.normalized_score} | "
                    f"{q.complexity_level} | {rule_names[:40]} |"
                )
            lines.append("")
        else:
            lines.append("고복잡도 쿼리가 없습니다.")
            lines.append("")
        
        # 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"Markdown report saved to: {output_path}")
    
    @staticmethod
    def to_csv(result: AnalysisResult, output_path: str):
        """CSV 형식으로 저장 (쿼리별 상세)"""
        import csv
        
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                'File', 'Query Name', 'Raw Score', 'Normalized Score', 
                'Complexity Level', 'Join Count', 'Subquery Depth', 
                'Table Count', 'SQL Length', 'Matched Rules Count', 'Top Rules'
            ])
            
            # 데이터
            for file_score in result.files:
                for q in file_score.queries:
                    top_rules = sorted(
                        q.matched_rules, 
                        key=lambda r: r.weight * r.match_count, 
                        reverse=True
                    )[:5]
                    top_rule_names = '; '.join([f"{r.rule_name}({r.match_count})" for r in top_rules])
                    
                    writer.writerow([
                        file_score.file_name,
                        q.query_name,
                        q.raw_score,
                        q.normalized_score,
                        q.complexity_level,
                        q.metrics.get('join_count', 0),
                        q.metrics.get('subquery_depth', 0),
                        q.metrics.get('table_count', 0),
                        q.metrics.get('length', 0),
                        len(q.matched_rules),
                        top_rule_names
                    ])
        
        print(f"CSV report saved to: {output_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='SQL Structural Complexity Scoring Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Oracle 쿼리 분석
  python3 structural_complexity_scoring_engine.py \\
      --source-db ORA \\
      --input queries.json \\
      --output result

  # 여러 파일 분석
  python3 structural_complexity_scoring_engine.py \\
      --source-db MY \\
      --input file1.json file2.json \\
      --output analysis_result

Supported DBMS:
  ORA (Oracle), MY (MySQL), MDB (MariaDB), PG (PostgreSQL),
  SS (SQL Server), ALT (Altibase), DB2 (IBM DB2)

Complexity Levels (0-10 normalized score):
  0-2: 매우 단순 (단순 CRUD)
  2-4: 단순 (기본 JOIN/조건)
  4-6: 보통 (복합 JOIN, 서브쿼리)
  6-8: 복잡 (다중 서브쿼리, 윈도우 함수)
  8-10: 매우 복잡 (계층 쿼리, 동적 SQL)
        """
    )
    
    parser.add_argument(
        '--source-db', '-s',
        required=True,
        help='Source DBMS type (ORA, MY, MDB, PG, SS, ALT, DB2)'
    )
    
    parser.add_argument(
        '--input', '-i',
        nargs='+',
        required=True,
        help='Input JSON file(s) containing SQL queries'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='structural_analysis_result',
        help='Output file base name (without extension)'
    )
    
    parser.add_argument(
        '--rules', '-r',
        default=None,
        help='Path to rules YAML file (default: auto-detect)'
    )
    
    parser.add_argument(
        '--format', '-f',
        nargs='+',
        default=['json', 'md', 'csv'],
        choices=['json', 'md', 'csv'],
        help='Output format(s): json, md, csv (default: all)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # 룰 파일 경로 결정
    if args.rules:
        rules_path = args.rules
    else:
        # 스크립트 위치 기준으로 룰 파일 찾기 (같은 디렉토리)
        script_dir = Path(__file__).parent
        rules_path = script_dir / 'structural-complexity-rules.yml'
        
        if not rules_path.exists():
            # 현재 디렉토리에서 찾기
            rules_path = Path('structural-complexity-rules.yml')
        
        if not rules_path.exists():
            print(f"Error: Rules file not found. Please specify with --rules option.")
            sys.exit(1)
    
    rules_path = str(rules_path)
    
    # 입력 파일 확인
    for input_file in args.input:
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            sys.exit(1)
    
    if args.verbose:
        print(f"Source DB: {args.source_db}")
        print(f"Rules file: {rules_path}")
        print(f"Input files: {args.input}")
        print(f"Output formats: {args.format}")
        print()
    
    # 스코어링 엔진 초기화
    print("Initializing scoring engine...")
    engine = SQLStructuralScoringEngine(rules_path, args.source_db)
    print(f"Loaded {len(engine.common_rules)} common rules and {len(engine.dbms_rules)} DBMS-specific rules for {engine.source_db}")
    print()
    
    # 분석 실행
    print("Analyzing SQL queries...")
    result = engine.analyze_json_files(args.input)
    print(f"Analyzed {result.summary['total_queries']} queries from {len(result.files)} files")
    print()
    
    # 결과 요약 출력
    print("=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total Queries: {result.summary['total_queries']}")
    print(f"Total Raw Score: {result.summary['total_raw_score']}")
    print(f"Average Raw Score: {result.summary['average_raw_score']}")
    print(f"Average Normalized Score (0-10): {result.summary['average_normalized_score']}")
    print(f"Overall Complexity: {result.summary['overall_complexity_level']}")
    print()
    print("Complexity Distribution:")
    for level in ['매우 단순', '단순', '보통', '복잡', '매우 복잡']:
        count = result.summary['complexity_distribution'].get(level, 0)
        total = result.summary['total_queries']
        pct = (count / total * 100) if total > 0 else 0
        bar = '█' * int(pct / 5)
        print(f"  {level:10s}: {count:4d} ({pct:5.1f}%) {bar}")
    print("=" * 60)
    print()
    
    # 결과 저장
    output_base = args.output
    
    if 'json' in args.format:
        ReportGenerator.to_json(result, f"{output_base}.json")
    
    if 'md' in args.format:
        ReportGenerator.to_markdown(result, f"{output_base}.md")
    
    if 'csv' in args.format:
        ReportGenerator.to_csv(result, f"{output_base}.csv")
    
    print()
    print("Analysis complete!")


if __name__ == '__main__':
    main()
