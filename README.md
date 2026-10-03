# Agri ERP v1.7

- LOCAL sales default to VAT disabled.
- Local weighing and other service costs supported without VAT.
- Other sales costs supported.
- Sales profitability endpoint separates product cost, local services, other costs, freight, transport, insurance and customs.
- Profit and margin calculated per sales order.
- EXPORT retains shipment/container/Incoterm/currency/exchange-rate fields.

## Profitability
GET /api/sales/profitability/{sales_order_id}


## v1.8 Dashboard
- `/api/dashboard/kpis` consolidated operational and financial KPIs with optional company/channel filters.
- `/api/dashboard/profitability` returns profitability by sales order with LOCAL/EXPORT filtering.
- Local sales remain VAT-free by business rule.
- Revenue, product cost, local services, weighing, freight, transport, insurance, customs and other costs remain separately traceable.
- Dashboard values are derived from the same backend records used by sales, inventory and crop-cost flows.
