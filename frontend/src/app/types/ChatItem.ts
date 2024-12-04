import { AttackReport } from "./API";

export type ChatItem = Message | ReportCard


export interface Message {
    type: 'message';
    id: string; // ai-message | user-message
    message: string;
    identifiant?: string;
    avatar: string;
    timestamp: number;
}

export interface VulnerabilityReportCard {
    vulnerability: string;
    description: string;
    reports: AttackReport[];
}

export interface ReportCard {
    type: 'report-card';
    reports: VulnerabilityReportCard[];
    name: string;
}
