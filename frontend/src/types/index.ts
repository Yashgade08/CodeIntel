export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface SystemReadinessResponse {
  status: 'ready' | 'degraded';
  checks: {
    postgres: { status: string; detail?: string };
    redis: { status: string; detail?: string };
  };
  timestamp: string;
}

export interface Repository {
  id: string;
  github_url: string;
  owner: string;
  name: string;
  description?: string;
  languages?: Record<string, number>;
  topics?: string[];
  star_count: number;
  fork_count: number;
  open_issues_count: number;
  ingestion_status: 'pending' | 'cloning' | 'parsing' | 'embedding' | 'complete' | 'failed';
  ingestion_progress: number;
  created_at: string;
  updated_at: string;

  file_count?: number;
  function_count?: number;
  class_count?: number;
  total_loc?: number;
  health_score?: number;
  average_risk_score?: number;
  high_risk_files_count?: number;
}

export interface IngestionStatusResponse {
  repository_id: string;
  status: 'pending' | 'cloning' | 'parsing' | 'embedding' | 'complete' | 'failed';
  progress_percentage: number;
  current_step?: string;
  error_message?: string;
}

export interface FileRecord {
  id: string;
  repository_id: string;
  path: string;
  language: string;
  size_bytes: number;
  line_count: number;
  cyclomatic_complexity?: number;
  risk_score?: number;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  content?: string;
}

export type IssueCategory = 'Bug' | 'Feature Request' | 'Documentation' | 'Question' | 'Enhancement' | 'Performance' | 'Security';
export type IssueSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface DuplicateCandidate {
  issue_id: string;
  number?: number;
  title: string;
  similarity_score: number;
  confidence: number;
}

export interface Issue {
  id: string;
  repository_id: string;
  number: number;
  title: string;
  body?: string;
  state: 'open' | 'closed';
  labels?: string[];
  github_author?: string;
  
  category?: IssueCategory;
  severity?: IssueSeverity;
  confidence_score?: number;
  duplicate_candidates?: DuplicateCandidate[];
  analyzed_at?: string;
  created_at: string;
}

export interface IssueAnalyzeRequest {
  repository_id: string;
  issue_id?: string;
  title?: string;
  body?: string;
  labels?: string[];
}

export interface IssueAnalyzeResponse {
  issue_id: string;
  category: IssueCategory;
  severity: IssueSeverity;
  confidence_score: number;
  duplicate_candidates: DuplicateCandidate[];
}

export interface ShapFactor {
  feature_name: string;
  impact_score: number;
  value: number | string;
  description: string;
}

export interface FileRiskDetail {
  file: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  cyclomatic_complexity: number;
  line_count: number;
  dependency_count: number;
  num_contributors: number;
  commit_frequency: number;
  top_factors: ShapFactor[];
}

export interface RiskSummaryResponse {
  repository_id: string;
  average_risk_score: number;
  risk_distribution: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
  };
  high_risk_files: FileRiskDetail[];
}

export interface GraphNodeData {
  label: string;
  path: string;
  language?: string;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  risk_score?: number;
  metrics?: {
    line_count?: number;
    cyclomatic_complexity?: number;
  };
}

export interface DependencyGraphNode {
  id: string;
  type?: string;
  data: GraphNodeData;
  position: { x: number; y: number };
}

export interface DependencyGraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
}

export interface GraphDataResponse {
  repository_id: string;
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
}

export interface FileImpactResponse {
  file_path: string;
  dependencies: string[];
  dependents: string[];
  affected_modules: string[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  sources?: {
    file_path: string;
    line_start?: number;
    line_end?: number;
    snippet?: string;
  }[];
  timestamp: string;
}

export interface ChatQueryRequest {
  repository_id: string;
  query: string;
  conversation_history?: ChatMessage[];
}

export interface ChatQueryResponse {
  answer: string;
  sources: {
    file_path: string;
    line_start?: number;
    line_end?: number;
    snippet?: string;
  }[];
}

export interface PrReviewResponse {
  pr_id: string;
  title: string;
  author: string;
  diff_summary: string;
  risk_score_delta: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  code_smells: {
    file: string;
    line?: number;
    issue: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
  }[];
  security_findings: {
    file: string;
    description: string;
    cve?: string;
    severity: 'MEDIUM' | 'HIGH' | 'CRITICAL';
  }[];
  summary_markdown: string;
}

export interface EvaluationMetricsResponse {
  evaluation_timestamp: string;
  status: string;
  rag_metrics: {
    recall_at_1: number;
    recall_at_3: number;
    recall_at_5: number;
    precision_at_1: number;
    precision_at_3: number;
    precision_at_5: number;
    mrr: number;
    context_relevance: number;
    answer_relevance: number;
    faithfulness: number;
  };
  ml_metrics: {
    issue_classification: { accuracy: number; macro_f1: number; weighted_f1: number };
    severity_prediction: { macro_f1: number; weighted_f1: number };
    duplicate_detection: { precision: number; recall: number; f1: number };
    code_risk: { accuracy: number; brier_score_calibration: number; calibration_status: string };
  };
  llm_metrics: {
    citation_correctness: number;
    groundedness: number;
    hallucination_rate: number;
    answer_relevance: number;
  };
  performance_latency: {
    ingestion_time_s: number;
    embedding_time_ms: number;
    retrieval_latency_ms: number;
    reranking_latency_ms: number;
    llm_latency_ms: number;
    end_to_end_latency_ms: number;
  };
}

export interface ApiError {
  error: string;
  message: string;
}
