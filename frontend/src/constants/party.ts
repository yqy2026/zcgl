import type { PartyIdentifierType, PartyType } from '@/types/party';

export const PARTY_TYPE_OPTIONS: Array<{ label: string; value: PartyType }> = [
  { label: '法人主体', value: 'legal_entity' },
  { label: '自然人', value: 'individual' },
];

export const PARTY_TYPE_LABELS: Record<PartyType, string> = {
  legal_entity: '法人主体',
  individual: '自然人',
};

const LEGAL_ENTITY_IDENTIFIER_OPTIONS: Array<{
  label: string;
  value: PartyIdentifierType;
}> = [
  { label: '统一社会信用代码', value: 'unified_social_credit_code' },
  { label: '法人登记号', value: 'legal_registration_number' },
  { label: '境外登记号', value: 'foreign_registration_number' },
];

const INDIVIDUAL_IDENTIFIER_OPTIONS: Array<{
  label: string;
  value: PartyIdentifierType;
}> = [
  { label: '居民身份证', value: 'national_id' },
  { label: '护照', value: 'passport' },
];

export const PARTY_IDENTIFIER_TYPE_LABELS: Record<PartyIdentifierType, string> = {
  unified_social_credit_code: '统一社会信用代码',
  legal_registration_number: '法人登记号',
  foreign_registration_number: '境外登记号',
  national_id: '居民身份证',
  passport: '护照',
};

export const getPartyIdentifierTypeOptions = (
  partyType: PartyType | null | undefined
): Array<{ label: string; value: PartyIdentifierType }> => {
  return partyType === 'individual'
    ? INDIVIDUAL_IDENTIFIER_OPTIONS
    : LEGAL_ENTITY_IDENTIFIER_OPTIONS;
};
