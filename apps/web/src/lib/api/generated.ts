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
    "/api/v1/auth/local-session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Session */
        post: operations["session_api_v1_auth_local_session_post"];
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
    "/api/v1/tasks/sample": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sample */
        get: operations["sample_api_v1_tasks_sample_get"];
        put?: never;
        post?: never;
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
        /** CurrentTaskResult */
        CurrentTaskResult: {
            /** Status */
            status: string;
            task?: components["schemas"]["TaskVersion"] | null;
        };
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
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HealthResult */
        HealthResult: {
            /**
             * Status
             * @default ok
             */
            status: string;
        };
        JsonValue: unknown;
        /**
         * Language
         * @enum {string}
         */
        Language: "ar-EG" | "en";
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
        /** RuntimeResult */
        RuntimeResult: {
            /** Mode */
            mode: string;
            /** Simulated Evaluation */
            simulated_evaluation: boolean;
        };
        /** SessionResult */
        SessionResult: {
            /** Access Token */
            access_token: string;
            /**
             * Expires In
             * @default 604800
             */
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
        /**
         * TaskStatus
         * @enum {string}
         */
        TaskStatus: "AVAILABLE" | "ACTIVE" | "COMPLETED";
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
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
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
            header?: {
                authorization?: string | null;
            };
            path?: never;
            cookie?: never;
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
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_api_v1_artifacts__artifact_id__complete_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path: {
                artifact_id: string;
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
                    "application/json": components["schemas"]["UploadCompletionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_api_v1_artifacts__artifact_id__content_put: {
        parameters: {
            query?: never;
            header?: {
                "x-upload-token"?: string | null;
                authorization?: string | null;
            };
            path: {
                artifact_id: string;
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
                    "application/json": components["schemas"]["UploadCompletionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    attempts_api_v1_attempts_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
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
                    "application/json": components["schemas"]["AttemptResult"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    session_api_v1_auth_local_session_post: {
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
                    "application/json": components["schemas"]["SessionResult"];
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
        };
    };
    me_api_v1_learners_me_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
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
                    "application/json": components["schemas"]["Learner"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    onboard_api_v1_learners_onboard_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path?: never;
            cookie?: never;
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
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
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
        };
    };
    skills_api_v1_skills_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
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
                    "application/json": components["schemas"]["SkillsProfile"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_api_v1_submissions_post: {
        parameters: {
            query?: never;
            header: {
                "idempotency-key": string;
                authorization?: string | null;
            };
            path?: never;
            cookie?: never;
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
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    outcome_api_v1_submissions__submission_id__get: {
        parameters: {
            query?: never;
            header: {
                "idempotency-key": string;
                authorization?: string | null;
            };
            path: {
                submission_id: string;
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
                    "application/json": components["schemas"]["SubmissionOutcome"] | components["schemas"]["ProcessingState"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    current_api_v1_tasks_current_get: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
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
                    "application/json": components["schemas"]["CurrentTaskResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sample_api_v1_tasks_sample_get: {
        parameters: {
            query?: {
                clean?: boolean;
            };
            header?: {
                authorization?: string | null;
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
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
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
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
