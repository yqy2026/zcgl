import type { Perspective } from './capability';

export interface ViewSelectionOption {
  key: string;
  perspective: Perspective;
  partyId: string;
  partyName: string;
  label: string;
}

export interface StoredViewSelection {
  key: string;
  perspective: Perspective;
  partyId: string;
}
