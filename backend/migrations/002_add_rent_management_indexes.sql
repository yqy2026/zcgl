-- Add performance indexes for rent management
-- This script adds indexes to improve query performance for rent management operations

-- Rent ledger indexes
CREATE INDEX IF NOT EXISTS idx_rent_ledger_date_status ON rent_ledger (due_date, payment_status);
CREATE INDEX IF NOT EXISTS idx_rent_ledger_year_month_status ON rent_ledger (year_month, payment_status);
CREATE INDEX IF NOT EXISTS idx_rent_ledger_contract_id ON rent_ledger (contract_id);
CREATE INDEX IF NOT EXISTS idx_rent_ledger_ownership_id ON rent_ledger (ownership_id);
CREATE INDEX IF NOT EXISTS idx_rent_ledger_asset_id ON rent_ledger (asset_id);

-- Rent contract indexes
CREATE INDEX IF NOT EXISTS idx_rent_contracts_dates_status ON rent_contracts (start_date, end_date, contract_status);
CREATE INDEX IF NOT EXISTS idx_rent_contracts_asset_id ON rent_contracts (asset_id);
CREATE INDEX IF NOT EXISTS idx_rent_contracts_ownership_id ON rent_contracts (ownership_id);
CREATE INDEX IF NOT EXISTS idx_rent_contracts_tenant_name ON rent_contracts (tenant_name);
CREATE INDEX IF NOT EXISTS idx_rent_contracts_contract_number ON rent_contracts (contract_number);

-- Rent term indexes
CREATE INDEX IF NOT EXISTS idx_rent_terms_contract_id ON rent_terms (contract_id);
CREATE INDEX IF NOT EXISTS idx_rent_terms_date_range ON rent_terms (start_date, end_date);