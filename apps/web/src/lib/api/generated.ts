export interface paths {
    "/api/v1/artifacts/upload-authorization": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Authorize */
        post: operations["authorize_api_v1_artifacts_upload_authorization_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/artifacts/{artifact_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete */
        post: operations["complete_api_v1_artifacts__artifact_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/artifacts/{artifact_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Upload */
        put: operations["upload_api_v1_artifacts__artifact_id__content_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attempts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Attempts */
        get: operations["attempts_api_v1_attempts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Session */
        post: operations["session_api_v1_auth_session_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/certificates/{token}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Public Certificate
         * @description Public and read-only: anyone holding the link can verify it, nothing else.
         */
        get: operations["public_certificate_api_v1_certificates__token__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learners/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_v1_learners_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learners/me/certificate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** My Certificate */
        get: operations["my_certificate_api_v1_learners_me_certificate_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learners/me/language": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Language */
        put: operations["language_api_v1_learners_me_language_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/learners/onboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Onboard */
        post: operations["onboard_api_v1_learners_onboard_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runtime": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runtime */
        get: operations["runtime_api_v1_runtime_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/skills": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Skills */
        get: operations["skills_api_v1_skills_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/submissions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit */
        post: operations["submit_api_v1_submissions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/submissions/{submission_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Outcome */
        get: operations["outcome_api_v1_submissions__submission_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/submissions/{submission_id}/feedback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Feedback */
        get: operations["feedback_api_v1_submissions__submission_id__feedback_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/submissions/{submission_id}/insights": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Insights */
        get: operations["insights_api_v1_submissions__submission_id__insights_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/submissions/{submission_id}/questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Ask
         * @description Ask Tarek about one's own graded submission; answers use its facts only.
         */
        post: operations["ask_api_v1_submissions__submission_id__questions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Tasks */
        get: operations["tasks_api_v1_tasks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Current */
        get: operations["current_api_v1_tasks_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Task Detail */
        get: operations["task_detail_api_v1_tasks__task_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/dataset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download */
        get: operations["download_api_v1_tasks__task_id__dataset_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/samples": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Samples */
        get: operations["samples_api_v1_tasks__task_id__samples_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/samples/{sample_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sample File */
        get: operations["sample_file_api_v1_tasks__task_id__samples__sample_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start */
        post: operations["start_api_v1_tasks__task_id__start_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/telegram/webhook": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Telegram */
        post: operations["telegram_api_v1_telegram_webhook_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** ApplicationError */
        ApplicationError: {
            category: components["schemas"]["ErrorCategory"];
            /** Code */
            code: string;
            /** Message */
            message: string;
            /** Retryable */
            retryable: boolean;
        };
        /** AttemptResult */
        AttemptResult: {
            /** Attempt Number */
            attempt_number: number;
            evaluation: components["schemas"]["EvaluationResult"];
            feedback: components["schemas"]["FeedbackResult"];
            /**
             * Submission Id
             * Format: uuid
             */
            submission_id: string;
        };
        /**
         * CellIssue
         * @description A cell in the learner's file; ``row`` is the spreadsheet row, the header being row 1.
         */
        CellIssue: {
            /** Check Id */
            check_id: string;
            /** Column */
            column: string;
            /** Issue */
            issue: string;
            /** Row */
            row: number;
        };
        /** Certificate */
        Certificate: {
            /** Display Name */
            display_name: string;
            /** Skills */
            skills: components["schemas"]["CertificateSkill"][];
            /** Tasks */
            tasks: components["schemas"]["CertificateTask"][];
            /** Token */
            token: string;
            /**
             * Verified At
             * Format: date-time
             */
            verified_at: string;
        };
        /** CertificateSkill */
        CertificateSkill: {
            /** Evidence */
            evidence: string[];
            /** Skill Id */
            skill_id: string;
        };
        /**
         * CertificateTask
         * @description A task the learner passed, as first proven by the evaluator.
         */
        CertificateTask: {
            /** Attempts */
            attempts: number;
            /** Checks */
            checks: string[];
            /**
             * Passed At
             * Format: date-time
             */
            passed_at: string;
            /** Score */
            score: number;
            /** Task Id */
            task_id: string;
            /** Title Ar */
            title_ar: string;
            /** Title En */
            title_en: string;
        };
        /** CheckInfo */
        CheckInfo: {
            /** Check Id */
            check_id: string;
            /** Critical */
            critical: boolean;
            /** Points */
            points: number;
        };
        /** CheckInsight */
        CheckInsight: {
            /** Check Id */
            check_id: string;
            /** Issue Count */
            issue_count: number;
            /** Passed */
            passed: boolean;
        };
        /** CoachAnswer */
        CoachAnswer: {
            /** Answer */
            answer: string;
            /** Grounded On */
            grounded_on: string[];
            language: components["schemas"]["Language"];
            /**
             * Source
             * @enum {string}
             */
            source: "gemini" | "guide";
        };
        /** CurrentTaskResult */
        CurrentTaskResult: {
            /** Status */
            status: string;
            task?: components["schemas"]["TaskVersion"] | null;
        };
        /** EmailElement */
        EmailElement: {
            /** Check Id */
            check_id: string;
            /** Element Id */
            element_id: string;
            /** End */
            end?: number | null;
            /** Found */
            found: boolean;
            /** Start */
            start?: number | null;
        };
        /** EmailInsight */
        EmailInsight: {
            /** Elements */
            elements: components["schemas"]["EmailElement"][];
            /** Max Words */
            max_words: number;
            /** Min Words */
            min_words: number;
            /** Text */
            text: string;
            /** Word Count */
            word_count: number;
        };
        /**
         * ErrorCategory
         * @enum {string}
         */
        ErrorCategory: "validation" | "authorization" | "evaluation" | "provider" | "persistence" | "external_channel" | "infrastructure" | "domain";
        /** EvaluationCheck */
        EvaluationCheck: {
            /** Check Id */
            check_id: string;
            /** Details Ar */
            details_ar: string;
            /** Details En */
            details_en: string;
            /** Diagnostic Code */
            diagnostic_code: string;
            /** Passed */
            passed: boolean;
            /** Weight */
            weight: number;
        };
        /** EvaluationError */
        EvaluationError: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** EvaluationResult */
        EvaluationResult: {
            /** Checks */
            checks: components["schemas"]["EvaluationCheck"][];
            /** Duration Ms */
            duration_ms: number;
            /** Errors */
            errors: components["schemas"]["EvaluationError"][];
            /** Evaluator Id */
            evaluator_id: string;
            /** Evaluator Version */
            evaluator_version: string;
            /** Passed */
            passed: boolean;
            /** Score */
            score: number;
            /** Summary Ar */
            summary_ar: string;
            /** Summary En */
            summary_en: string;
            /**
             * Task Version Id
             * Format: uuid
             */
            task_version_id: string;
        };
        /** FeedbackResult */
        FeedbackResult: {
            /** Duration Ms */
            duration_ms: number;
            /** Feedback Text */
            feedback_text: string;
            /**
             * Language
             * @enum {string}
             */
            language: "ar-EG" | "en";
            /** Model */
            model: string | null;
            /** Persona Id */
            persona_id: string;
            /** Prompt Version */
            prompt_version: string;
            /** Provider */
            provider: string;
            /** Used Fallback */
            used_fallback: boolean;
        };
        /** HealthResult */
        HealthResult: {
            /**
             * Status
             * @default ok
             */
            status: string;
        };
        /** ImpactMetric */
        ImpactMetric: {
            /** Metric Id */
            metric_id: string;
            /**
             * Unit
             * @enum {string}
             */
            unit: "egp" | "orders" | "customers" | "regions" | "elements";
            /** Value */
            value: string;
        };
        JsonValue: unknown;
        /**
         * Language
         * @enum {string}
         */
        Language: "ar-EG" | "en";
        /** LanguageInput */
        LanguageInput: {
            preferred_language: components["schemas"]["Language"];
        };
        /** Learner */
        Learner: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Display Name */
            display_name: string;
            /**
             * Learner Id
             * Format: uuid
             */
            learner_id: string;
            preferred_language: components["schemas"]["Language"];
            /**
             * State Machine Version
             * @default 1
             */
            state_machine_version: string;
            status: components["schemas"]["LearnerStatus"];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * LearnerStatus
         * @enum {string}
         */
        LearnerStatus: "ONBOARDING" | "READY" | "IN_TASK" | "PROCESSING" | "NEEDS_RETRY" | "TASK_COMPLETED" | "PROGRAM_COMPLETED";
        /** OnboardInput */
        OnboardInput: {
            /** Display Name */
            display_name: string;
            /** @default ar-EG */
            preferred_language: components["schemas"]["Language"];
        };
        /** PreviewRow */
        PreviewRow: {
            /** Cells */
            cells: string[];
            /** Row */
            row: number;
        };
        /** ProcessingState */
        ProcessingState: {
            /** Retry After Seconds */
            retry_after_seconds: number;
            status: components["schemas"]["SubmissionStatus"];
            /**
             * Submission Id
             * Format: uuid
             */
            submission_id: string;
        };
        /** QuestionInput */
        QuestionInput: {
            /** @default ar-EG */
            language: components["schemas"]["Language"];
            /** Question */
            question: string;
        };
        /** RuntimeResult */
        RuntimeResult: {
            /**
             * Demo Samples
             * @default false
             */
            demo_samples: boolean;
            /**
             * Feedback Provider
             * @enum {string}
             */
            feedback_provider: "gemini" | "deterministic";
            /**
             * Mode
             * @enum {string}
             */
            mode: "local" | "cloud";
        };
        /**
         * SampleInfo
         * @description A ready-made submission and the result the real evaluator gives it.
         */
        SampleInfo: {
            /** Filename */
            filename: string;
            /**
             * Outcome
             * @enum {string}
             */
            outcome: "pass" | "retry" | "rejected";
            /** Sample Id */
            sample_id: string;
            /** Score */
            score: number;
        };
        /** SampleList */
        SampleList: {
            /** Samples */
            samples: components["schemas"]["SampleInfo"][];
        };
        /** SessionResult */
        SessionResult: {
            /** Expires In */
            expires_in: number;
        };
        /** SkillMapping */
        SkillMapping: {
            /** Check Id */
            check_id: string;
            /** Skill Id */
            skill_id: string;
            /** Weight */
            weight: number;
        };
        /** SkillSummary */
        SkillSummary: {
            /** Score */
            score: number;
            /** Skill Id */
            skill_id: string;
        };
        /** SkillsProfile */
        SkillsProfile: {
            /**
             * Learner Id
             * Format: uuid
             */
            learner_id: string;
            /** Skills */
            skills: components["schemas"]["SkillSummary"][];
        };
        /** SqlInsight */
        SqlInsight: {
            /** Columns */
            columns: string[];
            /** Columns Ok */
            columns_ok: boolean;
            /** Missing Regions */
            missing_regions: number;
            /** Robustness Failed */
            robustness_failed: boolean;
            /** Rows */
            rows: components["schemas"]["SqlRowFinding"][];
        };
        /** SqlRowFinding */
        SqlRowFinding: {
            /** Cells */
            cells: string[];
            /** Count Ok */
            count_ok: boolean;
            /**
             * Region Status
             * @enum {string}
             */
            region_status: "ok" | "unexpected" | "duplicate" | "unreadable";
            /** Revenue Ok */
            revenue_ok: boolean;
        };
        /** SubmissionInput */
        SubmissionInput: {
            /**
             * Artifact Id
             * Format: uuid
             */
            artifact_id: string;
            /** Artifact Sha256 */
            artifact_sha256: string;
            /** Learner Note */
            learner_note?: string | null;
            /**
             * Task Version Id
             * Format: uuid
             */
            task_version_id: string;
        };
        /** SubmissionInsights */
        SubmissionInsights: {
            /** Checks */
            checks: components["schemas"]["CheckInsight"][];
            email?: components["schemas"]["EmailInsight"] | null;
            /**
             * Impact
             * @default []
             */
            impact: components["schemas"]["ImpactMetric"][];
            /**
             * Issues
             * @default []
             */
            issues: components["schemas"]["CellIssue"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "table" | "sql" | "email";
            /** Rejected Code */
            rejected_code?: string | null;
            sql?: components["schemas"]["SqlInsight"] | null;
            table?: components["schemas"]["TablePreview"] | null;
            /** Task Id */
            task_id: string;
        };
        /** SubmissionOutcome */
        SubmissionOutcome: {
            /**
             * Attempt Id
             * Format: uuid
             */
            attempt_id: string;
            /** Attempt Number */
            attempt_number: number;
            evaluation: components["schemas"]["EvaluationResult"];
            feedback: components["schemas"]["FeedbackResult"];
            learner_status: components["schemas"]["LearnerStatus"];
            /** Skills */
            skills: components["schemas"]["SkillSummary"][];
            /**
             * Submission Id
             * Format: uuid
             */
            submission_id: string;
            task_status: components["schemas"]["TaskStatus"];
        };
        /**
         * SubmissionStatus
         * @enum {string}
         */
        SubmissionStatus: "RECEIVED" | "EVALUATING" | "COMPLETED" | "FAILED";
        /** TablePreview */
        TablePreview: {
            /** Columns */
            columns: string[];
            /** Rows */
            rows: components["schemas"]["PreviewRow"][];
            /** Total Rows */
            total_rows: number;
        };
        /** TaskDetail */
        TaskDetail: {
            /** Brief Ar */
            brief_ar: string;
            /** Brief En */
            brief_en: string;
            /** Checks */
            checks: components["schemas"]["CheckInfo"][];
            /** Formats */
            formats: ("csv" | "xlsx")[];
            /** Hints Ar */
            hints_ar: string;
            /** Hints En */
            hints_en: string;
            /** Max Bytes */
            max_bytes: number;
            /** Pass Threshold */
            pass_threshold: number;
            /** Submission Formats */
            submission_formats: ("csv" | "xlsx" | "sql" | "txt")[];
            /** Task Id */
            task_id: string;
            /**
             * Task Version Id
             * Format: uuid
             */
            task_version_id: string;
            /** Title Ar */
            title_ar: string;
            /** Title En */
            title_en: string;
            /** Version */
            version: string;
        };
        /** TaskList */
        TaskList: {
            /** Tasks */
            tasks: components["schemas"]["TaskSummary"][];
        };
        /**
         * TaskStatus
         * @enum {string}
         */
        TaskStatus: "AVAILABLE" | "ACTIVE" | "COMPLETED";
        /** TaskSummary */
        TaskSummary: {
            /** Pass Threshold */
            pass_threshold: number;
            /** Points Total */
            points_total: number;
            /**
             * Status
             * @enum {string}
             */
            status: "available" | "in_progress" | "completed";
            /** Task Id */
            task_id: string;
            /**
             * Task Version Id
             * Format: uuid
             */
            task_version_id: string;
            /** Title Ar */
            title_ar: string;
            /** Title En */
            title_en: string;
            /** Version */
            version: string;
        };
        /** TaskVersion */
        TaskVersion: {
            /** Artifact Schema */
            artifact_schema: {
                [key: string]: components["schemas"]["JsonValue"];
            };
            /** Content Hash */
            content_hash: string;
            /** Evaluator Id */
            evaluator_id: string;
            /** Evaluator Version */
            evaluator_version: string;
            /** Instructions Ar */
            instructions_ar: string;
            /** Instructions En */
            instructions_en: string;
            /** Pass Threshold */
            pass_threshold: number;
            /** Skill Mappings */
            skill_mappings: components["schemas"]["SkillMapping"][];
            /** Task Id */
            task_id: string;
            /**
             * Task Version Id
             * Format: uuid
             */
            task_version_id: string;
            /** Version */
            version: string;
        };
        /** UploadAuthorizationResult */
        UploadAuthorizationResult: {
            /**
             * Artifact Id
             * Format: uuid
             */
            artifact_id: string;
            /** Expires In Seconds */
            expires_in_seconds: number;
            /** Headers */
            headers?: {
                [key: string]: string;
            };
            /** Upload Token */
            upload_token?: string | null;
            /** Upload Url */
            upload_url?: string | null;
        };
        /** UploadCompletionResult */
        UploadCompletionResult: {
            /**
             * Artifact Id
             * Format: uuid
             */
            artifact_id: string;
        };
        /** UploadInput */
        UploadInput: {
            /** Artifact Sha256 */
            artifact_sha256: string;
            /** Content Type */
            content_type: string;
            /** Filename */
            filename: string;
            /** Size Bytes */
            size_bytes: number;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    authorize_api_v1_artifacts_upload_authorization_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UploadInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UploadAuthorizationResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    complete_api_v1_artifacts__artifact_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                artifact_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UploadCompletionResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    upload_api_v1_artifacts__artifact_id__content_put: {
        parameters: {
            query?: never;
            header?: {
                "x-upload-token"?: string | null;
            };
            path: {
                artifact_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UploadCompletionResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    attempts_api_v1_attempts_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttemptResult"][];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    session_api_v1_auth_session_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    public_certificate_api_v1_certificates__token__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Certificate"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    me_api_v1_learners_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Learner"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    my_certificate_api_v1_learners_me_certificate_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Certificate"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    language_api_v1_learners_me_language_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LanguageInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Learner"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    onboard_api_v1_learners_onboard_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OnboardInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Learner"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    runtime_api_v1_runtime_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    skills_api_v1_skills_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SkillsProfile"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    submit_api_v1_submissions_post: {
        parameters: {
            query?: never;
            header: {
                "idempotency-key": string;
            };
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SubmissionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubmissionOutcome"] | components["schemas"]["ProcessingState"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    outcome_api_v1_submissions__submission_id__get: {
        parameters: {
            query?: never;
            header: {
                "idempotency-key": string;
            };
            path: {
                submission_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubmissionOutcome"] | components["schemas"]["ProcessingState"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    feedback_api_v1_submissions__submission_id__feedback_get: {
        parameters: {
            query: {
                language: components["schemas"]["Language"];
            };
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedbackResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    insights_api_v1_submissions__submission_id__insights_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubmissionInsights"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    ask_api_v1_submissions__submission_id__questions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuestionInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CoachAnswer"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    tasks_api_v1_tasks_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskList"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    current_api_v1_tasks_current_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentTaskResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    task_detail_api_v1_tasks__task_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskDetail"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    download_api_v1_tasks__task_id__dataset_get: {
        parameters: {
            query?: {
                format?: "csv" | "xlsx";
            };
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": unknown;
                    "text/csv": unknown;
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    samples_api_v1_tasks__task_id__samples_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SampleList"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    sample_file_api_v1_tasks__task_id__samples__sample_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
                sample_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": unknown;
                    "text/csv": unknown;
                    "text/plain": unknown;
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    start_api_v1_tasks__task_id__start_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: {
                yom_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentTaskResult"];
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
    telegram_api_v1_telegram_webhook_post: {
        parameters: {
            query?: never;
            header?: {
                "x-telegram-bot-api-secret-token"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: boolean;
                    };
                };
            };
            /** @description Malformed request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Authentication required */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Access denied */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Resource not found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description State or idempotency conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Artifact too large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Unsupported or unsafe artifact */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Validation or artifact integrity failure */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Rate limit exceeded */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
            /** @description Evaluation, persistence or infrastructure unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationError"];
                };
            };
        };
    };
}
