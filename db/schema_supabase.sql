-- Tour2Crypto Supabase/Postgres schema aligned with JSON contracts.

CREATE TYPE application_status AS ENUM ('draft', 'submitted', 'approved', 'rejected');
CREATE TYPE trip_status AS ENUM ('planned', 'completed', 'cancelled');
CREATE TYPE withdrawal_status AS ENUM ('pending', 'approved', 'rejected', 'processed');
CREATE TYPE ledger_entry_type AS ENUM ('cashback', 'adjustment', 'withdrawal');
CREATE TYPE ledger_rule_type AS ENUM ('cashback_accrual', 'cashback_reversal', 'withdrawal_lock', 'withdrawal_release', 'payout');
CREATE TYPE ledger_direction AS ENUM ('credit', 'debit');

CREATE TABLE applications (
    id TEXT PRIMARY KEY CHECK (char_length(id) = 26),
    traveler_id TEXT NOT NULL CHECK (char_length(traveler_id) = 26),
    trip_type TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    status application_status NOT NULL,
    notes TEXT
);

CREATE TABLE wallets (
    id TEXT PRIMARY KEY CHECK (char_length(id) = 26),
    owner_id TEXT NOT NULL CHECK (char_length(owner_id) = 26),
    currency TEXT NOT NULL CHECK (currency = 'USDT'),
    created_at TIMESTAMPTZ NOT NULL,
    description TEXT
);

CREATE TABLE trips (
    id TEXT PRIMARY KEY CHECK (char_length(id) = 26),
    traveler_id TEXT NOT NULL CHECK (char_length(traveler_id) = 26),
    application_id TEXT REFERENCES applications(id) ON DELETE SET NULL,
    partner_id TEXT,
    destination TEXT NOT NULL,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    status trip_status NOT NULL,
    CONSTRAINT trip_traveler_fk FOREIGN KEY (traveler_id) REFERENCES wallets(owner_id) ON DELETE CASCADE
);

CREATE TABLE withdrawals (
    id TEXT PRIMARY KEY CHECK (char_length(id) = 26),
    wallet_id TEXT NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
    requested_amount NUMERIC(14, 2) NOT NULL,
    status withdrawal_status NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    destination_address TEXT
);

CREATE TABLE cashback_ledger (
    id TEXT PRIMARY KEY CHECK (char_length(id) = 26),
    wallet_id TEXT NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
    trip_id TEXT REFERENCES trips(id) ON DELETE SET NULL,
    withdrawal_id TEXT REFERENCES withdrawals(id) ON DELETE SET NULL,
    amount NUMERIC(14, 2) NOT NULL,
    entry_type ledger_entry_type NOT NULL,
    rule_type ledger_rule_type NOT NULL,
    direction ledger_direction,
    occurred_at TIMESTAMPTZ NOT NULL,
    description TEXT,
    reference TEXT UNIQUE,
    lock_id TEXT REFERENCES withdrawals(id)
);

CREATE TABLE audit_events (
    id TEXT PRIMARY KEY CHECK (char_length(id) = 26),
    actor_id TEXT NOT NULL CHECK (char_length(actor_id) = 26),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL CHECK (char_length(entity_id) = 26),
    action TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    ip_address TEXT
);

CREATE INDEX idx_applications_traveler ON applications (traveler_id);
CREATE INDEX idx_applications_status ON applications (status);
CREATE INDEX idx_wallets_owner ON wallets (owner_id);
CREATE INDEX idx_wallets_created_at ON wallets (created_at);
CREATE INDEX idx_trips_traveler ON trips (traveler_id);
CREATE INDEX idx_trips_application ON trips (application_id);
CREATE INDEX idx_trips_status ON trips (status);
CREATE INDEX idx_trips_partner ON trips (partner_id);
CREATE INDEX idx_withdrawals_wallet ON withdrawals (wallet_id);
CREATE INDEX idx_withdrawals_status ON withdrawals (status);
CREATE INDEX idx_cashback_ledger_wallet ON cashback_ledger (wallet_id);
CREATE INDEX idx_cashback_ledger_trip ON cashback_ledger (trip_id);
CREATE INDEX idx_cashback_ledger_rule_type ON cashback_ledger (rule_type);
CREATE INDEX idx_audit_events_entity ON audit_events (entity_id);
CREATE INDEX idx_audit_events_created ON audit_events (created_at);

CREATE VIEW wallet_balances AS
SELECT
    wallet_id,
    SUM(amount) AS available_amount
FROM cashback_ledger
GROUP BY wallet_id;
