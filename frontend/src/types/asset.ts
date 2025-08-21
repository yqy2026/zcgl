export interface Asset {
  id: string
  property_name: string
  ownership_entity: string
  management_entity?: string
  address: string
  land_area?: number
  actual_property_area?: number
  rentable_area?: number
  rented_area?: number
  unrented_area?: number
  non_commercial_area?: number
  ownership_status: OwnershipStatus
  certificated_usage?: string
  actual_usage?: string
  business_category?: string
  usage_status: UsageStatus
  is_litigated?: boolean
  property_nature: PropertyNature
  business_model?: string
  include_in_occupancy_rate?: boolean
  occupancy_rate?: string
  lease_contract?: string
  current_contract_start_date?: string
  current_contract_end_date?: string
  tenant_name?: string
  ownership_category?: string
  current_lease_contract?: string
  wuyang_project_name?: string
  agreement_start_date?: string
  agreement_end_date?: string
  current_terminal_contract?: string
  description?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export enum OwnershipStatus {
  CONFIRMED = '已确权',
  UNCONFIRMED = '未确权',
  PARTIAL = '部分确权'
}

export enum UsageStatus {
  RENTED = '出租',
  VACANT = '闲置',
  SELF_USE = '自用',
  PUBLIC = '公房',
  OTHER = '其他'
}

export enum PropertyNature {
  COMMERCIAL = '经营类',
  NON_COMMERCIAL = '非经营类'
}

export interface AssetFormData extends Omit<Asset, 'id' | 'created_at' | 'updated_at'> {}

export interface AssetListResponse {
  data: Asset[]
  total: number
  page: number
  limit: number
  has_next: boolean
  has_prev: boolean
}

export interface AssetSummary {
  total: number
  rented: number
  vacant: number
  avgOccupancyRate: number
}