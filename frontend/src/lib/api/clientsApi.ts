import { callApi } from "./http"

export const ClientsApi = {
  listCompanies: () => callApi("/api/v1/companies/", "GET"),
  createCompany: (payload: { name: string; payment_term?: number; aka_names?: string[] }) =>
    callApi("/api/v1/companies/", "POST", payload),
  updateCompany: (
    companyId: string,
    payload: {
      name?: string
      payment_term?: number
      aka_names?: string[]
      is_active?: boolean
    },
  ) => callApi(`/api/v1/companies/${companyId}`, "PATCH", payload),
  deleteCompany: (companyId: string) => callApi(`/api/v1/companies/${companyId}`, "DELETE"),
  listCompanyDomains: (companyId: string) =>
    callApi(`/api/v1/companies/${companyId}/domains`, "GET"),
  createCompanyDomain: (companyId: string, domainPattern: string) =>
    callApi(`/api/v1/companies/${companyId}/domains`, "POST", {
      company_id: companyId,
      domain_pattern: domainPattern,
      is_active: true,
    }),
  updateCompanyDomain: (
    domainId: string,
    payload: { domain_pattern?: string; is_active?: boolean },
  ) => callApi(`/api/v1/companies/domains/${domainId}`, "PATCH", payload),
  deleteCompanyDomain: (domainId: string) =>
    callApi(`/api/v1/companies/domains/${domainId}`, "DELETE"),
  listRateContracts: (companyId?: string) =>
    callApi(
      `/api/v1/rate-contracts/${companyId ? `?company_id=${companyId}` : ""}`,
      "GET",
    ),
  createRateContract: (payload: {
    company_id: string
    product_name: string
    sku: string
    agreed_rate: number
    gst_rate: number
    is_active?: boolean
  }) => callApi("/api/v1/rate-contracts/", "POST", payload),
  updateRateContract: (
    contractId: string,
    payload: {
      product_name?: string
      sku?: string
      agreed_rate?: number
      gst_rate?: number
      is_active?: boolean
    },
  ) => callApi(`/api/v1/rate-contracts/${contractId}`, "PATCH", payload),
  deleteRateContract: (contractId: string) =>
    callApi(`/api/v1/rate-contracts/${contractId}`, "DELETE"),
  listValidationRules: () => callApi("/api/v1/validations/rules", "GET"),
  createValidationRule: (payload: {
    key: string
    label: string
    definition_json?: string
    is_active?: boolean
  }) =>
    callApi("/api/v1/validations/rules", "POST", {
      definition_json: "{}",
      is_active: true,
      ...payload,
    }),
  updateValidationRule: (
    ruleId: string,
    payload: {
      key?: string
      label?: string
      definition_json?: string
      is_active?: boolean
    },
  ) => callApi(`/api/v1/validations/rules/${ruleId}`, "PATCH", payload),
  deleteValidationRule: (ruleId: string) => callApi(`/api/v1/validations/rules/${ruleId}`, "DELETE"),
  listValidationAssignments: (companyId?: string) =>
    callApi(
      `/api/v1/validations/assignments${companyId ? `?company_id=${companyId}` : ""}`,
      "GET",
    ),
  createValidationAssignment: (payload: {
    company_id: string
    validation_rule_id: string
    is_enabled?: boolean
  }) =>
    callApi("/api/v1/validations/assignments", "POST", {
      ...payload,
      is_enabled: payload.is_enabled ?? true,
    }),
  updateValidationAssignment: (
    assignmentId: string,
    payload: { is_enabled?: boolean },
  ) => callApi(`/api/v1/validations/assignments/${assignmentId}`, "PATCH", payload),
  deleteValidationAssignment: (assignmentId: string) =>
    callApi(`/api/v1/validations/assignments/${assignmentId}`, "DELETE"),
}
