INSERT INTO entity_ontology (code, parent_code, label) VALUES
    ('REGULATED_ENTITY', NULL, 'Regulated entity'),
    ('BANK', 'REGULATED_ENTITY', 'Bank'),
    ('COMMERCIAL_BANK', 'BANK', 'Commercial bank'),
    ('SMALL_FINANCE_BANK', 'COMMERCIAL_BANK', 'Small finance bank'),
    ('LOCAL_AREA_BANK', 'COMMERCIAL_BANK', 'Local area bank'),
    ('REGIONAL_RURAL_BANK', 'COMMERCIAL_BANK', 'Regional rural bank'),
    ('PAYMENTS_BANK', 'COMMERCIAL_BANK', 'Payments bank'),
    ('COOPERATIVE_BANK', 'BANK', 'Co-operative bank'),
    ('PRIMARY_URBAN_COOPERATIVE_BANK', 'COOPERATIVE_BANK', 'Primary urban co-operative bank'),
    ('STATE_COOPERATIVE_BANK', 'COOPERATIVE_BANK', 'State co-operative bank'),
    ('DISTRICT_CENTRAL_COOPERATIVE_BANK', 'COOPERATIVE_BANK', 'District central co-operative bank'),
    ('NBFC', 'REGULATED_ENTITY', 'Non-banking financial company'),
    ('NBFC_ICC', 'NBFC', 'NBFC investment and credit company'),
    ('NBFC_MFI', 'NBFC', 'NBFC microfinance institution'),
    ('HFC', 'NBFC', 'Housing finance company')
ON CONFLICT (code) DO UPDATE SET
    parent_code = EXCLUDED.parent_code,
    label = EXCLUDED.label;
