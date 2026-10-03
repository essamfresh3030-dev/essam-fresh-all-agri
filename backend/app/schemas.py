from datetime import date
from pydantic import BaseModel, ConfigDict
from typing import Optional
class Out(BaseModel): model_config=ConfigDict(from_attributes=True)
class CompanyCreate(BaseModel): name:str
class SectorCreate(BaseModel): company_id:str; name:str; code:Optional[str]=None
class FarmCreate(BaseModel): sector_id:str; name:str; code:Optional[str]=None; area_feddan:Optional[float]=None
class ClusterCreate(BaseModel): farm_id:str; name:str; code:Optional[str]=None
class GreenhouseCreate(BaseModel): cluster_id:str; name:str; code:Optional[str]=None; area_m2:Optional[float]=None
class CropCreate(BaseModel): name:str; variety:Optional[str]=None
class CropCycleCreate(BaseModel): greenhouse_id:str; crop_id:str; start_date:date; expected_end_date:Optional[date]=None; status:str="PLANNED"
class CostCenterCreate(BaseModel): company_id:str; code:str; name:str; center_type:str; parent_id:Optional[str]=None; sector_id:Optional[str]=None; farm_id:Optional[str]=None; cluster_id:Optional[str]=None; greenhouse_id:Optional[str]=None; crop_cycle_id:Optional[str]=None
class AccountCreate(BaseModel): company_id:str; code:str; name:str; account_type:str; parent_id:Optional[str]=None; is_postable:bool=True
class JournalLineCreate(BaseModel): account_id:str; cost_center_id:Optional[str]=None; description:Optional[str]=None; debit:float=0; credit:float=0
class JournalCreate(BaseModel): company_id:str; entry_no:str; entry_date:date; description:str; source_type:Optional[str]=None; source_id:Optional[str]=None; lines:list[JournalLineCreate]
class ItemCreate(BaseModel): name:str; item_type:str; unit:str; min_stock:float=0; reorder_level:float=0; standard_cost:float=0; inventory_account_id:Optional[str]=None; expense_account_id:Optional[str]=None; revenue_account_id:Optional[str]=None
class WarehouseCreate(BaseModel): name:str; location:Optional[str]=None
class InventoryCreate(BaseModel): item_id:str; warehouse_id:str; crop_cycle_id:Optional[str]=None; transaction_type:str; quantity:float; unit_cost:float=0; batch_no:Optional[str]=None; expiry_date:Optional[date]=None; cost_center_id:Optional[str]=None
class SupplierCreate(BaseModel): name:str; country:Optional[str]=None; tax_id:Optional[str]=None; payable_account_id:Optional[str]=None
class PurchaseInvoiceCreate(BaseModel): supplier_id:str; company_id:str; invoice_no:str; invoice_date:date; currency:str="EGP"; exchange_rate:float=1; vat_enabled:bool=False; vat_rate:float=0; vat_account_id:Optional[str]=None; receipt_id:Optional[str]=None; lines:list[dict]
class PurchaseQuotationCreate(BaseModel): supplier_id:str; company_id:str; quotation_no:str; quotation_date:date; valid_until:Optional[date]=None; currency:str="EGP"; exchange_rate:float=1; vat_enabled:bool=False; vat_rate:float=0; lines:list[dict]
class PurchaseOrderCreate(BaseModel): supplier_id:str; company_id:str; order_no:str; order_date:date; quotation_id:Optional[str]=None; currency:str="EGP"; exchange_rate:float=1; vat_enabled:bool=False; vat_rate:float=0; lines:list[dict]
class GoodsReceiptCreate(BaseModel): purchase_order_id:str; receipt_no:str; receipt_date:date; lines:list[dict]
class InventoryIssueCreate(BaseModel): issue_no:str; issue_date:date; warehouse_id:str; crop_cycle_id:Optional[str]=None; cost_center_id:Optional[str]=None; lines:list[dict]
class CustomerCreate(BaseModel): name:str; customer_type:str="LOCAL"; country:Optional[str]=None; tax_id:Optional[str]=None; receivable_account_id:Optional[str]=None
class SalesOrderCreate(BaseModel): customer_id:str; channel:str; order_date:date; currency:str="EGP"; exchange_rate:float=1; destination_country:Optional[str]=None; port_or_destination:Optional[str]=None
class SalesLineCreate(BaseModel): sales_order_id:str; crop_cycle_id:Optional[str]=None; description:str; quantity:float; unit_price:float
class SalesInvoiceCreate(BaseModel): sales_order_id:str; invoice_no:str; invoice_date:date; vat_enabled:bool=False; vat_rate:float=0; vat_account_id:Optional[str]=None
class ShipmentCreate(BaseModel): sales_order_id:str; shipment_type:str; destination:Optional[str]=None; transport_cost:float=0; freight_cost:float=0; insurance_cost:float=0; customs_cost:float=0; container_no:Optional[str]=None; incoterm:Optional[str]=None; notes:Optional[str]=None

class FarmOperationCreate(BaseModel):
    crop_cycle_id:str
    operation_type:str
    operation_date:date
    quantity:Optional[float]=None
    unit:Optional[str]=None
    amount:float=0
    description:Optional[str]=None
    item_id:Optional[str]=None
    worker_count:Optional[int]=None
    cost_center_id:Optional[str]=None

class LoginRequest(BaseModel):
    username:str
    password:str
class UserCreate(BaseModel):
    username:str; full_name:str; password:str; company_id:Optional[str]=None; role_ids:list[str]=[]
class RoleCreate(BaseModel):
    name:str; description:Optional[str]=None
class PermissionCreate(BaseModel):
    code:str; description:Optional[str]=None
class RolePermissionCreate(BaseModel):
    role_id:str; permission_id:str
class TokenResponse(BaseModel):
    access_token:str; token_type:str="bearer"
class SyncOperation(BaseModel):
    client_operation_id:str
    endpoint:str
    method:str="POST"
    payload:dict
class SyncBatch(BaseModel):
    operations:list[SyncOperation]

class InventoryCountCreate(BaseModel):
    count_no:str; count_date:date; warehouse_id:str; lines:list[dict]

class SalesQuotationCreate(BaseModel):
    customer_id:str; company_id:str; quotation_no:str; quotation_date:date; valid_until:Optional[date]=None; channel:str="LOCAL"; currency:str="EGP"; exchange_rate:float=1; vat_enabled:bool=False; vat_rate:float=0; lines:list[dict]
class SalesDeliveryCreate(BaseModel):
    sales_order_id:str; delivery_no:str; delivery_date:date; warehouse_id:str; lines:list[dict]
class SalesLocalServiceCreate(BaseModel):
    sales_order_id:str; service_type:str; description:Optional[str]=None; amount:float; currency:str="EGP"; exchange_rate:float=1

class CustomerReceiptCreate(BaseModel):
    customer_id:str; receipt_no:str; receipt_date:date; currency:str="EGP"; exchange_rate:float=1; amount:float; sales_invoice_id:Optional[str]=None; cash_account_id:str


class SalesOtherCostCreate(BaseModel):
    sales_order_id:str; cost_type:str; description:Optional[str]=None; amount:float; currency:str="EGP"; exchange_rate:float=1

class EmployeeCreate(BaseModel):
    employee_code: str
    full_name: str
    national_id: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    salary: float = 0

class AttendanceCreate(BaseModel):
    employee_id: str
    date: date
    status: str = "PRESENT"
    overtime_hours: float = 0
    notes: Optional[str] = None
