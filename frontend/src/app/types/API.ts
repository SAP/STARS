export type APIResponse =
    | MessageResponse
    | StatusResponse
    | ReportResponse
    | IntermediateResponse
    | VulnerabilityReport;

interface MessageResponse {
    type: "message";
    data: string;
}

interface StatusResponse {
    type: "status";
    current: number;
    total: number;
}

export type ReportItem = {
    status: string;
    title: string;
    description: string;
    progress: number;
}

interface ReportResponse {
    type: "report";
    reset: boolean;
    data: ReportItem[];
}

interface IntermediateResponse {
    type: "intermediate";
    data: string;
}

// Vulnerability Reports (used for Report Cards)

interface ReportDetails {
    summary: string | undefined;
}

export interface AttackReport {
    attack: string;
    success: boolean;
    vulnerability_type: string;
    details: ReportDetails;
}

interface VulnerabilityReportItem {
    vulnerability: string;
    reports: AttackReport[];
}

interface VulnerabilityReport {
    type: "vulnerability-report";
    data: VulnerabilityReportItem[];
    name: string
}
