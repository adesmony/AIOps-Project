/**
 * @typedef {'runbook' | 'log' | 'metric'} CitationType
 *
 * @typedef {Object} Citation
 * @property {string} id
 * @property {CitationType} type
 * @property {string} source
 * @property {string} evidence
 * @property {string} observedAt
 *
 * @typedef {Object} AnalysisRequest
 * @property {string} description
 * @property {string=} service
 * @property {string=} timeWindow
 *
 * @typedef {Object} AnalysisResponse
 * @property {string} requestId
 * @property {string} diagnosis
 * @property {number} confidence
 * @property {Citation[]} citations
 * @property {string[]} recommendedHumanActions
 * @property {string[]} limitations
 *
 * @typedef {Object} User
 * @property {string} id
 * @property {string} name
 * @property {string} email
 * @property {string} role
 *
 * @typedef {Object} LoginInput
 * @property {string} email
 * @property {string} password
 *
 * @typedef {Object} CreateAccountInput
 * @property {string} name
 * @property {string} email
 * @property {string} password
 *
 * @typedef {Object} HealthResponse
 * @property {'healthy' | 'degraded' | 'unhealthy'} status
 * @property {Record<string, { status: 'healthy' | 'unhealthy' | 'disabled', essential: boolean }>} services
 *
 * @typedef {Object} DashboardMetrics
 * @property {number} totalApiRequests
 * @property {number} totalIncidents
 * @property {number} totalNonErrors
 * @property {{ label: string, count: number }[]} requestsOverTime
 *
 * Stable frontend boundary. A live client must implement every method without
 * requiring callers outside src/api to change.
 *
 * @typedef {Object} ApiClient
 * @property {(input: CreateAccountInput) => Promise<User>} createAccount
 * @property {(input: LoginInput) => Promise<User>} login
 * @property {() => Promise<void>} logout
 * @property {() => Promise<User | null>} getCurrentUser
 * @property {(input: AnalysisRequest) => Promise<AnalysisResponse | null>} analyzeIncident
 * @property {() => Promise<DashboardMetrics>} getMetrics
 * @property {() => Promise<HealthResponse>} getHealth
 */

export {};