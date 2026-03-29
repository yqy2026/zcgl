import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Form, Input, Modal, Select, Typography } from 'antd';
import type { SelectProps } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { useLocation } from 'react-router-dom';
import { partyService } from '@/services/partyService';
import type { Party, PartyType } from '@/types/party';
import { MessageManager } from '@/utils/messageManager';
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

const resolveCurrentViewFilterMode = (pathname: string): PartySelectorFilterMode => {
  if (pathname.startsWith('/owner/')) {
    return 'owner';
  }

  if (pathname.startsWith('/manager/')) {
    return 'manager';
  }

  return 'any';
};

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
  allowQuickCreate?: boolean;
}

interface QuickCreateFormValues {
  party_type: PartyType;
  name: string;
  code: string;
}

const resolveDefaultCreatePartyType = (filterMode: PartySelectorFilterMode): PartyType => {
  if (filterMode === 'tenant') {
    return 'legal_entity';
  }
  return 'organization';
};

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
  filterMode,
  fetcher = defaultFetcher,
  allowQuickCreate = false,
}) => {
  const location = useLocation();
  const [quickCreateForm] = Form.useForm<QuickCreateFormValues>();
  const [options, setOptions] = useState<PartyOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [quickCreateOpen, setQuickCreateOpen] = useState(false);
  const [quickCreateSubmitting, setQuickCreateSubmitting] = useState(false);
  const requestIdRef = useRef(0);

  const optionPartyMap = useMemo(() => {
    const map = new Map<string, Party>();
    options.forEach(option => {
      map.set(option.value, option.party);
    });
    return map;
  }, [options]);

  const resolvedFilterMode = filterMode ?? resolveCurrentViewFilterMode(location.pathname);
  const defaultCreatePartyType = resolveDefaultCreatePartyType(resolvedFilterMode);

  const loadOptions = useCallback(
    async (query: string) => {
      requestIdRef.current += 1;
      const currentRequestId = requestIdRef.current;
      setLoading(true);
      setStatusText(null);

      try {
        const parties = await fetcher(query, resolvedFilterMode);
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
    [fetcher, resolvedFilterMode]
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

  const handleQuickCreate = useCallback(async (): Promise<void> => {
    const values = await quickCreateForm.validateFields();
    setQuickCreateSubmitting(true);
    try {
      const createdParty = await partyService.createParty({
        party_type: values.party_type,
        name: values.name,
        code: values.code,
        status: 'active',
      });
      const createdOption = toPartyOption(createdParty);
      setOptions(currentOptions => {
        const nextOptions = currentOptions.filter(option => option.value !== createdOption.value);
        return [createdOption, ...nextOptions];
      });
      setStatusText(null);
      setQuickCreateOpen(false);
      quickCreateForm.resetFields();
      onChange?.(createdParty.id, {
        party_id: createdParty.id,
        party_name: createdParty.name,
        party: createdParty,
      });
      MessageManager.success(`主体 ${createdParty.name} 已创建`);
    } catch (error) {
      MessageManager.error(error instanceof Error ? error.message : '创建主体失败');
    } finally {
      setQuickCreateSubmitting(false);
    }
  }, [onChange, quickCreateForm]);

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

      {!loading && allowQuickCreate && statusText === EMPTY_STATUS_TEXT ? (
        <Button
          type="link"
          onClick={() => {
            quickCreateForm.setFieldsValue({ party_type: defaultCreatePartyType });
            setQuickCreateOpen(true);
          }}
        >
          快速新建主体
        </Button>
      ) : null}

      <Modal
        title="快速新建主体"
        open={quickCreateOpen}
        onCancel={() => {
          setQuickCreateOpen(false);
          quickCreateForm.resetFields();
        }}
        onOk={() => {
          void handleQuickCreate();
        }}
        okText="创建主体"
        cancelText="取消"
        confirmLoading={quickCreateSubmitting}
        destroyOnHidden
      >
        <Form<QuickCreateFormValues>
          form={quickCreateForm}
          layout="vertical"
          initialValues={{ party_type: defaultCreatePartyType }}
        >
          <Form.Item
            label="主体类型"
            name="party_type"
            rules={[{ required: true, message: '请选择主体类型' }]}
          >
            <Select
              aria-label="快速新建主体类型"
              options={[
                { label: '组织', value: 'organization' },
                { label: '法人主体', value: 'legal_entity' },
                { label: '自然人', value: 'individual' },
              ]}
            />
          </Form.Item>
          <Form.Item
            label="主体名称"
            name="name"
            rules={[{ required: true, message: '请输入主体名称' }]}
          >
            <Input aria-label="快速新建主体名称" />
          </Form.Item>
          <Form.Item
            label="主体编码"
            name="code"
            rules={[{ required: true, message: '请输入主体编码' }]}
          >
            <Input aria-label="快速新建主体编码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PartySelector;
