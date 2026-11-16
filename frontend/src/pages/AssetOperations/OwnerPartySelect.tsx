import { useQuery } from '@tanstack/react-query';
import { Select } from 'antd';

import { partyService } from '@/services/partyService';

/** 产权方筛选下拉：选项来自 owner 业务角色的主体清单。 */
export default function OwnerPartySelect({
  value,
  onChange,
}: {
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}): React.ReactElement {
  const query = useQuery({
    queryKey: ['owner-party-options'],
    // owner 主体超过 1000 时选项静默截断（接口 limit 上限），当前规模无碍。
    queryFn: () => partyService.getParties({ business_role: 'owner', limit: 1000 }),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  return (
    <Select
      aria-label="按产权方筛选"
      placeholder="全部产权方"
      allowClear
      style={{ minWidth: 180 }}
      value={value}
      loading={query.isLoading}
      onChange={next => onChange(next)}
      options={(query.data?.items ?? []).map(party => ({
        value: party.id,
        label: party.name,
      }))}
    />
  );
}
