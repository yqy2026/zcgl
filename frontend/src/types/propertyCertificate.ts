/** Property certificate contracts for the manual management API. */

export enum CertificateType {
  REAL_ESTATE = 'real_estate',
  HOUSE_OWNERSHIP = 'house_ownership',
  LAND_USE = 'land_use',
  OTHER = 'other',
}

/** 证照类型中文标签（列表/详情/资产摘要共用） */
export const CERTIFICATE_TYPE_LABELS: Record<CertificateType, string> = {
  [CertificateType.REAL_ESTATE]: '不动产权证',
  [CertificateType.HOUSE_OWNERSHIP]: '房屋所有权证',
  [CertificateType.LAND_USE]: '土地使用权证',
  [CertificateType.OTHER]: '其他',
};

export interface PropertyCertificate {
  id: string;
  certificate_number: string;
  certificate_type: CertificateType;
  registration_date: string | null;
  property_address: string | null;
  property_type: string | null;
  building_area: string | null;
  land_area: string | null;
  floor_info: string | null;
  land_use_type: string | null;
  land_use_term_start: string | null;
  land_use_term_end: string | null;
  co_ownership: string | null;
  restrictions: string | null;
  remarks: string | null;
  asset_ids: string[];
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface PropertyCertificateCreate {
  certificate_number: string;
  certificate_type: CertificateType;
  registration_date: string | null;
  property_address: string | null;
  property_type: string | null;
  building_area: string | null;
  land_area: string | null;
  floor_info: string | null;
  land_use_type: string | null;
  land_use_term_start: string | null;
  land_use_term_end: string | null;
  co_ownership: string | null;
  restrictions: string | null;
  remarks: string | null;
  asset_ids: string[];
  holder_party_ids: string[];
}

export interface PropertyCertificateUpdate {
  certificate_number?: string;
  certificate_type?: CertificateType;
  registration_date?: string | null;
  property_address?: string | null;
  property_type?: string | null;
  building_area?: string | null;
  land_area?: string | null;
  floor_info?: string | null;
  land_use_type?: string | null;
  land_use_term_start?: string | null;
  land_use_term_end?: string | null;
  co_ownership?: string | null;
  restrictions?: string | null;
  remarks?: string | null;
  asset_ids?: string[];
  holder_party_ids?: string[];
}
