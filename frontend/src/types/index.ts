export type SeverityLevel = "normal" | "low" | "moderate" | "high" | "critical";
export type ReportStatus = "pending" | "processing" | "completed" | "failed";
export type ReportType = "chest_xray" | "ct_scan" | "mri" | "ultrasound" | "mammogram" | "other";
export type UserRole = "admin" | "radiologist" | "clinician";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RadiologyReport {
  id: string;
  patient_id: string;
  report_type: ReportType;
  status: ReportStatus;
  severity?: SeverityLevel;
  risk_score?: number;
  classification_confidence?: number;
  ai_summary?: string;
  findings_count: number;
  has_critical_findings: boolean;
  flagged_for_review: boolean;
  created_at: string;
  updated_at: string;
  processing_time_ms?: number;
}

export interface ExtractedFinding {
  id: string;
  report_id: string;
  category: string;
  disease?: string;
  anatomy?: string;
  symptoms: string[];
  severity?: string;
  finding_text: string;
  normalized_term?: string;
  confidence: number;
  negated: boolean;
}

export interface SeverityScore {
  report_id: string;
  overall_score: number;
  risk_level: SeverityLevel;
  urgency_score: number;
  complexity_score: number;
  critical_findings: string[];
  recommendations: string[];
  explainability: Record<string, unknown>;
}

export interface DashboardKPIs {
  total_reports: number;
  reports_today: number;
  critical_cases: number;
  avg_risk_score: number;
  processing_rate: number;
  flagged_for_review: number;
}

export interface AnomalyAlert {
  id: string;
  anomaly_type: string;
  severity: string;
  description: string;
  detected_at: string;
  affected_metric: string;
  deviation_score: number;
  is_resolved: boolean;
}

export interface SearchResult {
  report_id: string;
  patient_id: string;
  summary: string;
  severity: SeverityLevel;
  score: number;
  created_at: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
