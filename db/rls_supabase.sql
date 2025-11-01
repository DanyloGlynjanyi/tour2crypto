-- Row Level Security policies for Supabase roles.

ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE withdrawals ENABLE ROW LEVEL SECURITY;
ALTER TABLE cashback_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

-- Helper expressions rely on custom JWT claims:
--   request.jwt.claim.role          -> anon | user | partner | admin
--   request.jwt.claim.partner_id    -> partner scope identifier
--   auth.uid()                      -> authenticated user ULID

-- Wallet access: users manage their own wallet, admins manage all.
CREATE POLICY user_wallets_select ON wallets
    FOR SELECT
    USING (owner_id = auth.uid()::text OR current_setting('request.jwt.claim.role', true) = 'admin');

CREATE POLICY user_wallets_modify ON wallets
    FOR ALL
    USING (owner_id = auth.uid()::text OR current_setting('request.jwt.claim.role', true) = 'admin')
    WITH CHECK (owner_id = auth.uid()::text OR current_setting('request.jwt.claim.role', true) = 'admin');

-- Applications follow traveler ownership.
CREATE POLICY user_applications ON applications
    FOR ALL
    USING (traveler_id = auth.uid()::text OR current_setting('request.jwt.claim.role', true) = 'admin')
    WITH CHECK (traveler_id = auth.uid()::text OR current_setting('request.jwt.claim.role', true) = 'admin');

-- Trips can be read by travelers, admins, or partners bound by partner_id.
CREATE POLICY trip_traveler_access ON trips
    FOR SELECT
    USING (
        traveler_id = auth.uid()::text
        OR current_setting('request.jwt.claim.role', true) = 'admin'
        OR (
            current_setting('request.jwt.claim.role', true) = 'partner'
            AND partner_id = current_setting('request.jwt.claim.partner_id', true)
        )
    );

CREATE POLICY trip_partner_manage ON trips
    FOR UPDATE
    USING (
        current_setting('request.jwt.claim.role', true) = 'partner'
        AND partner_id = current_setting('request.jwt.claim.partner_id', true)
    )
    WITH CHECK (
        current_setting('request.jwt.claim.role', true) = 'partner'
        AND partner_id = current_setting('request.jwt.claim.partner_id', true)
    );

CREATE POLICY trip_admin_manage ON trips
    FOR ALL
    USING (current_setting('request.jwt.claim.role', true) = 'admin')
    WITH CHECK (current_setting('request.jwt.claim.role', true) = 'admin');

-- Withdrawals limited to wallet owners or admins.
CREATE POLICY withdrawal_user_access ON withdrawals
    FOR ALL
    USING (wallet_id IN (SELECT id FROM wallets WHERE owner_id = auth.uid()::text)
           OR current_setting('request.jwt.claim.role', true) = 'admin')
    WITH CHECK (wallet_id IN (SELECT id FROM wallets WHERE owner_id = auth.uid()::text)
                OR current_setting('request.jwt.claim.role', true) = 'admin');

-- Ledger visible to wallet owners, partners for trips, or admins.
CREATE POLICY ledger_user_access ON cashback_ledger
    FOR SELECT
    USING (
        wallet_id IN (SELECT id FROM wallets WHERE owner_id = auth.uid()::text)
        OR current_setting('request.jwt.claim.role', true) = 'admin'
        OR (
            current_setting('request.jwt.claim.role', true) = 'partner'
            AND trip_id IN (
                SELECT id FROM trips
                WHERE partner_id = current_setting('request.jwt.claim.partner_id', true)
            )
        )
    );

CREATE POLICY ledger_admin_manage ON cashback_ledger
    FOR ALL
    USING (current_setting('request.jwt.claim.role', true) = 'admin')
    WITH CHECK (current_setting('request.jwt.claim.role', true) = 'admin');

-- Audit events only administrators can write; users can read their own actions.
CREATE POLICY audit_user_read ON audit_events
    FOR SELECT
    USING (
        actor_id = auth.uid()::text OR current_setting('request.jwt.claim.role', true) = 'admin'
    );

CREATE POLICY audit_admin_manage ON audit_events
    FOR ALL
    USING (current_setting('request.jwt.claim.role', true) = 'admin')
    WITH CHECK (current_setting('request.jwt.claim.role', true) = 'admin');
