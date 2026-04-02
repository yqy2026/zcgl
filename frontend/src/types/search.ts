export interface GlobalSearchResultItem {
  object_type:
    | 'asset'
    | 'project'
    | 'contract_group'
    | 'contract'
    | 'customer'
    | 'property_certificate';
  object_id: string;
  title: string;
  subtitle?: string | null;
  summary?: string | null;
  keywords: string[];
  route_path: string;
  score: number;
  business_rank: number;
  group_label: string;
}

export interface GlobalSearchGroup {
  object_type: string;
  label: string;
  count: number;
}

export interface GlobalSearchResponse {
  query: string;
  total: number;
  items: GlobalSearchResultItem[];
  groups: GlobalSearchGroup[];
}
