CREATE INDEX IF NOT EXISTS idx_applications_traveler ON applications(traveler_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_wallets_owner ON wallets(owner_id);
CREATE INDEX IF NOT EXISTS idx_wallets_created_at ON wallets(created_at);
CREATE INDEX IF NOT EXISTS idx_trips_traveler ON trips(traveler_id);
CREATE INDEX IF NOT EXISTS idx_trips_application ON trips(application_id);
CREATE INDEX IF NOT EXISTS idx_trips_partner ON trips(partner_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_withdrawals_wallet ON withdrawals(wallet_id);
CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status);
CREATE INDEX IF NOT EXISTS idx_cashback_ledger_wallet ON cashback_ledger(wallet_id);
CREATE INDEX IF NOT EXISTS idx_cashback_ledger_trip ON cashback_ledger(trip_id);
CREATE INDEX IF NOT EXISTS idx_cashback_ledger_rule_type ON cashback_ledger(rule_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at);

CREATE VIEW IF NOT EXISTS wallet_balances AS
SELECT
    wallet_id,
    printf('%.2f', IFNULL(SUM(CAST(amount AS REAL)), 0.0)) AS available_amount
FROM cashback_ledger
GROUP BY wallet_id;
