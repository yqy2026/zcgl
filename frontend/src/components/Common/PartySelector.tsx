import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Select, Typography } from 'antd';
import type { SelectProps } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { partyService } from '@/services/partyService';
import type { Party, PartyType } from '@/types/party';
import styles from './PartySelector.module.css';

const { Text } = Typography;

const DEFAULT_SEARCH_LIMIT = 20;
const EMPTY_STATUS_TEXT = '请先创建主体数据';
const FORBIDDEN_STATUS_TEXT = '当前账号无 party.read 权限，请联系管理员';
const FORBIDDEN_PATTERN = /(403|PERMISSION_DENIED|AUTHZ_DENIED|forbidden)/i;
const FORBIDDEN_ERROR_CODE_PATTERN = /(PERMISSION_DENIED|AUTHZ_DENIED|HTTP_403|FORBIDDEN)/i;
const ROLE_ALIGNED_PARTY_TYPES: readonly PartyType[] = ['organization', 'legal_entity'];

export type PartySelectorFilterMode = 'owner' | 'manager' | 'tenant' | 'any';

export interface PartySelectorSelection {
  party_id: string;
  party_name: string;
  party?: Party;
}

type PartyFetcher = (query: string, filterMode: PartySelectorFilterMode) => Promise<Party[]>;
type PartySearchExecutor = typeof partyService.searchParties;

interface PartyOption extends DefaultOptionType {
  value: string;
  label: string;
  party: Party;
}

export interface PartySelectorProps {
  value?: string;
  onChange?: (value?: string, selection?: PartySelectorSelection) => void;
  placeholder?: string;
  disabled?: boolean;
  allowClear?: boolean;
  size?: SelectProps<string>['size'];
  style?: React.CSSProperties;
  filterMode?: PartySelectorFilterMode;
  fetcher?: PartyFetcher;
}

const mergeAndDedupeParties = (partyGroups: Party[][]): Party[] => {
  const deduped = new Map<string, Party>();
  partyGroups.flat().forEach(party => {
    if (!deduped.has(party.id)) {
      deduped.set(party.id, party);
    }
  });
  return Array.from(deduped.values());
};

export const createDefaultPartyFetcher = (searchParties: PartySearchExecutor): PartyFetcher => {
  return async (query, filterMode) => {
    if (filterMode === 'owner' || filterMode === 'manager') {
      const responses = await Promise.all(
        ROLE_ALIGNED_PARTY_TYPES.map(async partyType => {
          const result = await searchParties(query, {
            limit: DEFAULT_SEARCH_LIMIT,
            party_type: partyType,
          });
          return result.items;
        })
      );
      return mergeAndDedupeParties(responses).slice(0, DEFAULT_SEARCH_LIMIT);
    }

    const result = await searchParties(query, { limit: DEFAULT_SEARCH_LIMIT });
    return result.items;
  };
};
const defaultFetcher = createDefaultPartyFetcher(partyService.searchParties.bind(partyService));

const toErrorRecord = (error: unknown): Record<string, unknown> | null => {
  if (error == null || typeof error !== 'object') {
    return null;
  }
  return error as Record<string, unknown>;
};

const isForbiddenStatusCode = (value: unknown): boolean => {
  if (typeof value === 'number') {
    return value === 403;
  }

  if (typeof value === 'string') {
    return value.trim() === '403';
  }

  return false;
};

const isForbiddenErrorCode = (value: unknown): boolean => {
  if (typeof value !== 'string') {
    return false;
  }

  return FORBIDDEN_ERROR_CODE_PATTERN.test(value);
};

const isPartyReadForbidden = (error: unknown): boolean => {
  if (error == null) {
    return false;
  }

  const errorRecord = toErrorRecord(error);
  if (errorRecord != null) {
    if (
      isForbiddenStatusCode(errorRecord.statusCode) ||
      isForbiddenStatusCode(errorRecord.status) ||
      isForbiddenErrorCode(errorRecord.code)
    ) {
      return true;
    }

    const responseRecord = toErrorRecord(errorRecord.response);
    if (responseRecord != null && isForbiddenStatusCode(responseRecord.status)) {
      return true;
    }

    const responseDataRecord = toErrorRecord(responseRecord?.data);
    if (
      responseDataRecord != null &&
      (isForbiddenErrorCode(responseDataRecord.code) ||
        isForbiddenStatusCode(responseDataRecord.statusCode) ||
        isForbiddenStatusCode(responseDataRecord.status))
    ) {
      return true;
    }
  }

  if (typeof error === 'string') {
    return FORBIDDEN_PATTERN.test(error);
  }
  if (error instanceof Error) {
    return FORBIDDEN_PATTERN.test(error.message);
  }
  return FORBIDDEN_PATTERN.test(String(error));
};

const toPartyOption = (party: Party): PartyOption => {
  return {
    value: party.id,
    label: `${party.name} [${party.code}]`,
    party,
  };
};

const PartySelector: React.FC<PartySelectorProps> = ({
  value,
  onChange,
  placeholder = '请选择主体',
  disabled = false,
  allowClear = true,
  size = 'middle',
  style,
  filterMode = 'any',
  fetcher = defaultFetcher,
}) => {
  const [options, setOptions] = useState<PartyOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const optionPartyMap = useMemo(() => {
    const map = new Map<string, Party>();
    options.forEach(option => {
      map.set(option.value, option.party);
    });
    return map;
  }, [options]);

  const loadOptions = useCallback(
    async (query: string) => {
      requestIdRef.current += 1;
      const currentRequestId = requestIdRef.current;
      setLoading(true);
      setStatusText(null);

      try {
        const parties = await fetcher(query, filterMode);
        if (currentRequestId !== requestIdRef.current) {
          return;
        }
        const nextOptions = parties.map(toPartyOption);
        setOptions(nextOptions);
        setStatusText(nextOptions.length === 0 ? EMPTY_STATUS_TEXT : null);
      } catch (error) {
        if (currentRequestId !== requestIdRef.current) {
          return;
        }
        setOptions([]);
        setStatusText(isPartyReadForbidden(error) ? FORBIDDEN_STATUS_TEXT : EMPTY_STATUS_TEXT);
      } finally {
        if (currentRequestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    },
    [fetcher, filterMode]
  );

  useEffect(() => {
    void loadOptions('');
  }, [loadOptions]);

  const handleSearch = useCallback(
    (nextKeyword: string) => {
      const normalizedKeyword = nextKeyword.trim();
      void loadOptions(normalizedKeyword);
    },
    [loadOptions]
  );

  const handleChange = useCallback<NonNullable<SelectProps<string, PartyOption>['onChange']>>(
    (nextValue, option) => {
      const selectedValue = typeof nextValue === 'string' ? nextValue : undefined;
      if (selectedValue == null || selectedValue === '') {
        onChange?.(undefined);
        return;
      }

      const party = optionPartyMap.get(selectedValue);
      if (party != null) {
        onChange?.(selectedValue, {
          party_id: selectedValue,
          party_name: party.name,
          party,
        });
        return;
      }

      const optionLabel =
        option != null && !Array.isArray(option) && typeof option.label === 'string'
          ? option.label
          : selectedValue;

      onChange?.(selectedValue, {
        party_id: selectedValue,
        party_name: optionLabel,
      });
    },
    [onChange, optionPartyMap]
  );

  const notFoundContent = loading ? '加载中...' : (statusText ?? EMPTY_STATUS_TEXT);

  return (
    <div className={styles.wrapper} style={style}>
      <Select<string, PartyOption>
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        allowClear={allowClear}
        size={size}
        showSearch
        filterOption={false}
        onSearch={handleSearch}
        options={options}
        loading={loading}
        notFoundContent={notFoundContent}
      />

      {!loading && statusText != null && (
        <Text role="status" type="secondary" className={styles.statusText}>
          {statusText}
        </Text>
      )}
    </div>
  );
};

export default PartySelector;
