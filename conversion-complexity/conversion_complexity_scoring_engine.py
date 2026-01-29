#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL Conversion Complexity Scoring Engine

SQL 변환 복잡도를 측정하는 스코어링 엔진입니다.
YML 룰 파일을 읽어서 각 SQL 쿼리의 변환 복잡도를 산출합니다.

Usage:
    python3 sql_conversion_scoring_engine.py \
        --source-db MY \
        --input file1.json file2.json \
        --output result.json

Author: SQL Conversion Scoring Engine
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
    conversion_grade: str
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
    weighted_score: float
    complexity_level: str
    matched_rules: List[RuleMatch] = field(default_factory=list)
    grade_summary: Dict[str, int] = field(default_factory=dict)
    

@dataclass
class FileScore:
    """파일별 스코어 결과"""
    file_name: str
    file_path: str
    query_count: int
    total_raw_score: float
    total_weighted_score: float
    avg_score: float
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

class SQLConversionScoringEngine:
    """SQL 변환 복잡도 스코어링 엔진"""
    
    # 변환 등급별 계수
    GRADE_COEFFICIENTS = {
        'A': 0.5,   # 자동 변환
        'P': 1.0,   # 부분 자동 변환
        'M': 1.5    # 수동 변환
    }
    
    # 복잡도 레벨 정의
    COMPLEXITY_LEVELS = [
        {'level': '매우 낮음', 'min': 0, 'max': 10},
        {'level': '낮음', 'min': 10, 'max': 30},
        {'level': '중간', 'min': 30, 'max': 60},
        {'level': '높음', 'min': 60, 'max': 100},
        {'level': '매우 높음', 'min': 100, 'max': float('inf')}
    ]
    
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
        self.compiled_patterns = self._compile_patterns()
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
    
    def _compile_patterns(self) -> List[Dict]:
        """정규식 패턴 컴파일 및 플랫 리스트 생성"""
        compiled = []
        rules_section = self.rules.get('rules', {})
        
        for category_name, category_data in rules_section.items():
            if not isinstance(category_data, dict):
                continue
                
            for subcategory_name, rules_list in category_data.items():
                if not isinstance(rules_list, list):
                    continue
                    
                for rule in rules_list:
                    if not self._is_applicable_rule(rule):
                        continue
                    
                    compiled_rule = {
                        'id': rule.get('id', ''),
                        'name': rule.get('name', ''),
                        'weight': rule.get('weight', 0),
                        'conversion_grade': rule.get('conversion_grade', 'P'),
                        'detection_method': rule.get('detection_method', 'regex'),
                        'pattern': rule.get('pattern', ''),
                        'logic': rule.get('logic', ''),
                        'category': category_name,
                        'subcategory': subcategory_name,
                        'group': rule.get('group', ''),
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
                        # 키워드는 단어 경계로 검색
                        try:
                            compiled_rule['compiled_pattern'] = re.compile(
                                r'\b' + re.escape(compiled_rule['pattern']) + r'\b',
                                re.IGNORECASE
                            )
                        except re.error:
                            compiled_rule['compiled_pattern'] = None
                    else:
                        compiled_rule['compiled_pattern'] = None
                    
                    compiled.append(compiled_rule)
        
        return compiled
    
    def _is_applicable_rule(self, rule: Dict) -> bool:
        """해당 Source DB에 적용 가능한 룰인지 확인"""
        applicable_db = rule.get('applicable_db', [])
        
        if not applicable_db:
            return False
        
        # ALL인 경우 모든 DB에 적용
        if 'ALL' in applicable_db:
            return True
        
        # Source DB가 목록에 있는지 확인
        return self.source_db in applicable_db
    
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
                # 그룹이 있는 경우
                matched_strings = [m[0] if m[0] else str(m) for m in matches]
            else:
                matched_strings = matches
            return len(matches), matched_strings[:5]  # 최대 5개만 저장
        return 0, []
    
    def score_query(self, sql: str, query_name: str = '') -> QueryScore:
        """단일 쿼리 스코어링"""
        preprocessed_sql = self._preprocess_sql(sql)
        matched_rules = []
        grade_summary = {'A': 0, 'P': 0, 'M': 0}
        
        for rule in self.compiled_patterns:
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
                    conversion_grade=rule['conversion_grade'],
                    category=rule['category'],
                    subcategory=rule['subcategory'],
                    match_count=match_count,
                    matched_patterns=matched_patterns
                )
                matched_rules.append(rule_match)
                
                # 등급별 카운트
                grade = rule['conversion_grade']
                if grade in grade_summary:
                    grade_summary[grade] += match_count
                
                # 전체 룰 매칭 통계
                self.rule_match_counts[rule['id']] += match_count
        
        # 점수 계산
        raw_score = sum(r.weight * r.match_count for r in matched_rules)
        
        # 가중 점수 계산 (변환 등급 계수 적용)
        weighted_score = sum(
            r.weight * r.match_count * self.GRADE_COEFFICIENTS.get(r.conversion_grade, 1.0)
            for r in matched_rules
        )
        
        # 복잡도 레벨 결정
        complexity_level = self._get_complexity_level(weighted_score)
        
        return QueryScore(
            query_name=query_name,
            sql=sql[:500] + '...' if len(sql) > 500 else sql,  # SQL 길이 제한
            raw_score=raw_score,
            weighted_score=round(weighted_score, 2),
            complexity_level=complexity_level,
            matched_rules=matched_rules,
            grade_summary=grade_summary
        )
    
    def _get_complexity_level(self, score: float) -> str:
        """점수에 따른 복잡도 레벨 반환"""
        for level in self.COMPLEXITY_LEVELS:
            if level['min'] <= score < level['max']:
                return level['level']
        return '매우 높음'
    
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
        total_weighted = sum(q.weighted_score for q in query_scores)
        avg_score = total_weighted / len(query_scores) if query_scores else 0
        
        return FileScore(
            file_name=file_data.get('file_name', ''),
            file_path=file_data.get('file_path', ''),
            query_count=len(query_scores),
            total_raw_score=round(total_raw, 2),
            total_weighted_score=round(total_weighted, 2),
            avg_score=round(avg_score, 2),
            complexity_distribution=dict(complexity_dist),
            queries=query_scores
        )
    
    def analyze_json_files(self, json_paths: List[str]) -> AnalysisResult:
        """여러 JSON 파일 분석"""
        all_files = []
        total_queries = 0
        total_score = 0
        overall_complexity_dist = defaultdict(int)
        
        for json_path in json_paths:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            files = data.get('files', [])
            for file_data in files:
                file_score = self.analyze_file(file_data)
                all_files.append(file_score)
                total_queries += file_score.query_count
                total_score += file_score.total_weighted_score
                
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
        summary = {
            'total_queries': total_queries,
            'total_weighted_score': round(total_score, 2),
            'average_score': round(avg_score, 2),
            'overall_complexity_level': self._get_complexity_level(avg_score),
            'complexity_distribution': dict(overall_complexity_dist),
            'grade_distribution': self._calculate_grade_distribution(all_files)
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
    
    def _calculate_grade_distribution(self, files: List[FileScore]) -> Dict[str, int]:
        """전체 등급 분포 계산"""
        grade_dist = {'A': 0, 'P': 0, 'M': 0}
        for file_score in files:
            for query in file_score.queries:
                for grade, count in query.grade_summary.items():
                    if grade in grade_dist:
                        grade_dist[grade] += count
        return grade_dist


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
        lines.append("# SQL 변환 복잡도 분석 리포트")
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
        lines.append(f"| 총 가중 점수 | {result.summary['total_weighted_score']} |")
        lines.append(f"| 평균 점수 | {result.summary['average_score']} |")
        lines.append(f"| 전체 복잡도 | {result.summary['overall_complexity_level']} |")
        lines.append("")
        
        # 복잡도 분포
        lines.append("### 복잡도 분포")
        lines.append("")
        lines.append("| 복잡도 | 쿼리 수 | 비율 |")
        lines.append("|--------|---------|------|")
        total = result.summary['total_queries']
        for level in ['매우 낮음', '낮음', '중간', '높음', '매우 높음']:
            count = result.summary['complexity_distribution'].get(level, 0)
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"| {level} | {count} | {pct:.1f}% |")
        lines.append("")
        
        # 변환 등급 분포
        lines.append("### 변환 등급 분포")
        lines.append("")
        lines.append("| 등급 | 설명 | 매칭 수 |")
        lines.append("|------|------|---------|")
        grade_desc = {'A': '자동 변환', 'P': '부분 자동', 'M': '수동 변환'}
        for grade in ['A', 'P', 'M']:
            count = result.summary['grade_distribution'].get(grade, 0)
            lines.append(f"| {grade} | {grade_desc[grade]} | {count} |")
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
            lines.append(f"- **총 점수**: {file_score.total_weighted_score}")
            lines.append(f"- **평균 점수**: {file_score.avg_score}")
            lines.append("")
            
            # 쿼리별 상세 (복잡도 높은 순)
            sorted_queries = sorted(
                file_score.queries, 
                key=lambda x: x.weighted_score, 
                reverse=True
            )
            
            lines.append("| 쿼리명 | 점수 | 복잡도 | A | P | M |")
            lines.append("|--------|------|--------|---|---|---|")
            
            for q in sorted_queries[:20]:  # 상위 20개만
                lines.append(
                    f"| {q.query_name[:30]} | {q.weighted_score} | {q.complexity_level} | "
                    f"{q.grade_summary.get('A', 0)} | {q.grade_summary.get('P', 0)} | "
                    f"{q.grade_summary.get('M', 0)} |"
                )
            
            if len(sorted_queries) > 20:
                lines.append(f"| ... ({len(sorted_queries) - 20}개 더) | | | | | |")
            
            lines.append("")
        
        # 고복잡도 쿼리 목록
        lines.append("## 고복잡도 쿼리 목록 (점수 >= 50)")
        lines.append("")
        
        high_complexity_queries = []
        for file_score in result.files:
            for q in file_score.queries:
                if q.weighted_score >= 50:
                    high_complexity_queries.append({
                        'file': file_score.file_name,
                        'query': q
                    })
        
        high_complexity_queries.sort(key=lambda x: x['query'].weighted_score, reverse=True)
        
        if high_complexity_queries:
            lines.append("| 파일 | 쿼리명 | 점수 | 복잡도 | 주요 매칭 룰 |")
            lines.append("|------|--------|------|--------|-------------|")
            
            for item in high_complexity_queries[:50]:
                q = item['query']
                top_rules = sorted(q.matched_rules, key=lambda r: r.weight * r.match_count, reverse=True)[:3]
                rule_names = ', '.join([r.rule_name for r in top_rules])
                lines.append(
                    f"| {item['file'][:20]} | {q.query_name[:25]} | {q.weighted_score} | "
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
                'File', 'Query Name', 'Raw Score', 'Weighted Score', 
                'Complexity Level', 'Grade A', 'Grade P', 'Grade M',
                'Matched Rules Count', 'Top Rules'
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
                        q.weighted_score,
                        q.complexity_level,
                        q.grade_summary.get('A', 0),
                        q.grade_summary.get('P', 0),
                        q.grade_summary.get('M', 0),
                        len(q.matched_rules),
                        top_rule_names
                    ])
        
        print(f"CSV report saved to: {output_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='SQL Conversion Complexity Scoring Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # MySQL 쿼리 분석
  python3 sql_conversion_scoring_engine.py \\
      --source-db MY \\
      --input queries.json \\
      --output result

  # 여러 파일 분석
  python3 sql_conversion_scoring_engine.py \\
      --source-db ORA \\
      --input file1.json file2.json \\
      --output analysis_result

Supported DBMS:
  ORA (Oracle), MY (MySQL), MDB (MariaDB), PG (PostgreSQL),
  SS (SQL Server), ALT (Altibase), DB2 (IBM DB2)
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
        default='conversion_analysis_result',
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
        rules_path = script_dir / 'conversion-rules.yml'
        
        if not rules_path.exists():
            # 현재 디렉토리에서 찾기
            rules_path = Path('conversion-rules.yml')
        
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
    engine = SQLConversionScoringEngine(rules_path, args.source_db)
    print(f"Loaded {len(engine.compiled_patterns)} applicable rules for {engine.source_db}")
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
    print(f"Total Weighted Score: {result.summary['total_weighted_score']}")
    print(f"Average Score: {result.summary['average_score']}")
    print(f"Overall Complexity: {result.summary['overall_complexity_level']}")
    print()
    print("Complexity Distribution:")
    for level in ['매우 낮음', '낮음', '중간', '높음', '매우 높음']:
        count = result.summary['complexity_distribution'].get(level, 0)
        total = result.summary['total_queries']
        pct = (count / total * 100) if total > 0 else 0
        bar = '█' * int(pct / 5)
        print(f"  {level:10s}: {count:4d} ({pct:5.1f}%) {bar}")
    print()
    print("Conversion Grade Distribution:")
    grade_desc = {'A': 'Auto', 'P': 'Partial', 'M': 'Manual'}
    for grade in ['A', 'P', 'M']:
        count = result.summary['grade_distribution'].get(grade, 0)
        print(f"  {grade} ({grade_desc[grade]:7s}): {count}")
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
