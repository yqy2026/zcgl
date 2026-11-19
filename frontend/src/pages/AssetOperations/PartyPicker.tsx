/**
 * 主体选择器（原型：录入合同时「选」主体而非手输 Party ID）。
 * 搜索走 partyService.searchParties，选中后仍回填 Party ID 保持既有
 * 提交契约不变；显示「名称（ID 前 8 位）」便于核对。
 */

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Select } from 'antd';
import { partyService } from '@/services/partyService';

export default function PartyPicker(props: {
  value: string;
  onChange: (value: string) => void;
  label: string;
  hint?: string;
}): React.ReactElement {
  const [keyword, setKeyword] = useState('');
  const partiesQuery = useQuery({
    queryKey: ['party-picker', keyword.trim()],
    queryFn: () => partyService.searchParties(keyword.trim(), { limit: 20 }),
    staleTime: 30 * 1000,
  });
  const options = useMemo(
    () =>
      (partiesQuery.data?.items ?? []).map(party => ({
        value: party.id,
        label: `${party.name}（${party.id.slice(0, 8)}…）`,
      })),
    [partiesQuery.data]
  );
  const selectedName = (partiesQuery.data?.items ?? []).find(
    party => party.id === props.value
  )?.name;
  return (
    <label
      className="intake-party-picker"
      style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
    >
      {props.label}
      <Select
        aria-label={props.label}
        showSearch
        allowClear
        filterOption={false}
        value={props.value === '' ? undefined : props.value}
        onSearch={text => setKeyword(text)}
        onChange={value => {
          props.onChange(value ?? '');
        }}
        notFoundContent={
          partiesQuery.isFetching
            ? '搜索中…'
            : keyword.trim() === ''
              ? '输入名称搜索主体'
              : '未找到匹配主体'
        }
        options={options}
        placeholder={props.hint ?? '输入主体名称搜索后选择'}
      />
      {props.value !== '' && selectedName != null ? (
        <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
          已选：{selectedName}
        </span>
      ) : null}
    </label>
  );
}
