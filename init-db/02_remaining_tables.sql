-- ============================================================
-- init-db/02_remaining_tables.sql
-- Properties, FAQs, Leads tables
-- Run after 01_sessions.sql
-- ============================================================

-- ─── PROPERTIES TABLE ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS properties (
    id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    title              VARCHAR(300) NOT NULL,
    property_type      VARCHAR(50)  NOT NULL,   -- flat|villa|plot|commercial|independent_house
    bhk                SMALLINT,                -- NULL for commercial/plot
    price              BIGINT       NOT NULL,   -- in INR (no floats)
    city               VARCHAR(100) NOT NULL,
    locality           VARCHAR(100),
    address            TEXT,
    furnishing         VARCHAR(50)  DEFAULT 'unfurnished',  -- unfurnished|semi_furnished|fully_furnished
    amenities          JSONB        DEFAULT '[]',           -- ["gym","pool","parking","security"]
    area_sqft          INTEGER,
    floor              SMALLINT,
    total_floors       SMALLINT,
    rental_or_purchase VARCHAR(20)  NOT NULL DEFAULT 'sale',-- rent|sale
    listing_status     VARCHAR(20)  DEFAULT 'active',       -- active|inactive|sold
    geom               GEOGRAPHY(POINT, 4326),              -- PostGIS — lat/lng
    image_urls         JSONB        DEFAULT '[]',
    created_at         TIMESTAMPTZ  DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_properties_city
    ON properties (city);
CREATE INDEX IF NOT EXISTS idx_properties_status
    ON properties (listing_status);
CREATE INDEX IF NOT EXISTS idx_properties_type_bhk
    ON properties (property_type, bhk);
CREATE INDEX IF NOT EXISTS idx_properties_price
    ON properties (price);
CREATE INDEX IF NOT EXISTS idx_properties_locality
    ON properties (locality);
CREATE INDEX IF NOT EXISTS idx_properties_geom
    ON properties USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_properties_amenities
    ON properties USING GIN (amenities);

-- Auto-update trigger
DROP TRIGGER IF EXISTS trg_properties_updated_at ON properties;
CREATE TRIGGER trg_properties_updated_at
    BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ─── FAQS TABLE ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS faqs (
    id         SERIAL      PRIMARY KEY,
    category   VARCHAR(100),   -- payment|documentation|policy|process|amenities|general
    question   TEXT        NOT NULL,
    answer     TEXT        NOT NULL,
    keywords   TEXT[]      DEFAULT '{}',
    is_active  BOOLEAN     DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Full-text search index (English stemming on question + answer)
CREATE INDEX IF NOT EXISTS idx_faqs_fts
    ON faqs USING GIN (
        to_tsvector('english', question || ' ' || answer)
    );

CREATE INDEX IF NOT EXISTS idx_faqs_keywords
    ON faqs USING GIN (keywords);

CREATE INDEX IF NOT EXISTS idx_faqs_category
    ON faqs (category);

-- ─── SAMPLE FAQ DATA ─────────────────────────────────────────────
INSERT INTO faqs (category, question, answer, keywords) VALUES
('documentation', 'What documents are needed to buy a flat?',
 'To purchase a flat you typically need: Aadhar card, PAN card, 6 months bank statements, salary slips or ITR for the last 2 years, and Form 16. The builder will require a booking application and cheque for the token amount.',
 ARRAY['documents','buy','flat','aadhar','pan','salary','itr']),

('payment', 'What payment plans are available?',
 'We offer flexible payment plans including: Construction-Linked Plans (CLP) where you pay as construction progresses, Down Payment Plans with a discount on upfront payment, and Subvention Schemes where the builder pays EMIs during construction.',
 ARRAY['payment','plan','emi','construction','down payment','subvention']),

('documentation', 'What is stamp duty and registration charges?',
 'In Maharashtra, stamp duty is 5% for male buyers and 4% for female buyers on the property value. Registration charges are 1% of the property value (capped at Rs 30,000). Total cost is typically 6–7% of property value.',
 ARRAY['stamp duty','registration','maharashtra','charges','tax']),

('policy', 'What is the cancellation policy?',
 'If you cancel within 30 days of booking, you get a full refund minus the processing fee of 1%. After 30 days, a cancellation charge of 2% of the booking amount applies. After possession date, standard developer cancellation policy applies.',
 ARRAY['cancellation','refund','policy','booking','cancel']),

('process', 'How long does property registration take?',
 'Property registration at the Sub-Registrar office typically takes 1–2 hours on the appointment day. Preparing all documents beforehand takes 1–2 weeks. We assist with appointment scheduling and document preparation.',
 ARRAY['registration','process','time','sub-registrar','appointment']),

('process', 'What happens after I pay the token amount?',
 'After paying the token amount: (1) You receive an allotment letter within 7 days, (2) Agreement for Sale is executed within 30 days, (3) Home loan processing begins if applicable, (4) Regular construction updates are sent monthly.',
 ARRAY['token','booking','allotment','agreement','process','after']),

('amenities', 'Is parking included in the price?',
 'Yes, one covered car parking space is included with each 2BHK and larger unit. 1BHK units can purchase a parking space at an additional cost. Additional parking is available at extra cost subject to availability.',
 ARRAY['parking','car','included','price','space']),

('payment', 'Can I get a home loan from any bank?',
 'Yes, our projects are pre-approved by major banks including SBI, HDFC, ICICI, Axis, and Kotak Mahindra. Pre-approval means faster loan processing. You are also free to approach any other bank of your choice.',
 ARRAY['home loan','bank','sbi','hdfc','icici','pre-approved','finance'])
ON CONFLICT DO NOTHING;

-- ─── LEADS TABLE ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id                     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id             UUID,
    name                   VARCHAR(200),
    phone                  VARCHAR(20),
    phone_normalized       VARCHAR(15),   -- E.164 format: +91XXXXXXXXXX
    email                  VARCHAR(300),
    interested_property_ids UUID[]      DEFAULT '{}',
    interested_filters     JSONB        DEFAULT '{}',  -- filters at time of capture
    intent_type            VARCHAR(50)  DEFAULT 'contact_request', -- contact_request|site_visit
    preferred_visit_time   VARCHAR(200),
    status                 VARCHAR(50)  DEFAULT 'new', -- new|contacted|qualified|converted|lost
    source_channel         VARCHAR(50)  DEFAULT 'web',
    notes                  TEXT,
    created_at             TIMESTAMPTZ  DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_status      ON leads (status);
CREATE INDEX IF NOT EXISTS idx_leads_session_id  ON leads (session_id);
CREATE INDEX IF NOT EXISTS idx_leads_phone       ON leads (phone_normalized);
CREATE INDEX IF NOT EXISTS idx_leads_created_at  ON leads (created_at DESC);

DROP TRIGGER IF EXISTS trg_leads_updated_at ON leads;
CREATE TRIGGER trg_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ─── SANITY CHECK ────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE 'Properties table: %', (SELECT COUNT(*) FROM properties);
    RAISE NOTICE 'FAQs table: %', (SELECT COUNT(*) FROM faqs);
    RAISE NOTICE 'Leads table: %', (SELECT COUNT(*) FROM leads);
END;
$$;
