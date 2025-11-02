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

DROP VIEW IF EXISTS wallet_balances;
CREATE VIEW IF NOT EXISTS wallet_balances AS
WITH normalized AS (
    SELECT
        wallet_id,
        ABS(CAST(amount AS REAL)) AS amount_value,
        rule_type
    FROM cashback_ledger
)
SELECT
    wallet_id,
    printf('%.2f', SUM(CASE WHEN rule_type = 'cashback_accrual' THEN amount_value ELSE 0 END)) AS credit_total,
    printf('%.2f', SUM(CASE WHEN rule_type IN ('cashback_reversal', 'payout') THEN amount_value ELSE 0 END)) AS debit_total,
    printf(
        '%.2f',
        SUM(
            CASE
                WHEN rule_type = 'withdrawal_lock' THEN amount_value
                WHEN rule_type = 'withdrawal_release' THEN -amount_value
                ELSE 0
            END
        )
    ) AS locked_total,
    printf(
        '%.2f',
        SUM(CASE WHEN rule_type = 'cashback_accrual' THEN amount_value ELSE 0 END)
        - SUM(CASE WHEN rule_type IN ('cashback_reversal', 'payout') THEN amount_value ELSE 0 END)
        - SUM(
            CASE
                WHEN rule_type = 'withdrawal_lock' THEN amount_value
                WHEN rule_type = 'withdrawal_release' THEN -amount_value
                ELSE 0
            END
        )
    ) AS available_amount
FROM normalized
GROUP BY wallet_id;
