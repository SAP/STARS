export interface Step {
    title: string;
    description?: string;
    progress?: number;
    status: Status;
}

export enum Status {
    RUNNING,
    COMPLETED,
    FAILED,
    SKIPPED,
    PENDING
}
