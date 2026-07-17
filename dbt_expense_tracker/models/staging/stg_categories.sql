-- Staging model: categories dimension with types FK (v3)
-- Derives category_type from types.name instead of old categories.type column

WITH source AS (
    SELECT
        id,
        name,
        type_id,
        icon,
        created_at
    FROM {{ source('expense_tracker', 'categories') }}
),

type_lookup AS (
    SELECT * FROM {{ source('expense_tracker', 'types') }}
)

SELECT
    c.id AS category_id,
    c.name AS category_name,
    c.type_id,
    t.name AS type_name,
    t.sort_order AS type_sort_order,

    -- Derive broad category (expense/income/saving) from type name
    -- fixed + variable = expense; income + saving are self-named
    CASE
        WHEN t.name IN ('fixed', 'variable') THEN 'expense'
        ELSE t.name
    END AS category_type,

    c.icon,
    c.created_at
FROM source c
JOIN type_lookup t ON c.type_id = t.id
