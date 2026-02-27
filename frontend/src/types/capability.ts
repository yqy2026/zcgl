/** Capability types consumed from `/api/v1/auth/me/capabilities`. */

export type AuthzAction = 'create' | 'read' | 'list' | 'update' | 'delete' | 'export';

export type ResourceType =
  | 'analytics'
  | 'asset'
  | 'backup'
  | 'collection'
  | 'contact'
  | 'custom_field'
  | 'dictionary'
  | 'enum_field'
  | 'error_recovery'
  | 'excel_config'
  | 'history'
  | 'llm_prompt'
  | 'notification'
  | 'occupancy'
  | 'operation_log'
  | 'organization'
  | 'ownership'
  | 'party'
  | 'project'
  | 'property_certificate'
  | 'rent_contract'
  | 'role'
  | 'system_monitoring'
  | 'system_settings'
  | 'task'
  | 'user'
  | (string & {});

export type Perspective = 'owner' | 'manager' | (string & {});

export interface CapabilityDataScope {
  owner_party_ids: string[];
  manager_party_ids: string[];
}

export interface CapabilityItem {
  resource: ResourceType;
  actions: AuthzAction[];
  perspectives: Perspective[];
  data_scope: CapabilityDataScope;
}

export interface CapabilitiesResponse {
  version: string;
  generated_at: string;
  capabilities: CapabilityItem[];
}
