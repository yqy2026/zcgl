/** Data policy package management types. */

export type DataPolicyPackageCode =
  | 'platform_admin'
  | 'asset_owner_operator'
  | 'asset_manager_operator'
  | 'dual_party_viewer'
  | 'project_manager_operator'
  | 'audit_viewer'
  | 'no_data_access'
  | (string & {});

export interface DataPolicyTemplate {
  name: string;
  description: string;
}

export type DataPolicyTemplatesResponse = Record<DataPolicyPackageCode, DataPolicyTemplate>;

export interface RoleDataPoliciesResponse {
  role_id: string;
  policy_packages: DataPolicyPackageCode[];
}

export interface RoleDataPoliciesUpdateRequest {
  policy_packages: DataPolicyPackageCode[];
}
