PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL,
    trip_type TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'submitted', 'approved', 'rejected')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS wallets (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    currency TEXT NOT NULL CHECK (currency = 'USDT'),
    created_at TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS trips (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL,
    application_id TEXT,
    partner_id TEXT,
    destination TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'completed', 'cancelled')),
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL,
    FOREIGN KEY (traveler_id) REFERENCES wallets(owner_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    requested_amount TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'processed')),
    requested_at TEXT NOT NULL,
    processed_at TEXT,
    destination_address TEXT,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cashback_ledger (
    id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    trip_id TEXT,
    withdrawal_id TEXT,
    amount TEXT NOT NULL,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('cashback', 'adjustment', 'withdrawal')),
    rule_type TEXT NOT NULL CHECK (rule_type IN ('cashback_accrual', 'cashback_reversal', 'withdrawal_lock', 'withdrawal_release', 'payout')),
    direction TEXT CHECK (direction IN ('credit', 'debit')),
    occurred_at TEXT NOT NULL,
    description TEXT,
    reference TEXT UNIQUE,
    lock_id TEXT,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id) ON DELETE CASCADE,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE SET NULL,
    FOREIGN KEY (withdrawal_id) REFERENCES withdrawals(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ip_address TEXT
);
