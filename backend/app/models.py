import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, ForeignKey, Numeric, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def uid(): return str(uuid.uuid4())

class Company(Base):
    __tablename__="companies"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); name:Mapped[str]=mapped_column(String(200),nullable=False)
    sectors=relationship("Sector",back_populates="company",cascade="all, delete-orphan")
class Sector(Base):
    __tablename__="sectors"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False); name:Mapped[str]=mapped_column(String(200),nullable=False); code:Mapped[str|None]=mapped_column(String(50))
    company=relationship("Company",back_populates="sectors"); farms=relationship("Farm",back_populates="sector",cascade="all, delete-orphan")
class Farm(Base):
    __tablename__="farms"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); sector_id:Mapped[str]=mapped_column(ForeignKey("sectors.id"),nullable=False); name:Mapped[str]=mapped_column(String(200),nullable=False); code:Mapped[str|None]=mapped_column(String(50)); area_feddan:Mapped[float|None]=mapped_column(Numeric(12,3)); active:Mapped[bool]=mapped_column(Boolean,default=True)
    sector=relationship("Sector",back_populates="farms"); clusters=relationship("Cluster",back_populates="farm",cascade="all, delete-orphan")
class Cluster(Base):
    __tablename__="clusters"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); farm_id:Mapped[str]=mapped_column(ForeignKey("farms.id"),nullable=False); name:Mapped[str]=mapped_column(String(200),nullable=False); code:Mapped[str|None]=mapped_column(String(50))
    farm=relationship("Farm",back_populates="clusters"); greenhouses=relationship("Greenhouse",back_populates="cluster",cascade="all, delete-orphan")
class Greenhouse(Base):
    __tablename__="greenhouses"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); cluster_id:Mapped[str]=mapped_column(ForeignKey("clusters.id"),nullable=False); name:Mapped[str]=mapped_column(String(200),nullable=False); code:Mapped[str|None]=mapped_column(String(50)); area_m2:Mapped[float|None]=mapped_column(Numeric(12,2)); active:Mapped[bool]=mapped_column(Boolean,default=True)
    cluster=relationship("Cluster",back_populates="greenhouses"); crop_cycles=relationship("CropCycle",back_populates="greenhouse")
class Crop(Base):
    __tablename__="crops"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); name:Mapped[str]=mapped_column(String(150),nullable=False); variety:Mapped[str|None]=mapped_column(String(150))
class CropCycle(Base):
    __tablename__="crop_cycles"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); greenhouse_id:Mapped[str]=mapped_column(ForeignKey("greenhouses.id"),nullable=False); crop_id:Mapped[str]=mapped_column(ForeignKey("crops.id"),nullable=False); start_date:Mapped[date]=mapped_column(Date,nullable=False); expected_end_date:Mapped[date|None]=mapped_column(Date); status:Mapped[str]=mapped_column(String(30),default="PLANNED")
    greenhouse=relationship("Greenhouse",back_populates="crop_cycles"); crop=relationship("Crop")

class CostCenter(Base):
    __tablename__="cost_centers"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False); parent_id:Mapped[str|None]=mapped_column(ForeignKey("cost_centers.id")); code:Mapped[str]=mapped_column(String(50),nullable=False,unique=True); name:Mapped[str]=mapped_column(String(200),nullable=False); center_type:Mapped[str]=mapped_column(String(30),nullable=False); sector_id:Mapped[str|None]=mapped_column(ForeignKey("sectors.id")); farm_id:Mapped[str|None]=mapped_column(ForeignKey("farms.id")); cluster_id:Mapped[str|None]=mapped_column(ForeignKey("clusters.id")); greenhouse_id:Mapped[str|None]=mapped_column(ForeignKey("greenhouses.id")); crop_cycle_id:Mapped[str|None]=mapped_column(ForeignKey("crop_cycles.id")); active:Mapped[bool]=mapped_column(Boolean,default=True)
    parent=relationship("CostCenter",remote_side=[id])

class Account(Base):
    __tablename__="accounts"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False); code:Mapped[str]=mapped_column(String(30),nullable=False); name:Mapped[str]=mapped_column(String(200),nullable=False); account_type:Mapped[str]=mapped_column(String(30),nullable=False); parent_id:Mapped[str|None]=mapped_column(ForeignKey("accounts.id")); is_postable:Mapped[bool]=mapped_column(Boolean,default=True); active:Mapped[bool]=mapped_column(Boolean,default=True)
    parent=relationship("Account",remote_side=[id])
class JournalEntry(Base):
    __tablename__="journal_entries"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False); entry_no:Mapped[str]=mapped_column(String(50),nullable=False); entry_date:Mapped[date]=mapped_column(Date,nullable=False); description:Mapped[str]=mapped_column(String(500),nullable=False); source_type:Mapped[str|None]=mapped_column(String(50)); source_id:Mapped[str|None]=mapped_column(String(36)); posted:Mapped[bool]=mapped_column(Boolean,default=True)
    lines=relationship("JournalLine",back_populates="entry",cascade="all, delete-orphan")
class JournalLine(Base):
    __tablename__="journal_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); journal_entry_id:Mapped[str]=mapped_column(ForeignKey("journal_entries.id"),nullable=False); account_id:Mapped[str]=mapped_column(ForeignKey("accounts.id"),nullable=False); cost_center_id:Mapped[str|None]=mapped_column(ForeignKey("cost_centers.id")); description:Mapped[str|None]=mapped_column(String(500)); debit:Mapped[float]=mapped_column(Numeric(18,2),default=0); credit:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    entry=relationship("JournalEntry",back_populates="lines"); account=relationship("Account")

class Item(Base):
    __tablename__="items"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); name:Mapped[str]=mapped_column(String(200),nullable=False); item_type:Mapped[str]=mapped_column(String(40),nullable=False); unit:Mapped[str]=mapped_column(String(30),nullable=False); active:Mapped[bool]=mapped_column(Boolean,default=True); min_stock:Mapped[float]=mapped_column(Numeric(18,4),default=0); reorder_level:Mapped[float]=mapped_column(Numeric(18,4),default=0); standard_cost:Mapped[float]=mapped_column(Numeric(18,4),default=0); inventory_account_id:Mapped[str|None]=mapped_column(ForeignKey("accounts.id")); expense_account_id:Mapped[str|None]=mapped_column(ForeignKey("accounts.id")); revenue_account_id:Mapped[str|None]=mapped_column(ForeignKey("accounts.id"))
class Warehouse(Base):
    __tablename__="warehouses"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); name:Mapped[str]=mapped_column(String(200),nullable=False); location:Mapped[str|None]=mapped_column(String(200))
class InventoryTransaction(Base):
    __tablename__="inventory_transactions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); item_id:Mapped[str]=mapped_column(ForeignKey("items.id"),nullable=False); warehouse_id:Mapped[str]=mapped_column(ForeignKey("warehouses.id"),nullable=False); crop_cycle_id:Mapped[str|None]=mapped_column(ForeignKey("crop_cycles.id")); transaction_type:Mapped[str]=mapped_column(String(20),nullable=False); quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); unit_cost:Mapped[float]=mapped_column(Numeric(18,4),default=0); total_cost:Mapped[float]=mapped_column(Numeric(18,4),default=0); batch_no:Mapped[str|None]=mapped_column(String(100)); expiry_date:Mapped[date|None]=mapped_column(Date); transaction_date:Mapped[datetime]=mapped_column(DateTime,nullable=False); journal_entry_id:Mapped[str|None]=mapped_column(ForeignKey("journal_entries.id"))
class CropCost(Base):
    __tablename__="crop_costs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); crop_cycle_id:Mapped[str]=mapped_column(ForeignKey("crop_cycles.id"),nullable=False); cost_type:Mapped[str]=mapped_column(String(50),nullable=False); description:Mapped[str|None]=mapped_column(Text); amount:Mapped[float]=mapped_column(Numeric(18,2),nullable=False); source_type:Mapped[str|None]=mapped_column(String(50)); source_id:Mapped[str|None]=mapped_column(String(36)); cost_date:Mapped[date]=mapped_column(Date,nullable=False); cost_center_id:Mapped[str|None]=mapped_column(ForeignKey("cost_centers.id"))

class Supplier(Base):
    __tablename__="suppliers"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); name:Mapped[str]=mapped_column(String(200),nullable=False); country:Mapped[str|None]=mapped_column(String(100)); tax_id:Mapped[str|None]=mapped_column(String(100)); payable_account_id:Mapped[str|None]=mapped_column(ForeignKey("accounts.id"))
class PurchaseInvoice(Base):
    __tablename__="purchase_invoices"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); supplier_id:Mapped[str]=mapped_column(ForeignKey("suppliers.id"),nullable=False); company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False); invoice_no:Mapped[str]=mapped_column(String(100),nullable=False); invoice_date:Mapped[date]=mapped_column(Date,nullable=False); currency:Mapped[str]=mapped_column(String(10),default="EGP"); exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1); total:Mapped[float]=mapped_column(Numeric(18,2),default=0); status:Mapped[str]=mapped_column(String(20),default="DRAFT"); approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id")); approved_at:Mapped[datetime|None]=mapped_column(DateTime); vat_enabled:Mapped[bool]=mapped_column(Boolean,default=False); subtotal:Mapped[float]=mapped_column(Numeric(18,2),default=0); vat_rate:Mapped[float]=mapped_column(Numeric(8,4),default=0); vat_amount:Mapped[float]=mapped_column(Numeric(18,2),default=0); grand_total:Mapped[float]=mapped_column(Numeric(18,2),default=0); vat_account_id:Mapped[str|None]=mapped_column(ForeignKey("accounts.id")); receipt_id:Mapped[str|None]=mapped_column(ForeignKey("goods_receipts.id")); journal_entry_id:Mapped[str|None]=mapped_column(ForeignKey("journal_entries.id"))
class PurchaseLine(Base):
    __tablename__="purchase_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); purchase_invoice_id:Mapped[str]=mapped_column(ForeignKey("purchase_invoices.id"),nullable=False); item_id:Mapped[str]=mapped_column(ForeignKey("items.id"),nullable=False); warehouse_id:Mapped[str]=mapped_column(ForeignKey("warehouses.id"),nullable=False); quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); unit_cost:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); total:Mapped[float]=mapped_column(Numeric(18,2),nullable=False)

class Customer(Base):
    __tablename__="customers"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); name:Mapped[str]=mapped_column(String(200),nullable=False); customer_type:Mapped[str]=mapped_column(String(20),default="LOCAL"); country:Mapped[str|None]=mapped_column(String(100)); tax_id:Mapped[str|None]=mapped_column(String(100)); receivable_account_id:Mapped[str|None]=mapped_column(ForeignKey("accounts.id"))
class SalesOrder(Base):
    __tablename__="sales_orders"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); customer_id:Mapped[str]=mapped_column(ForeignKey("customers.id"),nullable=False); channel:Mapped[str]=mapped_column(String(20),nullable=False); order_date:Mapped[date]=mapped_column(Date,nullable=False); currency:Mapped[str]=mapped_column(String(10),default="EGP"); exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1); status:Mapped[str]=mapped_column(String(30),default="DRAFT"); destination_country:Mapped[str|None]=mapped_column(String(100)); port_or_destination:Mapped[str|None]=mapped_column(String(200)); customer=relationship("Customer")
class SalesLine(Base):
    __tablename__="sales_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); sales_order_id:Mapped[str]=mapped_column(ForeignKey("sales_orders.id"),nullable=False); crop_cycle_id:Mapped[str|None]=mapped_column(ForeignKey("crop_cycles.id")); description:Mapped[str]=mapped_column(String(250),nullable=False); quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); unit_price:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); total:Mapped[float]=mapped_column(Numeric(18,4),nullable=False)
class SalesInvoice(Base):
    __tablename__="sales_invoices"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); sales_order_id:Mapped[str]=mapped_column(ForeignKey("sales_orders.id"),nullable=False); invoice_no:Mapped[str]=mapped_column(String(100),nullable=False); invoice_date:Mapped[date]=mapped_column(Date,nullable=False); total:Mapped[float]=mapped_column(Numeric(18,2),default=0); subtotal:Mapped[float]=mapped_column(Numeric(18,2),default=0); vat_enabled:Mapped[bool]=mapped_column(Boolean,default=False); vat_rate:Mapped[float]=mapped_column(Numeric(8,4),default=0); vat_amount:Mapped[float]=mapped_column(Numeric(18,2),default=0); total_egp:Mapped[float]=mapped_column(Numeric(18,2),default=0); journal_entry_id:Mapped[str|None]=mapped_column(ForeignKey("journal_entries.id")); status:Mapped[str]=mapped_column(String(20),default="POSTED")
class Shipment(Base):
    __tablename__="shipments"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); sales_order_id:Mapped[str]=mapped_column(ForeignKey("sales_orders.id"),nullable=False); shipment_type:Mapped[str]=mapped_column(String(20),nullable=False); destination:Mapped[str|None]=mapped_column(String(200)); transport_cost:Mapped[float]=mapped_column(Numeric(18,2),default=0); freight_cost:Mapped[float]=mapped_column(Numeric(18,2),default=0); insurance_cost:Mapped[float]=mapped_column(Numeric(18,2),default=0); customs_cost:Mapped[float]=mapped_column(Numeric(18,2),default=0); container_no:Mapped[str|None]=mapped_column(String(100)); incoterm:Mapped[str|None]=mapped_column(String(30)); notes:Mapped[str|None]=mapped_column(Text)



class SalesQuotation(Base):
    __tablename__="sales_quotations"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    customer_id:Mapped[str]=mapped_column(ForeignKey("customers.id"),nullable=False)
    company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False)
    quotation_no:Mapped[str]=mapped_column(String(100),nullable=False)
    quotation_date:Mapped[date]=mapped_column(Date,nullable=False)
    valid_until:Mapped[date|None]=mapped_column(Date)
    channel:Mapped[str]=mapped_column(String(20),default="LOCAL")
    currency:Mapped[str]=mapped_column(String(10),default="EGP")
    exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1)
    vat_enabled:Mapped[bool]=mapped_column(Boolean,default=False)
    vat_rate:Mapped[float]=mapped_column(Numeric(8,4),default=0)
    subtotal:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    vat_amount:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    grand_total:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    status:Mapped[str]=mapped_column(String(20),default="DRAFT")

class SalesQuotationLine(Base):
    __tablename__="sales_quotation_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    quotation_id:Mapped[str]=mapped_column(ForeignKey("sales_quotations.id"),nullable=False)
    description:Mapped[str]=mapped_column(String(250),nullable=False)
    crop_cycle_id:Mapped[str|None]=mapped_column(ForeignKey("crop_cycles.id"))
    quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False)
    unit_price:Mapped[float]=mapped_column(Numeric(18,4),nullable=False)
    total:Mapped[float]=mapped_column(Numeric(18,2),nullable=False)

class SalesDelivery(Base):
    __tablename__="sales_deliveries"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    sales_order_id:Mapped[str]=mapped_column(ForeignKey("sales_orders.id"),nullable=False)
    delivery_no:Mapped[str]=mapped_column(String(100),nullable=False)
    delivery_date:Mapped[date]=mapped_column(Date,nullable=False)
    warehouse_id:Mapped[str]=mapped_column(ForeignKey("warehouses.id"),nullable=False)
    status:Mapped[str]=mapped_column(String(20),default="POSTED")
    approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id"))
    approved_at:Mapped[datetime|None]=mapped_column(DateTime)

class SalesDeliveryLine(Base):
    __tablename__="sales_delivery_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    delivery_id:Mapped[str]=mapped_column(ForeignKey("sales_deliveries.id"),nullable=False)
    description:Mapped[str]=mapped_column(String(250),nullable=False)
    item_id:Mapped[str|None]=mapped_column(ForeignKey("items.id"))
    quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False)
    unit_cost:Mapped[float]=mapped_column(Numeric(18,4),default=0)
    batch_no:Mapped[str|None]=mapped_column(String(100))

class SalesLocalService(Base):
    __tablename__="sales_local_services"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    sales_order_id:Mapped[str]=mapped_column(ForeignKey("sales_orders.id"),nullable=False)
    service_type:Mapped[str]=mapped_column(String(80),nullable=False)
    description:Mapped[str|None]=mapped_column(String(250))
    amount:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    currency:Mapped[str]=mapped_column(String(10),default="EGP")
    exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1)
    vat_enabled:Mapped[bool]=mapped_column(Boolean,default=False)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class SalesOtherCost(Base):
    __tablename__="sales_other_costs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    sales_order_id:Mapped[str]=mapped_column(ForeignKey("sales_orders.id"),nullable=False)
    cost_type:Mapped[str]=mapped_column(String(80),nullable=False)
    description:Mapped[str|None]=mapped_column(String(250))
    amount:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    currency:Mapped[str]=mapped_column(String(10),default="EGP")
    exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class CustomerReceipt(Base):
    __tablename__="customer_receipts"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    customer_id:Mapped[str]=mapped_column(ForeignKey("customers.id"),nullable=False)
    receipt_no:Mapped[str]=mapped_column(String(100),nullable=False)
    receipt_date:Mapped[date]=mapped_column(Date,nullable=False)
    currency:Mapped[str]=mapped_column(String(10),default="EGP")
    exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1)
    amount:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    amount_egp:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    sales_invoice_id:Mapped[str|None]=mapped_column(ForeignKey("sales_invoices.id"))
    status:Mapped[str]=mapped_column(String(20),default="POSTED")

class FarmOperation(Base):
    __tablename__="farm_operations"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    crop_cycle_id:Mapped[str]=mapped_column(ForeignKey("crop_cycles.id"),nullable=False)
    operation_type:Mapped[str]=mapped_column(String(40),nullable=False)
    operation_date:Mapped[date]=mapped_column(Date,nullable=False)
    quantity:Mapped[float|None]=mapped_column(Numeric(18,4))
    unit:Mapped[str|None]=mapped_column(String(30))
    amount:Mapped[float]=mapped_column(Numeric(18,2),default=0)
    description:Mapped[str|None]=mapped_column(Text)
    item_id:Mapped[str|None]=mapped_column(ForeignKey("items.id"))
    worker_count:Mapped[int|None]=mapped_column(Integer)
    cost_center_id:Mapped[str|None]=mapped_column(ForeignKey("cost_centers.id"))
    source_type:Mapped[str|None]=mapped_column(String(40))
    source_id:Mapped[str|None]=mapped_column(String(36))

class Role(Base):
    __tablename__="roles"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(100),nullable=False,unique=True)
    description:Mapped[str|None]=mapped_column(String(300))

class Permission(Base):
    __tablename__="permissions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    code:Mapped[str]=mapped_column(String(120),nullable=False,unique=True)
    description:Mapped[str|None]=mapped_column(String(300))

class User(Base):
    __tablename__="users"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    username:Mapped[str]=mapped_column(String(100),nullable=False,unique=True)
    full_name:Mapped[str]=mapped_column(String(200),nullable=False)
    password_hash:Mapped[str]=mapped_column(String(300),nullable=False)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    company_id:Mapped[str|None]=mapped_column(ForeignKey("companies.id"))

class UserRole(Base):
    __tablename__="user_roles"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    role_id:Mapped[str]=mapped_column(ForeignKey("roles.id"),nullable=False)

class RolePermission(Base):
    __tablename__="role_permissions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    role_id:Mapped[str]=mapped_column(ForeignKey("roles.id"),nullable=False)
    permission_id:Mapped[str]=mapped_column(ForeignKey("permissions.id"),nullable=False)

class AuditLog(Base):
    __tablename__="audit_logs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str|None]=mapped_column(ForeignKey("users.id"))
    action:Mapped[str]=mapped_column(String(80),nullable=False)
    entity_type:Mapped[str]=mapped_column(String(80),nullable=False)
    entity_id:Mapped[str|None]=mapped_column(String(36))
    metadata_json:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,nullable=False)

class SyncInbox(Base):
    __tablename__="sync_inbox"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    client_operation_id:Mapped[str]=mapped_column(String(100),nullable=False,unique=True)
    user_id:Mapped[str|None]=mapped_column(ForeignKey("users.id"))
    endpoint:Mapped[str]=mapped_column(String(200),nullable=False)
    method:Mapped[str]=mapped_column(String(10),nullable=False)
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="COMMITTED")
    response_json:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,nullable=False)

class PurchaseQuotation(Base):
    __tablename__="purchase_quotations"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); supplier_id:Mapped[str]=mapped_column(ForeignKey("suppliers.id"),nullable=False); company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False); quotation_no:Mapped[str]=mapped_column(String(100),nullable=False); quotation_date:Mapped[date]=mapped_column(Date,nullable=False); valid_until:Mapped[date|None]=mapped_column(Date); currency:Mapped[str]=mapped_column(String(10),default="EGP"); exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1); vat_enabled:Mapped[bool]=mapped_column(Boolean,default=False); subtotal:Mapped[float]=mapped_column(Numeric(18,2),default=0); vat_rate:Mapped[float]=mapped_column(Numeric(8,4),default=0); vat_amount:Mapped[float]=mapped_column(Numeric(18,2),default=0); grand_total:Mapped[float]=mapped_column(Numeric(18,2),default=0); status:Mapped[str]=mapped_column(String(20),default="DRAFT"); approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id")); approved_at:Mapped[datetime|None]=mapped_column(DateTime)
class PurchaseQuotationLine(Base):
    __tablename__="purchase_quotation_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); quotation_id:Mapped[str]=mapped_column(ForeignKey("purchase_quotations.id"),nullable=False); item_id:Mapped[str]=mapped_column(ForeignKey("items.id"),nullable=False); quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); unit_price:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); total:Mapped[float]=mapped_column(Numeric(18,2),nullable=False)
class PurchaseOrder(Base):
    __tablename__="purchase_orders"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); supplier_id:Mapped[str]=mapped_column(ForeignKey("suppliers.id"),nullable=False); company_id:Mapped[str]=mapped_column(ForeignKey("companies.id"),nullable=False); order_no:Mapped[str]=mapped_column(String(100),nullable=False); order_date:Mapped[date]=mapped_column(Date,nullable=False); quotation_id:Mapped[str|None]=mapped_column(ForeignKey("purchase_quotations.id")); vat_enabled:Mapped[bool]=mapped_column(Boolean,default=False); currency:Mapped[str]=mapped_column(String(10),default="EGP"); exchange_rate:Mapped[float]=mapped_column(Numeric(18,6),default=1); subtotal:Mapped[float]=mapped_column(Numeric(18,2),default=0); vat_rate:Mapped[float]=mapped_column(Numeric(8,4),default=0); vat_amount:Mapped[float]=mapped_column(Numeric(18,2),default=0); grand_total:Mapped[float]=mapped_column(Numeric(18,2),default=0); status:Mapped[str]=mapped_column(String(20),default="DRAFT"); approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id")); approved_at:Mapped[datetime|None]=mapped_column(DateTime)
class PurchaseOrderLine(Base):
    __tablename__="purchase_order_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); purchase_order_id:Mapped[str]=mapped_column(ForeignKey("purchase_orders.id"),nullable=False); item_id:Mapped[str]=mapped_column(ForeignKey("items.id"),nullable=False); warehouse_id:Mapped[str]=mapped_column(ForeignKey("warehouses.id"),nullable=False); quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); unit_price:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); total:Mapped[float]=mapped_column(Numeric(18,2),nullable=False)
class GoodsReceipt(Base):
    __tablename__="goods_receipts"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); purchase_order_id:Mapped[str]=mapped_column(ForeignKey("purchase_orders.id"),nullable=False); receipt_no:Mapped[str]=mapped_column(String(100),nullable=False); receipt_date:Mapped[date]=mapped_column(Date,nullable=False); status:Mapped[str]=mapped_column(String(20),default="POSTED"); approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id")); approved_at:Mapped[datetime|None]=mapped_column(DateTime)
class GoodsReceiptLine(Base):
    __tablename__="goods_receipt_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); receipt_id:Mapped[str]=mapped_column(ForeignKey("goods_receipts.id"),nullable=False); item_id:Mapped[str]=mapped_column(ForeignKey("items.id"),nullable=False); warehouse_id:Mapped[str]=mapped_column(ForeignKey("warehouses.id"),nullable=False); quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); unit_cost:Mapped[float]=mapped_column(Numeric(18,4),default=0); batch_no:Mapped[str|None]=mapped_column(String(100)); expiry_date:Mapped[date|None]=mapped_column(Date)
class InventoryIssue(Base):
    __tablename__="inventory_issues"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); issue_no:Mapped[str]=mapped_column(String(100),nullable=False); issue_date:Mapped[date]=mapped_column(Date,nullable=False); warehouse_id:Mapped[str]=mapped_column(ForeignKey("warehouses.id"),nullable=False); crop_cycle_id:Mapped[str|None]=mapped_column(ForeignKey("crop_cycles.id")); cost_center_id:Mapped[str|None]=mapped_column(ForeignKey("cost_centers.id")); status:Mapped[str]=mapped_column(String(20),default="POSTED"); approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id")); approved_at:Mapped[datetime|None]=mapped_column(DateTime)
class InventoryIssueLine(Base):
    __tablename__="inventory_issue_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); issue_id:Mapped[str]=mapped_column(ForeignKey("inventory_issues.id"),nullable=False); item_id:Mapped[str]=mapped_column(ForeignKey("items.id"),nullable=False); quantity:Mapped[float]=mapped_column(Numeric(18,4),nullable=False); unit_cost:Mapped[float]=mapped_column(Numeric(18,4),default=0); total_cost:Mapped[float]=mapped_column(Numeric(18,2),default=0)


class InventoryCount(Base):
    __tablename__="inventory_counts"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    count_no:Mapped[str]=mapped_column(String(100),nullable=False)
    count_date:Mapped[date]=mapped_column(Date,nullable=False)
    warehouse_id:Mapped[str]=mapped_column(ForeignKey("warehouses.id"),nullable=False)
    status:Mapped[str]=mapped_column(String(20),default="DRAFT")
    approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id"))
    approved_at:Mapped[datetime|None]=mapped_column(DateTime)

class InventoryCountLine(Base):
    __tablename__="inventory_count_lines"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    count_id:Mapped[str]=mapped_column(ForeignKey("inventory_counts.id"),nullable=False)
    item_id:Mapped[str]=mapped_column(ForeignKey("items.id"),nullable=False)
    batch_no:Mapped[str|None]=mapped_column(String(100))
    expiry_date:Mapped[date|None]=mapped_column(Date)
    system_quantity:Mapped[float]=mapped_column(Numeric(18,4),default=0)
    counted_quantity:Mapped[float]=mapped_column(Numeric(18,4),default=0)
    unit_cost:Mapped[float]=mapped_column(Numeric(18,4),default=0)

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    national_id: Mapped[str|None] = mapped_column(String(50))
    job_title: Mapped[str|None] = mapped_column(String(100))
    department: Mapped[str|None] = mapped_column(String(100))
    salary: Mapped[float] = mapped_column(Numeric(18,2), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Attendance(Base):
    __tablename__ = "attendances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT") # PRESENT, ABSENT, LEAVE
    overtime_hours: Mapped[float] = mapped_column(Numeric(8,2), default=0)
    notes: Mapped[str|None] = mapped_column(Text)
